"""Tool contracts and a deliberately small JSON-schema validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class ToolValidationError(ValueError):
    """Raised before execution when a model supplies invalid tool arguments."""


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
    retryable_exceptions: tuple[type[BaseException], ...] = (OSError, TimeoutError)

    def as_llm_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(slots=True)
class ToolExecution:
    name: str
    arguments: dict[str, Any]
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_type: str | None = None
    attempts: int = 1
    latency_ms: float = 0.0

    def to_observation(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.name,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "attempts": self.attempts,
            "latency_ms": round(self.latency_ms, 3),
        }


def validate_arguments(schema: dict[str, Any], arguments: Any) -> dict[str, Any]:
    """Validate the JSON-schema subset used by this project's four tools."""

    if not isinstance(arguments, dict):
        raise ToolValidationError("arguments must be a JSON object")
    required = schema.get("required", [])
    missing = [name for name in required if name not in arguments]
    if missing:
        raise ToolValidationError(f"missing required argument(s): {', '.join(missing)}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        extras = sorted(set(arguments) - set(properties))
        if extras:
            raise ToolValidationError(f"unexpected argument(s): {', '.join(extras)}")

    for name, value in arguments.items():
        if name not in properties:
            continue
        rule = properties[name]
        expected = rule.get("type")
        valid_type = (
            (expected == "string" and isinstance(value, str))
            or (expected == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (expected == "boolean" and isinstance(value, bool))
            or expected is None
        )
        if not valid_type:
            raise ToolValidationError(f"argument '{name}' must be {expected}")
        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                raise ToolValidationError(f"argument '{name}' is too short")
            if "maxLength" in rule and len(value) > rule["maxLength"]:
                raise ToolValidationError(f"argument '{name}' is too long")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in rule and value < rule["minimum"]:
                raise ToolValidationError(f"argument '{name}' must be >= {rule['minimum']}")
            if "maximum" in rule and value > rule["maximum"]:
                raise ToolValidationError(f"argument '{name}' must be <= {rule['maximum']}")
        if "enum" in rule and value not in rule["enum"]:
            allowed = ", ".join(map(str, rule["enum"]))
            raise ToolValidationError(f"argument '{name}' must be one of: {allowed}")
    return arguments
