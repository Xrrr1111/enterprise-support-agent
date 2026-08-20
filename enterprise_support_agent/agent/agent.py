"""High-level composition root used by the CLI, tests, and evaluation runner."""

from __future__ import annotations

from pathlib import Path

from enterprise_support_agent.agent.harness import ToolHarness
from enterprise_support_agent.agent.loop import AgentLoop
from enterprise_support_agent.agent.state import AgentState
from enterprise_support_agent.agent.trace import TraceRecorder, configure_application_logger
from enterprise_support_agent.config import Settings
from enterprise_support_agent.llm.base import LLMClient
from enterprise_support_agent.llm.factory import create_llm
from enterprise_support_agent.tools.registry import ToolRegistry, build_default_registry


class EnterpriseSupportAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        model: LLMClient | None = None,
        registry: ToolRegistry | None = None,
        trace_enabled: bool = True,
    ) -> None:
        self.settings = settings or Settings()
        self.model = model or create_llm(self.settings)
        self.registry = registry or build_default_registry(self.settings)
        self.trace_enabled = trace_enabled
        self.logger = configure_application_logger(self.settings.logs_path)
        self.system_prompt = self._read_prompt(self.settings.system_prompt_path)

    @staticmethod
    def _read_prompt(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def run(self, task: str) -> AgentState:
        if not task or not task.strip():
            raise ValueError("task must not be empty")
        state = AgentState.for_task(task.strip())
        trace = TraceRecorder(self.settings.logs_path, state.trace_id, enabled=self.trace_enabled)
        harness = ToolHarness(
            registry=self.registry,
            timeout_seconds=self.settings.tool_timeout_seconds,
            retries=self.settings.tool_retries,
        )
        loop = AgentLoop(
            model=self.model,
            registry=self.registry,
            harness=harness,
            system_prompt=self.system_prompt,
            max_turns=self.settings.max_turns,
            model_retries=self.settings.model_retries,
            repeated_call_threshold=self.settings.repeated_call_threshold,
            no_progress_threshold=self.settings.no_progress_threshold,
            logger=self.logger,
        )
        result = loop.run(state, trace)
        self.logger.info(
            "trace_id=%s stop_reason=%s turns=%s latency_ms=%.3f",
            result.trace_id,
            result.stop_reason,
            result.turn_count,
            result.latency_ms,
        )
        return result
