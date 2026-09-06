"""Persistent TXT, Markdown, PDF and image knowledge ingestion with local OCR."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from functools import wraps
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image
from pypdf import PdfReader

from enterprise_support_agent.rag.embeddings import create_embedder, cosine_similarity, tokenize


ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg"}
STORE_LOCK = threading.RLock()

def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with STORE_LOCK:
            self._load()
            return method(self, *args, **kwargs)
    return call


class KnowledgeIngestionError(ValueError):
    pass


@dataclass(slots=True)
class ManagedChunk:
    chunk_id: str
    document_id: str
    source: str
    page: int | None
    text: str
    vector: list[float]


class MultimodalKnowledgeStore:
    def __init__(self, root: Path, *, max_bytes: int = 8 * 1024 * 1024) -> None:
        self.root = root
        self.files_path = root / "files"
        self.index_path = root / "index.json"
        self.max_bytes = max_bytes
        self.embedder = create_embedder()
        self.documents: dict[str, dict[str, Any]] = {}
        self.chunks: list[ManagedChunk] = []
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.documents = {item["document_id"]: item for item in payload.get("documents", [])}
        self.chunks = [ManagedChunk(**item) for item in payload.get("chunks", [])]
        if payload.get('embedding_provider') != self.embedder.provider:
            for chunk in self.chunks:
                chunk.vector = self.embedder.embed(chunk.text)

    def _persist(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "embedding_provider": self.embedder.provider,
            "documents": list(self.documents.values()),
            "chunks": [asdict(item) for item in self.chunks],
        }
        temporary = self.index_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.index_path)

    def list_documents(self) -> list[dict[str, Any]]:
        return sorted(self.documents.values(), key=lambda item: item["created_at"], reverse=True)

    @serialized
    def ingest(self, filename: str, content: bytes) -> dict[str, Any]:
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise KnowledgeIngestionError("仅支持 TXT、Markdown、PDF、PNG、JPG 和 JPEG")
        if not content:
            raise KnowledgeIngestionError("文件为空")
        if len(content) > self.max_bytes:
            raise KnowledgeIngestionError(f"文件超过 {self.max_bytes // 1024 // 1024} MB 限制")
        document_id = hashlib.sha256(safe_name.encode("utf-8") + b"\0" + content).hexdigest()[:16]
        if document_id in self.documents and self.documents[document_id]['status'] == 'ready':
            return self.documents[document_id]
        stored_name = f"{document_id}{suffix}"
        self.documents[document_id] = {'document_id': document_id, 'filename': safe_name, 'status': 'processing', 'parser': '', 'chunk_count': 0, 'size_bytes': len(content), 'created_at': datetime.now(timezone.utc).isoformat(), 'stored_name': stored_name, 'error': None}
        self._persist()
        try:
            pages, parser = self._extract(suffix, content)
            if not any(text.strip() for _, text in pages):
                raise KnowledgeIngestionError('未提取到可检索文本')
        except Exception as error:
            self.documents[document_id].update(status='failed', error=str(error))
            self._persist()
            raise KnowledgeIngestionError(str(error)) from error
        self.files_path.mkdir(parents=True, exist_ok=True)
        (self.files_path / stored_name).write_bytes(content)
        created_at = datetime.now(timezone.utc).isoformat()
        new_chunks: list[ManagedChunk] = []
        for page, text in pages:
            for index, part in enumerate(self._chunk_text(text)):
                new_chunks.append(
                    ManagedChunk(
                        chunk_id=f"{document_id}#p{page or 0}-{index}",
                        document_id=document_id,
                        source=safe_name,
                        page=page,
                        text=part,
                        vector=self.embedder.embed(part),
                    )
                )
        record = {
            "document_id": document_id,
            "filename": safe_name,
            "media_type": suffix.lstrip("."),
            "parser": parser,
            "status": "ready",
            "page_count": len(pages),
            "chunk_count": len(new_chunks),
            "created_at": created_at,
            "size_bytes": len(content),
            "stored_name": stored_name,
        }
        self.documents[document_id] = record
        self.chunks.extend(new_chunks)
        self._persist()
        return record

    @serialized
    def delete(self, document_id: str) -> bool:
        record = self.documents.pop(document_id, None)
        if record is None:
            return False
        self.chunks = [item for item in self.chunks if item.document_id != document_id]
        stored = self.files_path / record["stored_name"]
        if stored.exists():
            stored.unlink()
        self._persist()
        return True

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not query.strip():
            raise KnowledgeIngestionError("检索词不能为空")
        query_vector = self.embedder.embed(query)
        query_tokens = set(tokenize(query))
        ranked: list[tuple[float, ManagedChunk]] = []
        for chunk in self.chunks:
            semantic = cosine_similarity(query_vector, chunk.vector)
            lexical = len(query_tokens & set(tokenize(chunk.text))) / max(1, len(query_tokens))
            ranked.append((0.55 * semantic + 0.45 * lexical, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "category": "uploaded",
                "source": chunk.source,
                "page": chunk.page,
                "text": chunk.text,
                "score": round(score, 6),
            }
            for score, chunk in ranked[:top_k]
            if score >= (0.25 if self.embedder.provider != 'local-hashing' else 0.12)
        ]

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 520) -> list[str]:
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = paragraph
            else:
                current = candidate
        if current:
            chunks.append(current)
        return [part[start:start + max_chars] for part in chunks for start in range(0, len(part), max_chars)]

    def _extract(self, suffix: str, content: bytes) -> tuple[list[tuple[int | None, str]], str]:
        if suffix in {".txt", ".md"}:
            try:
                text = content.decode("utf-8-sig").strip()
            except UnicodeDecodeError as error:
                raise KnowledgeIngestionError("文本文件必须使用 UTF-8 编码") from error
            return [(None, text)], "utf8-text"
        if suffix == ".pdf":
            return self._extract_pdf(content)
        return [(1, self._ocr_image(content))], "rapidocr"

    def _extract_pdf(self, content: bytes) -> tuple[list[tuple[int, str]], str]:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as error:
            raise KnowledgeIngestionError("PDF 无法解析") from error
        pages: list[tuple[int, str]] = []
        missing: list[int] = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append((number, text))
            if not text:
                missing.append(number)
        parser = "pypdf"
        if missing:
            rendered = self._ocr_pdf_pages(content, missing)
            pages = [(number, rendered.get(number, text)) for number, text in pages]
            parser = "pypdf+rapidocr"
        return pages, parser

    def _ocr_pdf_pages(self, content: bytes, pages: list[int]) -> dict[int, str]:
        configured = os.getenv("ESA_PDFTOPPM_PATH", "").strip()
        executable = configured or shutil.which("pdftoppm")
        if executable and not Path(executable).is_file() and configured:
            raise KnowledgeIngestionError("ESA_PDFTOPPM_PATH 指向的文件不存在")
        if executable is None:
            raise KnowledgeIngestionError("扫描 PDF 需要 pdftoppm，当前环境未找到")
        extracted: dict[int, str] = {}
        with tempfile.TemporaryDirectory(prefix="esa-pdf-") as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(content)
            for page in pages:
                prefix = Path(directory) / f"page-{page}"
                run = subprocess.run(
                    [str(executable), "-f", str(page), "-l", str(page), "-png", "-r", "160", str(source), str(prefix)],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if run.returncode != 0:
                    raise KnowledgeIngestionError(f"PDF 第 {page} 页渲染失败")
                images = list(Path(directory).glob(f"page-{page}-*.png"))
                if images:
                    extracted[page] = self._ocr_image(images[0].read_bytes())
        return extracted

    @staticmethod
    def _ocr_image(content: bytes) -> str:
        try:
            import numpy as np
            from rapidocr_onnxruntime import RapidOCR

            image = Image.open(io.BytesIO(content)).convert("RGB")
            result, _ = RapidOCR()(np.asarray(image))
        except Exception as error:
            raise KnowledgeIngestionError("图片 OCR 失败") from error
        if not result:
            return ""
        return "\n".join(str(item[1]).strip() for item in result if len(item) > 1 and str(item[1]).strip())
