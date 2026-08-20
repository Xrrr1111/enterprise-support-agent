"""Small internal protocol that keeps the agent independent of model vendors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments, "call_id": self.call_id}


@dataclass(frozen=True, slots=True)
class ModelDecision:
    """Exactly one next action: call one tool, or return a final answer."""

    kind: Literal["tool_call", "final"]
    content: str = ""
    tool_call: ToolCall | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def call(cls, name: str, arguments: dict[str, Any], call_id: str | None = None) -> "ModelDecision":
        return cls(kind="tool_call", tool_call=ToolCall(name, arguments, call_id))

    @classmethod
    def final(cls, content: str) -> "ModelDecision":
        return cls(kind="final", content=content)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind, "content": self.content}
        if self.tool_call is not None:
            result["tool_call"] = self.tool_call.to_dict()
        return result


class LLMClient(Protocol):
    provider: str

    def decide(
        self,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        system_prompt: str,
    ) -> ModelDecision:
        """Return the next model decision in the agent loop."""


class LLMError(RuntimeError):
    """Raised when a provider cannot produce a valid decision."""
