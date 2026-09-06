"""Deterministic offline model used by demos, tests, and reproducible evals."""

from __future__ import annotations

import json
import hashlib
import re
from typing import Any

from enterprise_support_agent.llm.base import ModelDecision


ORDER_PATTERN = re.compile(r"\b(?:ORD|ORDER)[-_]?\d{3,}\b", re.IGNORECASE)
POLICY_TERMS = {
    "refund": ("refund", "退款", "退钱", "退费"),
    "return": ("return", "退货", "换货"),
    "shipping": ("shipping", "delivery", "tracking", "carrier", "delay", "发货", "物流", "送达", "配送"),
    "after_sales": ("warranty", "after-sales", "售后", "保修", "维修"),
}


def _tool_observations(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        content = message.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                content = {"raw": content}
        observations.append({"name": message.get("name"), "content": content})
    return observations


class MockLLM:
    """A transparent policy model, not a fake direct-answer shortcut.

    It only sees messages and tool schemas, emits one decision per turn, and must
    consume tool observations before it can answer. This makes the complete
    harness executable without credentials while preserving the real control flow.
    """

    provider = "mock"

    def decide(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        system_prompt: str,
    ) -> ModelDecision:
        del tool_schemas, system_prompt
        user_text = next(str(m["content"]) for m in messages if m.get("role") == "user")
        lowered = user_text.lower()
        observations = _tool_observations(messages)
        called = [item["name"] for item in observations]

        order_match = ORDER_PATTERN.search(user_text)
        if order_match and "query_order" not in called:
            order_id = order_match.group(0).upper().replace("ORDER", "ORD").replace("_", "-")
            if order_id.startswith("ORD") and not order_id.startswith("ORD-"):
                order_id = "ORD-" + order_id[3:].lstrip("-")
            return ModelDecision.call("query_order", {"order_id": order_id})

        categories = [category for category, terms in POLICY_TERMS.items() if any(term in lowered for term in terms)]
        policy_qualifiers = (
            "policy", "how long", "how many", "what happens", "what items", "who pays",
            "can i", "allowed", "when should", "explain", "what does", "政策", "规定", "多久", "能否",
        )
        asks_policy = bool(categories) and (not order_match or any(term in lowered for term in policy_qualifiers))
        asks_uploaded_knowledge = any(term in lowered for term in ("知识库", "资料", "文档", "knowledge base", "uploaded document"))
        if (asks_policy or asks_uploaded_knowledge) and "search_policy" not in called:
            arguments: dict[str, Any] = {"query": user_text, "top_k": 3}
            if len(categories) == 1:
                arguments["category"] = categories[0]
            return ModelDecision.call("search_policy", arguments)

        asks_human = any(term in lowered for term in ("human", "人工", "客服介入", "投诉"))
        order_missing = any(
            item["name"] == "query_order" and not item["content"].get("data", {}).get("found", False)
            for item in observations
        )
        if (asks_human or order_missing) and "create_ticket" not in called:
            reason = "Customer explicitly requested human support" if asks_human else "Order could not be found automatically"
            priority = "high" if any(term in lowered for term in ("urgent", "紧急", "投诉")) else "medium"
            return ModelDecision.call(
                "create_ticket",
                {
                    "user_request": user_text,
                    "reason": reason,
                    "priority": priority,
                    "idempotency_key": hashlib.sha256(user_text.strip().encode("utf-8")).hexdigest()[:20],
                },
            )

        expression = self._extract_expression(user_text)
        if expression and "calculator" not in called:
            return ModelDecision.call("calculator", {"expression": expression})

        if observations:
            return ModelDecision.final(self._compose_answer(observations))
        return ModelDecision.final(
            "I can help with orders, refunds, returns, shipping, after-sales policies, calculations, or a human-support ticket."
        )

    @staticmethod
    def _extract_expression(text: str) -> str | None:
        explicit = re.search(r"(?:calculate|计算|算一下|等于)\s*[:：]?\s*([\d\s+\-*/().%]+)", text, re.IGNORECASE)
        if explicit and any(operator in explicit.group(1) for operator in "+-*/%"):
            return explicit.group(1).strip().rstrip("?.。？")
        money = re.search(r"(?:refund|退款)[^\d]*(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if money:
            return f"{money.group(1)} * {money.group(2)}"
        return None

    @staticmethod
    def _compose_answer(observations: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for observation in observations:
            name = observation["name"]
            payload = observation["content"]
            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            if name == "query_order":
                if data.get("found"):
                    order = data["order"]
                    parts.append(
                        f"Order {order['order_id']} is {order['order_status']}; payment is {order['payment_status']}, "
                        f"shipping is {order['shipping_status']}, refund is {order['refund_status']}, "
                        f"and the amount is {order['currency']} {order['amount']:.2f}."
                    )
                else:
                    parts.append(f"I could not find order {data.get('order_id', '')}.")
            elif name == "search_policy":
                results = data.get("results", [])
                if results:
                    summaries = " ".join(MockLLM._clean_policy_text(result["text"]) for result in results[:2])
                    sources = ", ".join(dict.fromkeys(result["document_id"] for result in results[:2]))
                    parts.append(f"Policy guidance: {summaries} Sources: {sources}.")
                else:
                    parts.append("No relevant policy passage was found.")
            elif name == "create_ticket" and data.get("ticket"):
                ticket = data["ticket"]
                parts.append(f"I created support ticket {ticket['ticket_id']} with {ticket['priority']} priority.")
            elif name == "calculator":
                parts.append(f"The calculated result is {data.get('result')}.")
            elif not payload.get("ok", True):
                parts.append(f"The {name} tool failed: {payload.get('error', 'unknown error')}.")
        return " ".join(parts) or "I could not complete the request automatically."

    @staticmethod
    def _clean_policy_text(text: str) -> str:
        without_headings = re.sub(r"(?m)^#+\s*[^\n]+\s*", "", text)
        return re.sub(r"\s+", " ", without_headings).strip()


class ScriptedLLM:
    """Test/eval adapter that returns an explicit sequence of decisions."""

    provider = "scripted"

    def __init__(self, decisions: list[ModelDecision]) -> None:
        self.decisions = decisions
        self.index = 0

    def decide(self, messages, tool_schemas, system_prompt) -> ModelDecision:  # type: ignore[no-untyped-def]
        del messages, tool_schemas, system_prompt
        if not self.decisions:
            return ModelDecision.final("No scripted decisions were provided.")
        decision = self.decisions[min(self.index, len(self.decisions) - 1)]
        self.index += 1
        return decision
