"""Durable local ticket creation for escalation paths."""

from __future__ import annotations

import json
import hashlib
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STORE_LOCK = threading.Lock()


class TicketStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = STORE_LOCK

    def create(self, user_request: str, reason: str, priority: str, idempotency_key: str) -> dict[str, Any]:
        clean_key = idempotency_key.strip()
        if not clean_key:
            raise ValueError("idempotency_key must not be empty")
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "user_request": user_request.strip(),
                    "reason": reason.strip(),
                    "priority": priority,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        ticket = {
            "ticket_id": f"TKT-{uuid.uuid4().hex[:10].upper()}",
            "user_request": user_request.strip(),
            "reason": reason.strip(),
            "priority": priority,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": clean_key,
            "request_fingerprint": fingerprint,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self.path.exists():
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    existing = json.loads(line)
                    if existing.get("idempotency_key") != clean_key:
                        continue
                    if existing.get("request_fingerprint") != fingerprint:
                        raise ValueError("idempotency_key was already used for a different request")
                    return {"ticket": existing, "deduplicated": True}
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(ticket, ensure_ascii=False) + "\n")
        return {"ticket": ticket, "deduplicated": False}
