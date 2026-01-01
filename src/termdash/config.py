from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceConfig:
    name: str
    type: str
    refresh_seconds: int = 300
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    title: str = "Term Dashboard"
    refresh_ui_seconds: float = 2.0
    sources: list[SourceConfig] = field(default_factory=list)


def default_config() -> DashboardConfig:
    return DashboardConfig(
        title="Term Dashboard",
        refresh_ui_seconds=1.5,
        sources=[
            SourceConfig(
                name="Local Weather",
                type="open_meteo",
                refresh_seconds=300,
                options={
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "timezone": "auto",
                },
            ),
            SourceConfig(
                name="Top News",
                type="rss",
                refresh_seconds=300,
                options={"url": "https://news.ycombinator.com/rss"},
            ),
        ],
    )


def load_config(path: Path | None) -> DashboardConfig:
    if path is None or not path.exists():
        return default_config()

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dashboard = data.get("dashboard", {})
    sources_data = data.get("sources", [])
    env = dict(os.environ)

    sources: list[SourceConfig] = []
    for item in sources_data:
        if not item:
            continue
        sources.append(
            SourceConfig(
                name=item.get("name") or item.get("type", "source"),
                type=item.get("type", "unknown"),
                refresh_seconds=int(item.get("refresh_seconds", 300)),
                options=_resolve_options(item.get("options", {}) or {}, env),
            )
        )

    return DashboardConfig(
        title=dashboard.get("title", "Term Dashboard"),
        refresh_ui_seconds=float(dashboard.get("refresh_ui_seconds", 2.0)),
        sources=sources,
    )


def _resolve_options(options: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in options.items():
        if isinstance(value, str):
            resolved[key] = _expand_env(value, env)
        else:
            resolved[key] = value
    return resolved


def _expand_env(value: str, env: dict[str, str]) -> str:
    if value.startswith("${") and value.endswith("}"):
        name = value[2:-1]
        return env.get(name, value)
    return value
