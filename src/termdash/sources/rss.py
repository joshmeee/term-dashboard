from __future__ import annotations

import feedparser
import httpx

from termdash.sources.base import DataPoint, DataSource


class RssSource(DataSource):
    async def fetch(self) -> DataPoint:
        url = self.options.get("url")
        if not url:
            return DataPoint(title=self.name, value="Missing URL", status="error")

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

        if not feed.entries:
            return DataPoint(title=self.name, value="No entries", status="warn")

        entry = feed.entries[0]
        title = entry.get("title", "Untitled")
        return DataPoint(title=self.name, value=title, status="ok")
