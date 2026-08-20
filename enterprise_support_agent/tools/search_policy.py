"""RAG-backed policy search tool."""

from __future__ import annotations

from typing import Any

from enterprise_support_agent.rag.retriever import PolicyRetriever


class PolicySearchTool:
    def __init__(self, retriever: PolicyRetriever) -> None:
        self.retriever = retriever

    def search(self, query: str, top_k: int = 3, category: str | None = None) -> dict[str, Any]:
        return self.retriever.search(query=query, top_k=top_k, category=category)
