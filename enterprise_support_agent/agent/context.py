"""Helpers for presenting state to model adapters and human debuggers."""

from __future__ import annotations

from typing import Any

from enterprise_support_agent.agent.state import AgentState


def compact_context(state: AgentState) -> dict[str, Any]:
    """A serializable diagnostic view that excludes implementation objects."""

    return {
        "task": state.current_task,
        "turn": state.turn_count,
        "messages": state.messages,
        "tools_used": [item.tool_name for item in state.tool_history],
        "errors": [error.error_type for error in state.errors],
    }
