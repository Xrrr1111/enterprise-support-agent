"""Explicit tool registry and dependency wiring."""

from __future__ import annotations

from pathlib import Path

from enterprise_support_agent.config import Settings
from enterprise_support_agent.rag.knowledge_store import MultimodalKnowledgeStore
from enterprise_support_agent.rag.retriever import CombinedKnowledgeRetriever, PolicyRetriever
from enterprise_support_agent.tools.base import ToolDefinition
from enterprise_support_agent.tools.calculator import calculate
from enterprise_support_agent.tools.create_ticket import TicketStore
from enterprise_support_agent.tools.query_order import OrderRepository
from enterprise_support_agent.tools.schemas import (
    CALCULATOR_SCHEMA,
    CREATE_TICKET_SCHEMA,
    QUERY_ORDER_SCHEMA,
    SEARCH_POLICY_SCHEMA,
)
from enterprise_support_agent.tools.search_policy import PolicySearchTool


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools = {tool.name: tool for tool in (tools or [])}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        return [tool.as_llm_schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)


def build_default_registry(settings: Settings, tickets_path: Path | None = None) -> ToolRegistry:
    orders = OrderRepository(settings.orders_path)
    uploads = MultimodalKnowledgeStore(settings.knowledge_uploads_path)
    policy = PolicySearchTool(CombinedKnowledgeRetriever(PolicyRetriever(settings.policies_path), uploads))
    tickets = TicketStore(tickets_path or settings.tickets_path)
    return ToolRegistry(
        [
            ToolDefinition(
                "query_order",
                "Look up verified payment, fulfillment, shipping, refund, and amount fields for one order ID.",
                QUERY_ORDER_SCHEMA,
                orders.query,
            ),
            ToolDefinition(
                "search_policy",
                "Retrieve top policy passages from the local refund, return, shipping, and after-sales knowledge base.",
                SEARCH_POLICY_SCHEMA,
                policy.search,
            ),
            ToolDefinition(
                "create_ticket",
                "Create a durable human-support ticket when automation cannot resolve the request or escalation is requested.",
                CREATE_TICKET_SCHEMA,
                tickets.create,
                idempotent=False,
            ),
            ToolDefinition(
                "calculator",
                "Safely calculate a basic arithmetic expression; never perform arithmetic in the model.",
                CALCULATOR_SCHEMA,
                calculate,
                retryable_exceptions=(),
            ),
        ]
    )
