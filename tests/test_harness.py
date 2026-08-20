from __future__ import annotations

import time
from pathlib import Path

from enterprise_support_agent.agent.harness import ToolHarness
from enterprise_support_agent.agent.trace import TraceRecorder
from enterprise_support_agent.tools.base import ToolDefinition
from enterprise_support_agent.tools.registry import ToolRegistry


SCHEMA = {
    "type": "object",
    "properties": {"value": {"type": "integer"}},
    "required": ["value"],
    "additionalProperties": False,
}


def harness(tool: ToolDefinition | None, tmp_path: Path, timeout: float = 0.03, retries: int = 1):
    registry = ToolRegistry([tool] if tool else [])
    return ToolHarness(registry, timeout, retries), TraceRecorder(tmp_path, "test", enabled=False)


def test_invalid_tool_becomes_observation(tmp_path: Path) -> None:
    target, trace = harness(None, tmp_path)
    result = target.execute("missing", {}, 1, trace)
    assert result.ok is False
    assert result.error_type == "invalid_tool"


def test_invalid_arguments_never_execute_handler(tmp_path: Path) -> None:
    calls = {"count": 0}

    def handler(value: int):
        calls["count"] += 1
        return {"value": value}

    target, trace = harness(ToolDefinition("tool", "", SCHEMA, handler), tmp_path)
    result = target.execute("tool", {"value": "wrong"}, 1, trace)
    assert result.error_type == "invalid_arguments"
    assert calls["count"] == 0


def test_retry_recovers_retryable_exception(tmp_path: Path) -> None:
    calls = {"count": 0}

    def flaky(value: int):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("temporary")
        return {"value": value}

    target, trace = harness(ToolDefinition("flaky", "", SCHEMA, flaky), tmp_path, retries=1)
    result = target.execute("flaky", {"value": 4}, 1, trace)
    assert result.ok is True
    assert result.attempts == 2


def test_non_retryable_exception_is_captured(tmp_path: Path) -> None:
    def broken(value: int):
        raise ValueError(value)

    target, trace = harness(ToolDefinition("broken", "", SCHEMA, broken), tmp_path, retries=3)
    result = target.execute("broken", {"value": 4}, 1, trace)
    assert result.ok is False
    assert result.error_type == "tool_exception"
    assert result.attempts == 1


def test_timeout_is_captured(tmp_path: Path) -> None:
    def slow(value: int):
        time.sleep(0.05)
        return {"value": value}

    target, trace = harness(ToolDefinition("slow", "", SCHEMA, slow), tmp_path, timeout=0.001, retries=0)
    result = target.execute("slow", {"value": 1}, 1, trace)
    assert result.ok is False
    assert result.error_type == "tool_timeout"
