import io
from dataclasses import replace
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from enterprise_support_agent.rag.knowledge_store import MultimodalKnowledgeStore, KnowledgeIngestionError
from enterprise_support_agent.tools.create_ticket import TicketStore

def test_failed_document_status_is_persisted_and_can_be_deleted(tmp_path):
    store = MultimodalKnowledgeStore(tmp_path)
    with pytest.raises(KnowledgeIngestionError):
        store.ingest('broken.pdf', b'not-pdf')
    doc = MultimodalKnowledgeStore(tmp_path).list_documents()[0]
    assert doc['status'] == 'failed' and doc['error']
    assert store.delete(doc['document_id'])

def test_separate_stores_do_not_lose_documents(tmp_path):
    one, two = MultimodalKnowledgeStore(tmp_path), MultimodalKnowledgeStore(tmp_path)
    one.ingest('a.txt', b'apple warranty terms')
    two.ingest('b.txt', b'banana delivery time')
    assert len(MultimodalKnowledgeStore(tmp_path).list_documents()) == 2

def test_concurrent_ticket_replay_across_instances_is_deduplicated(tmp_path):
    def call(_):
        return TicketStore(tmp_path / 'tickets.jsonl').create('Help me', 'Review requested', 'high', 'same-request-001')
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(call, range(12)))
    assert len({r['ticket']['ticket_id'] for r in results}) == 1
    assert len((tmp_path / 'tickets.jsonl').read_text().splitlines()) == 1

def test_long_paragraph_chunk_limit():
    chunks = MultimodalKnowledgeStore._chunk_text('a' * 1600)
    assert len(chunks) == 4
    assert max(map(len, chunks)) <= 520
