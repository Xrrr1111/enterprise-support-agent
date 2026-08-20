"""Structured JSONL trace events plus one readable JSON run summary."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any

from enterprise_support_agent.agent.state import AgentState


def configure_application_logger(log_directory: Path) -> logging.Logger:
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("enterprise_support_agent")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_directory / "application.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


class TraceRecorder:
    def __init__(self, directory: Path, trace_id: str, enabled: bool = True) -> None:
        self.directory = directory
        self.trace_id = trace_id
        self.enabled = enabled
        self._lock = Lock()
        self.events_path = directory / f"trace_{trace_id}.jsonl"
        self.summary_path = directory / f"trace_{trace_id}.json"
        if enabled:
            directory.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, turn: int, **details: Any) -> None:
        if not self.enabled:
            return
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": self.trace_id,
            "turn": turn,
            "event": event,
            **details,
        }
        with self._lock, self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def finalize(self, state: AgentState) -> None:
        if not self.enabled:
            return
        with self._lock, self.summary_path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2, default=str)
