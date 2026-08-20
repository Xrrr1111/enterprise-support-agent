from enterprise_support_agent.rag.chunker import build_chunks, load_documents
from enterprise_support_agent.rag.embeddings import HashingEmbedder, cosine_similarity, tokenize
from enterprise_support_agent.rag.retriever import PolicyRetriever


def test_knowledge_base_has_all_policy_documents(settings) -> None:
    documents = load_documents(settings.policies_path)
    assert {document.category for document in documents} == {"refund", "return", "shipping", "after_sales"}


def test_chunk_ids_are_stable_and_bounded(settings) -> None:
    chunks = build_chunks(settings.policies_path)
    assert len(chunks) >= 8
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert max(map(lambda chunk: len(chunk.text), chunks)) <= 520


def test_hashing_embeddings_are_deterministic() -> None:
    embedder = HashingEmbedder()
    assert embedder.embed("refund policy") == embedder.embed("refund policy")
    assert cosine_similarity(embedder.embed("refund"), embedder.embed("refund")) > 0.99


def test_tokenizer_supports_english_stems_and_chinese_bigrams() -> None:
    tokens = tokenize("refunds 退款政策")
    assert "refund" in tokens
    assert "退款" in tokens


def test_retrieval_recall_for_each_domain(settings) -> None:
    retriever = PolicyRetriever(settings.policies_path)
    cases = {
        "refund window": "refund_policy",
        "return merchandise authorization": "return_policy",
        "carrier investigation tracking stuck": "shipping_policy",
        "hardware warranty repair": "after_sales_policy",
    }
    for query, expected in cases.items():
        documents = {item["document_id"] for item in retriever.search(query, top_k=3)["results"]}
        assert expected in documents


def test_category_filter_never_leaks_other_policy(settings) -> None:
    result = PolicyRetriever(settings.policies_path).search("days", top_k=10, category="return")
    assert {item["category"] for item in result["results"]} == {"return"}
