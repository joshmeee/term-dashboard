from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

DEFAULT_CONFIG_DIR = Path.home() / ".termdash"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULTS_PATH = DEFAULT_CONFIG_DIR / "defaults.yaml"


def ensure_user_config(config_path: Path | None) -> Path:
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        return path

    print("No config found. Let's create one.")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _interactive_setup()
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"Config written to {path}")
    return path


def _interactive_setup() -> dict[str, Any]:
    defaults = _load_defaults()
    city, state, latitude, longitude = _collect_location()
    favorites = _collect_favorites(defaults.get("favorites", {}))

    local_query = _google_news_query(f"{city} {state}")
    state_query = _google_news_query(f"{state} government")
    federal_query = _google_news_query("US federal government")
    topic_query = _google_news_query(_topic_query(defaults))
    sports_query = _google_news_query(_sports_query_string(favorites, defaults))

    return {
        "dashboard": {"title": "Term Dashboard", "refresh_ui_seconds": 1.5},
        "sources": [
            {
                "name": "Local Weather",
                "type": "open_meteo",
                "refresh_seconds": 300,
                "options": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": "auto",
                },
            },
            {
                "name": "Live Sports",
                "type": "espn_scores",
                "refresh_seconds": 60,
                "options": {
                    "preset": "all_major",
                    "show_only_favorites": False,
                    "highlight_favorites": True,
                    "favorites": favorites,
                },
            },
            {
                "name": "Live Summary",
                "type": "espn_summary",
                "refresh_seconds": 120,
                "options": {"preset": "all_major"},
            },
            {
                "name": "F1 Status",
                "type": "f1_ergast",
                "refresh_seconds": 300,
            },
            {
                "name": "News Ticker",
                "type": "rss_ticker",
                "refresh_seconds": 15,
                "options": {
                    "auto_lines": True,
                    "min_lines": 2,
                    "max_lines": 6,
                    "show_source": True,
                    "max_items": 40,
                    "block_sources": defaults.get("block_sources", ["msnbc", "al jazeera"]),
                    "prefer_sources": defaults.get("prefer_sources", ["fox news"]),
                    "urls": [local_query, state_query, federal_query, topic_query],
                },
            },
            {
                "name": "Sports News Ticker",
                "type": "rss_ticker",
                "refresh_seconds": 20,
                "options": {
                    "auto_lines": True,
                    "min_lines": 2,
                    "max_lines": 4,
                    "show_source": True,
                    "max_items": 30,
                    "block_sources": defaults.get("block_sources", ["msnbc", "al jazeera"]),
                    "prefer_sources": defaults.get("prefer_sources", ["fox news"]),
                    "urls": [sports_query],
                },
            },
        ],
    }


def _collect_location() -> tuple[str, str, float, float]:
    use_ip = _prompt_bool("Detect city/state from IP? (y/n) ", default=True)
    if use_ip:
        city, state, latitude, longitude = _lookup_location()
        if city and state:
            print(f"Detected location: {city}, {state}")
            confirm = _prompt_bool("Use this location? (y/n) ", default=True)
            if confirm:
                return city, state, latitude, longitude

    city = _prompt_text("City: ")
    state = _prompt_text("State (abbrev or full): ")
    latitude = _prompt_float("Latitude: ")
    longitude = _prompt_float("Longitude: ")
    return city, state, latitude, longitude


def _lookup_location() -> tuple[str, str, float, float]:
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("https://ipapi.co/json/")
            response.raise_for_status()
            data = response.json()
        city = str(data.get("city", "")).strip()
        state = str(data.get("region", "")).strip()
        latitude = float(data.get("latitude", 0.0))
        longitude = float(data.get("longitude", 0.0))
        return city, state, latitude, longitude
    except Exception:
        return "", "", 0.0, 0.0


def _collect_favorites(defaults: dict[str, list[str]]) -> dict[str, list[str]]:
    print("Enter favorite team abbreviations (comma separated). Leave blank to skip.")
    return {
        "nfl": _prompt_list("NFL teams (e.g., NE): ", defaults.get("nfl", [])),
        "nba": _prompt_list("NBA teams (e.g., BOS): ", defaults.get("nba", [])),
        "mlb": _prompt_list("MLB teams (e.g., BOS,DET): ", defaults.get("mlb", [])),
        "nhl": _prompt_list("NHL teams (e.g., MTL): ", defaults.get("nhl", [])),
        "college-football": _prompt_list(
            "NCAAF teams (e.g., MICH): ", defaults.get("college-football", [])
        ),
        "mens-college-basketball": _prompt_list(
            "NCAAM teams (e.g., MICH): ", defaults.get("mens-college-basketball", [])
        ),
    }


def _prompt_text(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value


def _prompt_float(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print("Please enter a number.")


def _prompt_list(prompt: str, default: list[str]) -> list[str]:
    default_text = ",".join(default) if default else ""
    value = input(f"{prompt}{f'[{default_text}] ' if default_text else ''}").strip()
    if not value:
        return list(default)
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _prompt_bool(prompt: str, *, default: bool = False) -> bool:
    value = input(prompt).strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def _google_news_query(query: str) -> str:
    safe = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={safe}&hl=en-US&gl=US&ceid=US:en"


def _sports_query_string(favorites: dict[str, list[str]], defaults: dict[str, Any]) -> str:
    names: list[str] = []
    for teams in favorites.values():
        names.extend(teams)
    if names:
        return " OR ".join(names)
    topics = defaults.get("sports_topics")
    if isinstance(topics, list) and topics:
        return " OR ".join(str(topic) for topic in topics)
    return "NFL OR NBA OR MLB OR NHL"


def _topic_query(defaults: dict[str, Any]) -> str:
    topics = defaults.get("news_topics")
    if isinstance(topics, list) and topics:
        return " OR ".join(str(topic) for topic in topics)
    return "Israel OR Jewish OR antisemitism"


def _load_defaults() -> dict[str, Any]:
    if not DEFAULTS_PATH.exists():
        return {}
    data = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data
