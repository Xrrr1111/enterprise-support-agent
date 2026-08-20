"""Optional OpenAI-compatible and Ollama adapters using only the standard library."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from enterprise_support_agent.llm.base import LLMError, ModelDecision


def _parse_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise LLMError(f"Model returned invalid JSON tool arguments: {error}") from error
        if isinstance(parsed, dict):
            return parsed
    raise LLMError("Model tool arguments must be a JSON object")


class OpenAICompatibleLLM:
    """Adapter for OpenAI's Chat Completions-compatible function calling API."""

    provider = "openai"

    def __init__(self, model: str, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def decide(self, messages, tool_schemas, system_prompt) -> ModelDecision:  # type: ignore[no-untyped-def]
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("OPENAI_API_KEY is required when ESA_LLM_PROVIDER=openai")
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system_prompt}, *self._messages(messages)],
            "tools": tool_schemas,
            "tool_choice": "auto",
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LLMError(f"OpenAI-compatible request failed: {error}") from error
        message = result["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            function = tool_calls[0]["function"]
            return ModelDecision.call(function["name"], _parse_arguments(function["arguments"]), tool_calls[0].get("id"))
        return ModelDecision.final(str(message.get("content", "")))

    @staticmethod
    def _messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        translated: list[dict[str, Any]] = []
        for message in messages:
            if message.get("role") == "assistant" and message.get("tool_call"):
                call = message["tool_call"]
                translated.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call.get("call_id") or f"call_{len(translated)}",
                                "type": "function",
                                "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])},
                            }
                        ],
                    }
                )
            elif message.get("role") == "tool":
                translated.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.get("tool_call_id") or f"call_{max(0, len(translated) - 1)}",
                        "content": str(message.get("content", "")),
                    }
                )
            else:
                translated.append({"role": message["role"], "content": str(message.get("content", ""))})
        return translated


class OllamaLLM:
    """Adapter for Ollama's native chat and function-calling endpoint."""

    provider = "ollama"

    def __init__(self, model: str, base_url: str, timeout_seconds: float = 120.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def decide(self, messages, tool_schemas, system_prompt) -> ModelDecision:  # type: ignore[no-untyped-def]
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system_prompt}, *OpenAICompatibleLLM._messages(messages)],
            "tools": tool_schemas,
            "options": {"temperature": 0},
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LLMError(f"Ollama request failed: {error}") from error
        message = result.get("message", {})
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            function = tool_calls[0].get("function", {})
            return ModelDecision.call(str(function.get("name", "")), _parse_arguments(function.get("arguments", {})))
        return ModelDecision.final(str(message.get("content", "")))
