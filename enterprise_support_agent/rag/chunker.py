"""Policy document loader and paragraph-aware chunker."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Document:
    document_id: str
    category: str
    text: str
    source: str


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    category: str
    text: str
    source: str


def load_documents(directory: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        category = path.stem.replace("_policy", "")
        documents.append(Document(path.stem, category, text, path.name))
    if not documents:
        raise FileNotFoundError(f"No Markdown policy documents found in {directory}")
    return documents


def chunk_document(document: Document, max_chars: int = 520, overlap_chars: int = 0) -> list[Chunk]:
    """Create coherent chunks from Markdown paragraphs, with bounded overlap."""

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", document.text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            prefix = current[-overlap_chars:] if overlap_chars else ""
            current = f"{prefix}\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [
        Chunk(
            chunk_id=f"{document.document_id}#{index}",
            document_id=document.document_id,
            category=document.category,
            text=text,
            source=document.source,
        )
        for index, text in enumerate(chunks)
    ]


def build_chunks(directory: Path) -> list[Chunk]:
    return [chunk for document in load_documents(directory) for chunk in chunk_document(document)]
