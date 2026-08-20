"""Durable local ticket creation for escalation paths."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TicketStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def create(self, user_request: str, reason: str, priority: str) -> dict[str, Any]:
        ticket = {
            "ticket_id": f"TKT-{uuid.uuid4().hex[:10].upper()}",
            "user_request": user_request.strip(),
            "reason": reason.strip(),
            "priority": priority,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(ticket, ensure_ascii=False) + "\n")
        return {"ticket": ticket}
