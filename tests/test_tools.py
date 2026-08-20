from __future__ import annotations

import json

import pytest

from enterprise_support_agent.rag.retriever import PolicyRetriever
from enterprise_support_agent.tools.base import ToolValidationError, validate_arguments
from enterprise_support_agent.tools.calculator import calculate
from enterprise_support_agent.tools.create_ticket import TicketStore
from enterprise_support_agent.tools.query_order import OrderRepository
from enterprise_support_agent.tools.schemas import QUERY_ORDER_SCHEMA


def test_query_order_returns_business_fields(settings) -> None:
    result = OrderRepository(settings.orders_path).query("ord-1002")
    assert result["found"] is True
    assert result["order"]["shipping_status"] == "in_transit"
    assert result["order"]["amount"] == 249.0


def test_query_order_not_found_is_data_not_exception(settings) -> None:
    assert OrderRepository(settings.orders_path).query("ORD-9999") == {
        "found": False,
        "order_id": "ORD-9999",
        "message": "Order was not found.",
    }


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("2 + 3 * 4", 14), ("(10 - 2) / 4", 2.0), ("5 ** 3", 125), ("11 % 4", 3)],
)
def test_calculator_valid_expressions(expression: str, expected: float) -> None:
    assert calculate(expression)["result"] == expected


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('whoami')", "open('secret')", "2 ** 100", "1 / 0", "[1, 2][0]"],
)
def test_calculator_rejects_unsafe_or_unbounded_input(expression: str) -> None:
    with pytest.raises((ValueError, ZeroDivisionError)):
        calculate(expression)


def test_ticket_store_persists_required_fields(settings) -> None:
    result = TicketStore(settings.tickets_path).create("Need help", "Manual review", "high")
    ticket = result["ticket"]
    persisted = json.loads(settings.tickets_path.read_text(encoding="utf-8"))
    assert ticket["ticket_id"].startswith("TKT-")
    assert persisted["priority"] == "high"
    assert persisted["created_at"].endswith("+00:00")


def test_schema_validation_rejects_missing_and_extra_arguments() -> None:
    with pytest.raises(ToolValidationError, match="missing required"):
        validate_arguments(QUERY_ORDER_SCHEMA, {})
    with pytest.raises(ToolValidationError, match="unexpected"):
        validate_arguments(QUERY_ORDER_SCHEMA, {"order_id": "ORD-1", "secret": True})


def test_policy_search_tool_pipeline(settings) -> None:
    result = PolicyRetriever(settings.policies_path).search("refund window", top_k=2, category="refund")
    assert len(result["results"]) == 2
    assert result["results"][0]["document_id"] == "refund_policy"
    assert "context" in result
    assert result["embedding_provider"] == "local-hashing"
