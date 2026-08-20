"""Local order lookup tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OrderRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._orders: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._orders is None:
            with self.path.open("r", encoding="utf-8") as handle:
                records = json.load(handle)
            if not isinstance(records, list):
                raise ValueError("orders.json must contain a list")
            self._orders = {str(item["order_id"]).upper(): item for item in records}
        return self._orders

    def query(self, order_id: str) -> dict[str, Any]:
        normalized = order_id.strip().upper()
        order = self._load().get(normalized)
        if order is None:
            return {"found": False, "order_id": normalized, "message": "Order was not found."}
        return {"found": True, "order": order}
