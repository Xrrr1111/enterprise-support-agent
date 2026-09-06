"""Explicit mutable state carried through every step of a run."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ToolHistoryItem:
    turn: int
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    observation: dict[str, Any]
    latency_ms: float
    attempts: int

    @property
    def signature(self) -> str:
        return f"{self.tool_name}:{json.dumps(self.arguments, ensure_ascii=False, sort_keys=True)}"


@dataclass(slots=True)
class AgentError:
    turn: int
    error_type: str
    message: str
    recoverable: bool


@dataclass(slots=True)
class AgentState:
    messages: list[dict[str, Any]]
    current_task: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_history: list[ToolHistoryItem] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    errors: list[AgentError] = field(default_factory=list)
    final_answer: str | None = None
    stop_reason: str | None = None
    latency_ms: float = 0.0

    @classmethod
    def for_task(cls, task: str) -> "AgentState":
        return cls(messages=[{"role": "user", "content": task}], current_task=task)

    def add_tool_call(self, name: str, arguments: dict[str, Any], call_id: str | None) -> None:
        self.messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_call": {"name": name, "arguments": arguments, "call_id": call_id},
            }
        )

    def add_observation(self, name: str, observation: dict[str, Any], call_id: str | None) -> None:
        self.observations.append(observation)
        self.messages.append(
            {
                "role": "tool",
                "name": name,
                "tool_call_id": call_id,
                "content": json.dumps(observation, ensure_ascii=False),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        seen: set[tuple[str, int | None]] = set()
        for observation in self.observations:
            data = observation.get("data", {}) if isinstance(observation, dict) else {}
            for result in data.get("results", []) if isinstance(data, dict) else []:
                source = str(result.get("source") or result.get("document_id") or "")
                page = result.get("page")
                key = (source, page)
                if source and key not in seen:
                    seen.add(key)
                    sources.append(
                        {
                            "source": source,
                            "page": page,
                            "document_id": result.get("document_id"),
                            "score": result.get("score"),
                        }
                    )
        return {
            "trace_id": self.trace_id,
            "started_at": self.started_at,
            "current_task": self.current_task,
            "messages": self.messages,
            "tool_history": [asdict(item) for item in self.tool_history],
            "observations": self.observations,
            "turn_count": self.turn_count,
            "errors": [asdict(item) for item in self.errors],
            "final_answer": self.final_answer,
            "stop_reason": self.stop_reason,
            "latency_ms": round(self.latency_ms, 3),
            "sources": sources,
        }
