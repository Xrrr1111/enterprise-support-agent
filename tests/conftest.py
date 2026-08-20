from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from enterprise_support_agent.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return replace(
        Settings(),
        tickets_path=tmp_path / "tickets.jsonl",
        logs_path=tmp_path / "logs",
        tool_timeout_seconds=0.05,
    )
