from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

DEFAULT_CONFIG_DIR = Path.home() / ".termdash"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"


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
    city, state, latitude, longitude = _collect_location()
    favorites = _collect_favorites()

    local_query = _google_news_query(f"{city} {state}")
    state_query = _google_news_query(f"{state} government")
    federal_query = _google_news_query("US federal government")
    topic_query = _google_news_query("Israel OR Jewish OR antisemitism")
    sports_query = _google_news_query(_sports_query_string(favorites))

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
                    "block_sources": ["msnbc", "al jazeera"],
                    "prefer_sources": ["fox news"],
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
                    "block_sources": ["msnbc", "al jazeera"],
                    "prefer_sources": ["fox news"],
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


def _collect_favorites() -> dict[str, list[str]]:
    print("Enter favorite team abbreviations (comma separated). Leave blank to skip.")
    return {
        "nfl": _prompt_list("NFL teams (e.g., NE): "),
        "nba": _prompt_list("NBA teams (e.g., BOS): "),
        "mlb": _prompt_list("MLB teams (e.g., BOS,DET): "),
        "nhl": _prompt_list("NHL teams (e.g., MTL): "),
        "college-football": _prompt_list("NCAAF teams (e.g., MICH): "),
        "mens-college-basketball": _prompt_list("NCAAM teams (e.g., MICH): "),
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


def _prompt_list(prompt: str) -> list[str]:
    value = input(prompt).strip()
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _prompt_bool(prompt: str, *, default: bool = False) -> bool:
    value = input(prompt).strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def _google_news_query(query: str) -> str:
    safe = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={safe}&hl=en-US&gl=US&ceid=US:en"


def _sports_query_string(favorites: dict[str, list[str]]) -> str:
    names: list[str] = []
    for teams in favorites.values():
        names.extend(teams)
    if not names:
        return "NFL OR NBA OR MLB OR NHL"
    return " OR ".join(names)
