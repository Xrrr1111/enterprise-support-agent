from __future__ import annotations

from dataclasses import replace

import pytest

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.llm.base import LLMError, ModelDecision
from enterprise_support_agent.llm.mock import MockLLM, ScriptedLLM
from enterprise_support_agent.tools.base import ToolDefinition
from enterprise_support_agent.tools.registry import build_default_registry


def test_mock_model_runs_order_policy_chain(settings) -> None:
    state = EnterpriseSupportAgent(settings, MockLLM(), trace_enabled=False).run(
        "For ORD-1002, explain the shipping policy"
    )
    assert [item.tool_name for item in state.tool_history] == ["query_order", "search_policy"]


def test_mock_model_understands_chinese_delivery_policy_request(settings) -> None:
    state = EnterpriseSupportAgent(settings, trace_enabled=False).run("检查订单 ORD-1002，并解释配送政策")
    assert [item.tool_name for item in state.tool_history] == ["query_order", "search_policy"]
    assert state.to_dict()["sources"]
    assert state.turn_count == 3
    assert state.stop_reason == "completed"


def test_repeated_tool_call_detector_stops_loop(settings) -> None:
    call = ModelDecision.call("query_order", {"order_id": "ORD-1001"})
    model = ScriptedLLM([call])
    state = EnterpriseSupportAgent(settings, model, trace_enabled=False).run("loop")
    assert state.stop_reason == "repeated_tool_call"
    assert len(state.tool_history) == 1
    assert state.errors[-1].error_type == "repeated_tool_call"


def test_max_turns_stops_unfinished_run(settings) -> None:
    limited = replace(settings, max_turns=2, repeated_call_threshold=3)
    model = ScriptedLLM(
        [
            ModelDecision.call("query_order", {"order_id": "ORD-1001"}),
            ModelDecision.call("query_order", {"order_id": "ORD-1002"}),
            ModelDecision.final("unreachable"),
        ]
    )
    state = EnterpriseSupportAgent(limited, model, trace_enabled=False).run("exhaust")
    assert state.stop_reason == "max_turns"
    assert state.turn_count == 2


def test_no_progress_detector_uses_observation_fingerprints(settings) -> None:
    schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    registry = build_default_registry(settings)
    registry.register(ToolDefinition("constant", "", schema, lambda value: {"same": True}))
    configured = replace(settings, no_progress_threshold=2, repeated_call_threshold=3)
    model = ScriptedLLM(
        [
            ModelDecision.call("constant", {"value": 1}),
            ModelDecision.call("constant", {"value": 2}),
        ]
    )
    state = EnterpriseSupportAgent(configured, model, registry, trace_enabled=False).run("no progress")
    assert state.stop_reason == "no_progress"
    assert len(state.tool_history) == 2


def test_invalid_tool_observation_allows_model_redecision(settings) -> None:
    model = ScriptedLLM(
        [ModelDecision.call("not_real", {}), ModelDecision.final("Recovered after observing invalid tool.")]
    )
    state = EnterpriseSupportAgent(settings, model, trace_enabled=False).run("recover")
    assert state.stop_reason == "completed"
    assert state.errors[0].error_type == "invalid_tool"
    assert "Recovered" in state.final_answer


def test_model_retry_succeeds(settings) -> None:
    class FlakyModel:
        provider = "flaky"

        def __init__(self) -> None:
            self.calls = 0

        def decide(self, messages, tool_schemas, system_prompt):
            self.calls += 1
            if self.calls == 1:
                raise LLMError("temporary")
            return ModelDecision.final("Recovered model")

    model = FlakyModel()
    state = EnterpriseSupportAgent(settings, model, trace_enabled=False).run("retry model")
    assert state.stop_reason == "completed"
    assert model.calls == 2
    assert state.errors[0].recoverable is True


def test_model_retry_exhaustion_stops(settings) -> None:
    class BrokenModel:
        provider = "broken"

        def decide(self, messages, tool_schemas, system_prompt):
            raise LLMError("offline")

    state = EnterpriseSupportAgent(settings, BrokenModel(), trace_enabled=False).run("fail model")
    assert state.stop_reason == "model_error"
    assert len(state.errors) == settings.model_retries + 1


def test_empty_task_is_rejected(settings) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        EnterpriseSupportAgent(settings, MockLLM(), trace_enabled=False).run("  ")
