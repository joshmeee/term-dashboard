from __future__ import annotations

import feedparser
import httpx

from termdash.sources.base import DataPoint, DataSource


class RssTickerSource(DataSource):
    def __init__(self, name: str, refresh_seconds: int, options: dict) -> None:
        super().__init__(name, refresh_seconds, options)
        self._items: list[str] = []
        self._index = 0

    async def fetch(self) -> DataPoint:
        url = self.options.get("url")
        if not url:
            return DataPoint(title=self.name, value="Missing URL", status="error")

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

        entries = feed.entries or []
        max_items = int(self.options.get("max_items", 10))
        items = [entry.get("title", "Untitled") for entry in entries[:max_items]]
        if not items:
            return DataPoint(title=self.name, value="No entries", status="warn")

        if items != self._items:
            self._items = items
            self._index = 0

        item = self._items[self._index % len(self._items)]
        self._index += 1

        return DataPoint(title=self.name, value=item, status="ok")
