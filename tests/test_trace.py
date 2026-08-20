from __future__ import annotations

import json

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.llm.mock import MockLLM


def test_trace_contains_decision_tool_observation_and_stop(settings) -> None:
    state = EnterpriseSupportAgent(settings, MockLLM(), trace_enabled=True).run("Where is ORD-1001?")
    events_path = settings.logs_path / f"trace_{state.trace_id}.jsonl"
    summary_path = settings.logs_path / f"trace_{state.trace_id}.json"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    names = [event["event"] for event in events]
    assert names[0] == "run_started"
    assert "model_decision" in names
    assert "tool_call" in names
    assert "tool_result" in names
    assert names[-1] == "run_stopped"
    assert json.loads(summary_path.read_text(encoding="utf-8"))["stop_reason"] == "completed"


def test_trace_records_latency_and_final_result(settings) -> None:
    state = EnterpriseSupportAgent(settings, MockLLM(), trace_enabled=True).run("Calculate: 7 * 6")
    summary = json.loads((settings.logs_path / f"trace_{state.trace_id}.json").read_text(encoding="utf-8"))
    assert summary["latency_ms"] >= 0
    assert "42" in summary["final_answer"]
