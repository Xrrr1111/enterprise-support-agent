"""The explicit LLM -> Tool -> Observation -> LLM execution loop."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from enterprise_support_agent.agent.harness import ToolHarness
from enterprise_support_agent.agent.state import AgentError, AgentState, ToolHistoryItem
from enterprise_support_agent.agent.trace import TraceRecorder
from enterprise_support_agent.llm.base import LLMClient, LLMError, ModelDecision
from enterprise_support_agent.tools.registry import ToolRegistry


class AgentLoop:
    def __init__(
        self,
        model: LLMClient,
        registry: ToolRegistry,
        harness: ToolHarness,
        system_prompt: str,
        max_turns: int,
        model_retries: int,
        repeated_call_threshold: int,
        no_progress_threshold: int,
        logger: logging.Logger,
    ) -> None:
        self.model = model
        self.registry = registry
        self.harness = harness
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.model_retries = model_retries
        self.repeated_call_threshold = repeated_call_threshold
        self.no_progress_threshold = no_progress_threshold
        self.logger = logger

    def run(self, state: AgentState, trace: TraceRecorder) -> AgentState:
        run_started = time.perf_counter()
        trace.record("run_started", 0, task=state.current_task, model_provider=self.model.provider)
        previous_observation_fingerprint: str | None = None
        no_progress_count = 0

        for turn in range(1, self.max_turns + 1):
            state.turn_count = turn
            decision, model_latency = self._decide(state, trace)
            if decision is None:
                return self._stop(state, trace, "model_error", run_started)
            trace.record("model_decision", turn, decision=decision.to_dict(), latency_ms=round(model_latency, 3))

            if decision.kind == "final":
                if not decision.content.strip():
                    state.errors.append(AgentError(turn, "empty_final_answer", "Model returned an empty final answer", False))
                    return self._stop(state, trace, "invalid_model_response", run_started)
                state.final_answer = decision.content.strip()
                return self._stop(state, trace, "completed", run_started)

            call = decision.tool_call
            if call is None or not call.name:
                state.errors.append(AgentError(turn, "invalid_model_response", "Tool decision has no tool call", False))
                return self._stop(state, trace, "invalid_model_response", run_started)

            signature = f"{call.name}:{json.dumps(call.arguments, ensure_ascii=False, sort_keys=True)}"
            consecutive = 1
            for history in reversed(state.tool_history):
                if history.signature != signature:
                    break
                consecutive += 1
            if consecutive >= self.repeated_call_threshold:
                state.errors.append(
                    AgentError(turn, "repeated_tool_call", f"Repeated tool call detected: {signature}", False)
                )
                trace.record("loop_detected", turn, signature=signature, consecutive=consecutive)
                return self._stop(state, trace, "repeated_tool_call", run_started)

            trace.record("tool_call", turn, tool=call.name, arguments=call.arguments, call_id=call.call_id)
            state.add_tool_call(call.name, call.arguments, call.call_id)
            execution = self.harness.execute(call.name, call.arguments, turn, trace)
            observation = execution.to_observation()
            state.add_observation(call.name, observation, call.call_id)
            state.tool_history.append(
                ToolHistoryItem(
                    turn=turn,
                    tool_name=call.name,
                    arguments=execution.arguments,
                    ok=execution.ok,
                    observation=observation,
                    latency_ms=execution.latency_ms,
                    attempts=execution.attempts,
                )
            )
            if not execution.ok:
                state.errors.append(
                    AgentError(turn, execution.error_type or "tool_error", execution.error or "Unknown tool error", True)
                )

            fingerprint = json.dumps(
                {"ok": execution.ok, "data": execution.data, "error_type": execution.error_type},
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            if fingerprint == previous_observation_fingerprint:
                no_progress_count += 1
            else:
                no_progress_count = 1
                previous_observation_fingerprint = fingerprint
            if no_progress_count >= self.no_progress_threshold:
                state.errors.append(AgentError(turn, "no_progress", "Tool observations are no longer changing", False))
                trace.record("no_progress_detected", turn, repeated_observations=no_progress_count)
                return self._stop(state, trace, "no_progress", run_started)

        return self._stop(state, trace, "max_turns", run_started)

    def _decide(self, state: AgentState, trace: TraceRecorder) -> tuple[ModelDecision | None, float]:
        started = time.perf_counter()
        for attempt in range(1, self.model_retries + 2):
            try:
                decision = self.model.decide(state.messages, self.registry.schemas(), self.system_prompt)
                if not isinstance(decision, ModelDecision):
                    raise LLMError("Adapter returned a non-ModelDecision value")
                return decision, (time.perf_counter() - started) * 1000
            except Exception as error:
                recoverable = attempt <= self.model_retries
                state.errors.append(AgentError(state.turn_count, "model_error", str(error), recoverable))
                trace.record(
                    "model_attempt_failed",
                    state.turn_count,
                    attempt=attempt,
                    error=str(error),
                    retrying=recoverable,
                )
                if not recoverable:
                    self.logger.exception("Model decision failed after retries")
                    return None, (time.perf_counter() - started) * 1000
        return None, (time.perf_counter() - started) * 1000

    @staticmethod
    def _stop(state: AgentState, trace: TraceRecorder, reason: str, started: float) -> AgentState:
        state.stop_reason = reason
        state.latency_ms = (time.perf_counter() - started) * 1000
        if state.final_answer is None:
            state.final_answer = {
                "max_turns": "I could not finish within the allowed number of turns.",
                "repeated_tool_call": "I stopped because the same tool call repeated without progress.",
                "no_progress": "I stopped because repeated observations showed no progress.",
                "model_error": "I could not reach the language model after retries.",
                "invalid_model_response": "I stopped because the model returned an invalid response.",
            }.get(reason, "I could not complete the request.")
        trace.record(
            "run_stopped",
            state.turn_count,
            stop_reason=reason,
            final_answer=state.final_answer,
            latency_ms=round(state.latency_ms, 3),
        )
        trace.finalize(state)
        return state
