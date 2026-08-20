from enterprise_support_agent.agent.context import compact_context
from enterprise_support_agent.agent.state import AgentError, AgentState, ToolHistoryItem


def test_state_starts_with_user_message() -> None:
    state = AgentState.for_task("check order")
    assert state.current_task == "check order"
    assert state.messages == [{"role": "user", "content": "check order"}]
    assert state.turn_count == 0


def test_state_updates_messages_and_observations() -> None:
    state = AgentState.for_task("check")
    state.add_tool_call("query_order", {"order_id": "ORD-1001"}, "call-1")
    state.add_observation("query_order", {"ok": True}, "call-1")
    assert [message["role"] for message in state.messages] == ["user", "assistant", "tool"]
    assert state.observations == [{"ok": True}]


def test_state_serialization_and_compact_context() -> None:
    state = AgentState.for_task("task")
    state.errors.append(AgentError(1, "sample", "message", True))
    state.tool_history.append(ToolHistoryItem(1, "calculator", {"expression": "1+1"}, True, {}, 1.0, 1))
    assert state.to_dict()["errors"][0]["error_type"] == "sample"
    assert compact_context(state)["tools_used"] == ["calculator"]
