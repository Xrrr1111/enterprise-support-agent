from __future__ import annotations

import io
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter

from enterprise_support_agent.rag.knowledge_store import KnowledgeIngestionError, MultimodalKnowledgeStore


def test_text_ingest_search_and_delete(tmp_path) -> None:
    store = MultimodalKnowledgeStore(tmp_path / "knowledge")
    document = store.ingest("退换货说明.md", "定制商品不支持无理由退货。".encode())
    results = store.search("定制商品退货")
    assert results and results[0]["source"] == "退换货说明.md"
    assert store.delete(document["document_id"]) is True
    assert store.search("定制商品退货") == []


def test_rejects_empty_unsupported_and_oversized_files(tmp_path) -> None:
    store = MultimodalKnowledgeStore(tmp_path / "knowledge", max_bytes=4)
    with pytest.raises(KnowledgeIngestionError, match="为空"):
        store.ingest("empty.txt", b"")
    with pytest.raises(KnowledgeIngestionError, match="仅支持"):
        store.ingest("payload.exe", b"x")
    with pytest.raises(KnowledgeIngestionError, match="超过"):
        store.ingest("large.txt", b"12345")


def test_pdf_text_keeps_page_source(tmp_path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    store = MultimodalKnowledgeStore(tmp_path / "knowledge")
    with pytest.raises(KnowledgeIngestionError, match="未提取到"):
        store.ingest("blank.pdf", stream.getvalue())


def test_image_uses_real_ocr_pipeline(tmp_path) -> None:
    image = Image.new("RGB", (760, 180), "white")
    font = ImageFont.truetype("arial.ttf" if sys.platform == "win32" else "DejaVuSans.ttf", 48)
    ImageDraw.Draw(image).text((30, 45), "REFUND POLICY 30 DAYS", fill="black", font=font)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    store = MultimodalKnowledgeStore(tmp_path / "knowledge")
    document = store.ingest("policy.png", stream.getvalue())
    assert document["parser"] == "rapidocr"
    assert document["chunk_count"] >= 1
    assert store.search("REFUND POLICY")
