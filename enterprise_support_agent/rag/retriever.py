"""In-memory Top-K retriever: Document -> Chunk -> Embed -> Rank -> Context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from enterprise_support_agent.rag.chunker import Chunk, build_chunks
from enterprise_support_agent.rag.embeddings import HashingEmbedder, create_embedder, cosine_similarity, tokenize
from enterprise_support_agent.rag.knowledge_store import MultimodalKnowledgeStore


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk_id: str
    document_id: str
    category: str
    source: str
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["score"] = round(self.score, 6)
        return value


class PolicyRetriever:
    def __init__(self, knowledge_base: Path, embedder: HashingEmbedder | None = None) -> None:
        self.knowledge_base = knowledge_base
        self.embedder = embedder or create_embedder()
        self.chunks: list[Chunk] = build_chunks(knowledge_base)
        self._vectors = [self.embedder.embed(chunk.text) for chunk in self.chunks]

    def search(self, query: str, top_k: int = 3, category: str | None = None, min_score: float = 0.12) -> dict[str, Any]:
        expanded_query = self._expand_query(query)
        query_vector = self.embedder.embed(expanded_query)
        query_tokens = set(tokenize(expanded_query))
        ranked: list[SearchResult] = []
        for chunk, vector in zip(self.chunks, self._vectors, strict=True):
            if category and chunk.category != category:
                continue
            semantic = cosine_similarity(query_vector, vector)
            lexical_tokens = set(tokenize(chunk.text))
            lexical = len(query_tokens & lexical_tokens) / max(1, len(query_tokens))
            score = 0.55 * semantic + 0.45 * lexical
            ranked.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    category=chunk.category,
                    source=chunk.source,
                    text=chunk.text,
                    score=score,
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        results = [item for item in ranked if item.score >= min_score][:top_k]
        return {
            "query": query,
            "top_k": top_k,
            "category": category,
            "embedding_provider": self.embedder.provider,
            "results": [item.to_dict() for item in results],
            "context": "\n\n".join(f"[{item.chunk_id}] {item.text}" for item in results),
        }

    @staticmethod
    def _expand_query(query: str) -> str:
        """Add a few domain synonyms; a production embedder can replace this layer."""

        lowered = query.lower()
        expansions: list[str] = []
        if "window" in lowered:
            expansions.append("eligibility timing calendar days")
        if "stuck" in lowered:
            expansions.append("not changed carrier investigation")
        if "change of mind" in lowered:
            expansions.append("preference based return")
        if "warranty" in lowered:
            expansions.append("coverage limited warranty")
        if any(term in lowered for term in ("配送", "物流", "发货", "送达")):
            expansions.append("shipping delivery carrier")
        if any(term in lowered for term in ("退款", "退钱", "退费")):
            expansions.append("refund eligibility timing")
        if any(term in lowered for term in ("退货", "换货")):
            expansions.append("return window eligibility")
        return " ".join([query, *expansions])


class CombinedKnowledgeRetriever:
    """Merge versioned policy passages with user-managed multimodal knowledge."""

    def __init__(self, policies: PolicyRetriever, uploads: MultimodalKnowledgeStore) -> None:
        self.policies = policies
        self.uploads = uploads

    def search(self, query: str, top_k: int = 3, category: str | None = None) -> dict[str, Any]:
        policy = self.policies.search(query=query, top_k=top_k, category=category)
        uploaded = self.uploads.search(query, top_k=top_k)
        results = [*policy["results"], *uploaded]
        results.sort(key=lambda item: item["score"], reverse=True)
        results = results[:top_k]
        return {
            "query": query,
            "top_k": top_k,
            "category": category,
            "embedding_provider": self.uploads.embedder.provider,
            "results": results,
            "context": "\n\n".join(f"[{item['chunk_id']}] {item['text']}" for item in results),
        }
