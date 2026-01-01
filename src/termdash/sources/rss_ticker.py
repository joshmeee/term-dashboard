from __future__ import annotations

from typing import Any

import feedparser
import httpx

from termdash.sources.base import DataPoint, DataSource


class RssTickerSource(DataSource):
    def __init__(self, name: str, refresh_seconds: int, options: dict) -> None:
        super().__init__(name, refresh_seconds, options)
        self._items: list[dict[str, str]] = []
        self._index = 0

    async def fetch(self) -> DataPoint:
        urls = _resolve_urls(self.options)
        if not urls:
            return DataPoint(title=self.name, value="Missing URL", status="error")

        async with httpx.AsyncClient(timeout=10) as client:
            items: list[dict[str, str]] = []
            for url in urls:
                items.extend(await _fetch_feed(client, url))

        filtered = _filter_items(items, self.options)
        max_items = int(self.options.get("max_items", 20))
        filtered = filtered[:max_items]
        if not filtered:
            return DataPoint(title=self.name, value="No entries", status="warn")

        if filtered != self._items:
            self._items = filtered
            self._index = 0

        lines = max(1, int(self.options.get("lines", 1)))
        selected = _select_items(self._items, self._index, lines)
        self._index = (self._index + lines) % len(self._items)

        show_source = bool(self.options.get("show_source", False))
        rendered = [_render_item(item, show_source) for item in selected]
        return DataPoint(title=self.name, value="\n".join(rendered), status="ok")


def _resolve_urls(options: dict[str, Any]) -> list[str]:
    urls = options.get("urls")
    if isinstance(urls, list) and urls:
        return [str(url) for url in urls if url]
    url = options.get("url")
    if url:
        return [str(url)]
    return []


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    response = await client.get(url)
    response.raise_for_status()
    feed = feedparser.parse(response.text)

    items: list[dict[str, str]] = []
    for entry in feed.entries or []:
        title = str(entry.get("title", "Untitled")).strip()
        link = str(entry.get("link", "")).strip()
        source = _extract_source(entry)
        items.append({"title": title, "link": link, "source": source})
    return items


def _extract_source(entry: dict[str, Any]) -> str:
    source = entry.get("source")
    if isinstance(source, dict):
        return str(source.get("title", "")).strip()
    return ""


def _filter_items(items: list[dict[str, str]], options: dict[str, Any]) -> list[dict[str, str]]:
    include_keywords = _normalize_list(options.get("include_keywords"))
    exclude_keywords = _normalize_list(options.get("exclude_keywords"))
    block_sources = _normalize_list(options.get("block_sources"))
    only_sources = _normalize_list(options.get("only_sources"))
    prefer_sources = _normalize_list(options.get("prefer_sources"))
    dedupe = bool(options.get("dedupe", True))

    filtered: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for item in items:
        title = item.get("title", "")
        title_lower = title.lower()
        source = item.get("source", "")
        source_lower = source.lower()
        link = item.get("link", "")
        domain_lower = _domain_from_link(link)

        if include_keywords and not _match_keywords(title_lower, include_keywords):
            continue
        if exclude_keywords and _match_keywords(title_lower, exclude_keywords):
            continue
        if block_sources and _match_source(block_sources, source_lower, domain_lower):
            continue
        if only_sources and not _match_source(only_sources, source_lower, domain_lower):
            continue
        if dedupe:
            key = title_lower.strip()
            if key in seen_titles:
                continue
            seen_titles.add(key)

        filtered.append(item)

    if prefer_sources:
        filtered.sort(key=lambda item: _prefer_rank(item, prefer_sources))

    return filtered


def _prefer_rank(item: dict[str, str], prefer_sources: list[str]) -> int:
    source = item.get("source", "").lower()
    link = item.get("link", "").lower()
    for i, pref in enumerate(prefer_sources):
        if pref in source or pref in link:
            return i
    return len(prefer_sources) + 1


def _normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip().lower()]
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return []


def _match_keywords(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _match_source(sources: list[str], source: str, domain: str) -> bool:
    return any(token in source or token in domain for token in sources)


def _domain_from_link(link: str) -> str:
    if "://" not in link:
        return ""
    domain = link.split("://", 1)[1].split("/", 1)[0]
    return domain.lower()


def _select_items(items: list[dict[str, str]], start: int, count: int) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for i in range(count):
        selected.append(items[(start + i) % len(items)])
    return selected


def _render_item(item: dict[str, str], show_source: bool) -> str:
    title = item.get("title", "Untitled")
    source = item.get("source", "")
    if show_source and source:
        return f"{title} ({source})"
    return title
