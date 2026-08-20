"""Validated, timed, retried, observable tool execution boundary."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from enterprise_support_agent.agent.trace import TraceRecorder
from enterprise_support_agent.tools.base import ToolExecution, ToolValidationError, validate_arguments
from enterprise_support_agent.tools.registry import ToolRegistry


class ToolHarness:
    def __init__(self, registry: ToolRegistry, timeout_seconds: float, retries: int) -> None:
        self.registry = registry
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def execute(
        self,
        name: str,
        arguments: Any,
        turn: int,
        trace: TraceRecorder,
    ) -> ToolExecution:
        started = time.perf_counter()
        tool = self.registry.get(name)
        if tool is None:
            result = ToolExecution(
                name=name,
                arguments=arguments if isinstance(arguments, dict) else {},
                ok=False,
                error=f"Unknown tool: {name}",
                error_type="invalid_tool",
            )
            result.latency_ms = (time.perf_counter() - started) * 1000
            trace.record("tool_result", turn, **result.to_observation(), arguments=arguments)
            return result
        try:
            validated = validate_arguments(tool.parameters, arguments)
        except ToolValidationError as error:
            result = ToolExecution(
                name=name,
                arguments=arguments if isinstance(arguments, dict) else {},
                ok=False,
                error=str(error),
                error_type="invalid_arguments",
            )
            result.latency_ms = (time.perf_counter() - started) * 1000
            trace.record("tool_result", turn, **result.to_observation(), arguments=arguments)
            return result

        max_attempts = self.retries + 1
        for attempt in range(1, max_attempts + 1):
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"tool-{name}")
            future = executor.submit(tool.handler, **validated)
            try:
                data = future.result(timeout=self.timeout_seconds)
                if not isinstance(data, dict):
                    raise TypeError(f"Tool {name} must return a dictionary")
                result = ToolExecution(name, validated, True, data=data, attempts=attempt)
                result.latency_ms = (time.perf_counter() - started) * 1000
                executor.shutdown(wait=False, cancel_futures=True)
                trace.record("tool_result", turn, **result.to_observation(), arguments=validated)
                return result
            except FutureTimeoutError:
                future.cancel()
                error: BaseException = TimeoutError(f"Tool exceeded {self.timeout_seconds:.3f}s timeout")
                error_type = "tool_timeout"
                retryable = True
            except BaseException as caught:  # boundary converts failures into observations
                error = caught
                error_type = "tool_exception"
                retryable = isinstance(caught, tool.retryable_exceptions)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            trace.record(
                "tool_attempt_failed",
                turn,
                tool=name,
                arguments=validated,
                attempt=attempt,
                error_type=error_type,
                error=str(error),
                retrying=retryable and attempt < max_attempts,
            )
            if not retryable or attempt == max_attempts:
                result = ToolExecution(
                    name=name,
                    arguments=validated,
                    ok=False,
                    error=str(error),
                    error_type=error_type,
                    attempts=attempt,
                )
                result.latency_ms = (time.perf_counter() - started) * 1000
                trace.record("tool_result", turn, **result.to_observation(), arguments=validated)
                return result
        raise AssertionError("unreachable")
