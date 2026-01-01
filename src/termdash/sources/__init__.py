from __future__ import annotations

from termdash.config import SourceConfig
from termdash.sources.base import DataSource
from termdash.sources.espn_scores import EspnScoresSource
from termdash.sources.f1_ergast import F1ErgastSource
from termdash.sources.gmail_unread import GmailUnreadSource
from termdash.sources.mcp_base import MCPSource
from termdash.sources.open_meteo import OpenMeteoSource
from termdash.sources.rss import RssSource

SOURCE_REGISTRY = {
    "open_meteo": OpenMeteoSource,
    "rss": RssSource,
    "mcp": MCPSource,
    "espn_scores": EspnScoresSource,
    "f1_ergast": F1ErgastSource,
    "gmail_unread": GmailUnreadSource,
}


def create_source(config: SourceConfig, *, mcp_client: object | None = None) -> DataSource:
    source_cls = SOURCE_REGISTRY.get(config.type)
    if source_cls is None:
        raise ValueError(f"Unknown source type: {config.type}")

    options = dict(config.options)
    if config.type == "mcp" and mcp_client is not None:
        options["client"] = mcp_client

    return source_cls(config.name, config.refresh_seconds, options)
