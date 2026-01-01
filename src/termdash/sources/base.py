from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DataPoint:
    title: str
    value: str
    status: str = "ok"
    detail: str = ""
    updated_at: datetime = field(default_factory=now_utc)


class DataSource:
    def __init__(self, name: str, refresh_seconds: int, options: dict[str, Any]) -> None:
        self.name = name
        self.refresh_seconds = refresh_seconds
        self.options = options

    async def fetch(self) -> DataPoint:
        raise NotImplementedError
