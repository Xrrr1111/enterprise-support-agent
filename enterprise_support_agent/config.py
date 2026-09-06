"""Environment-backed configuration with safe, local-first defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings. All paths are relative to the repository by default."""

    llm_provider: str = os.getenv("ESA_LLM_PROVIDER", "mock")
    llm_model: str = os.getenv("ESA_LLM_MODEL", "gpt-4.1-mini")
    api_base_url: str = os.getenv("ESA_API_BASE_URL", "https://api.openai.com/v1")
    ollama_base_url: str = os.getenv("ESA_OLLAMA_BASE_URL", "http://localhost:11434")
    max_turns: int = _env_int("ESA_MAX_TURNS", 8)
    model_retries: int = _env_int("ESA_MODEL_RETRIES", 1)
    tool_retries: int = _env_int("ESA_TOOL_RETRIES", 1)
    tool_timeout_seconds: float = _env_float("ESA_TOOL_TIMEOUT_SECONDS", 3.0)
    repeated_call_threshold: int = _env_int("ESA_REPEATED_CALL_THRESHOLD", 2)
    no_progress_threshold: int = _env_int("ESA_NO_PROGRESS_THRESHOLD", 3)
    rag_top_k: int = _env_int("ESA_RAG_TOP_K", 3)
    orders_path: Path = PROJECT_ROOT / "data" / "orders.json"
    policies_path: Path = PROJECT_ROOT / "data" / "policies"
    tickets_path: Path = PROJECT_ROOT / "data" / "tickets.jsonl"
    logs_path: Path = PROJECT_ROOT / "logs"
    system_prompt_path: Path = PROJECT_ROOT / "prompts" / "system_prompt.txt"
    knowledge_uploads_path: Path = PROJECT_ROOT / "data" / "knowledge_uploads"

    def __post_init__(self) -> None:
        if self.max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        if self.tool_timeout_seconds <= 0:
            raise ValueError("tool_timeout_seconds must be positive")
        if self.repeated_call_threshold < 2:
            raise ValueError("repeated_call_threshold must be at least 2")
