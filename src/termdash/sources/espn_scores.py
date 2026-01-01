from __future__ import annotations

import asyncio
from typing import Any

import httpx

from termdash.sources.base import DataPoint, DataSource


PRESETS = {
    "all_major": [
        {"label": "NFL", "sport": "football", "league": "nfl"},
        {"label": "NCAA Football", "sport": "football", "league": "college-football"},
        {"label": "NBA", "sport": "basketball", "league": "nba"},
        {"label": "NCAA MBB", "sport": "basketball", "league": "mens-college-basketball"},
        {"label": "MLB", "sport": "baseball", "league": "mlb"},
        {"label": "NHL", "sport": "hockey", "league": "nhl"},
    ]
}


class EspnScoresSource(DataSource):
    async def fetch(self) -> DataPoint:
        leagues = _resolve_leagues(self.options)
        if not leagues:
            return DataPoint(title=self.name, value="No leagues configured", status="error")

        favorites = _resolve_favorites(self.options)
        show_only_favorites = bool(self.options.get("show_only_favorites", False))
        highlight_favorites = bool(self.options.get("highlight_favorites", True))

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [
                self._fetch_league(
                    client,
                    league,
                    favorites=favorites,
                    show_only_favorites=show_only_favorites,
                    highlight_favorites=highlight_favorites,
                )
                for league in leagues
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        lines: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            lines.extend(result)

        if not lines:
            return DataPoint(title=self.name, value="No live games", status="ok")

        return DataPoint(title=self.name, value="\n".join(lines), status="ok")

    async def _fetch_league(
        self,
        client: httpx.AsyncClient,
        league: dict[str, Any],
        *,
        favorites: dict[str, set[str]],
        show_only_favorites: bool,
        highlight_favorites: bool,
    ) -> list[str]:
        sport = league.get("sport")
        league_code = league.get("league")
        label = league.get("label", league_code or sport or "league").upper()
        if not sport or not league_code:
            return [f"{label}: missing sport/league config"]

        url = f"https://site.web.api.espn.com/apis/v2/sports/{sport}/{league_code}/scoreboard"
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()

        events = payload.get("events", []) or []
        lines: list[str] = []
        fav_set = _favorite_set_for_league(favorites, league_code, label)
        for event in events:
            competitions = event.get("competitions", []) or []
            if not competitions:
                continue
            competition = competitions[0]
            status = (competition.get("status", {}) or {}).get("type", {}) or {}
            if status.get("state") != "in":
                continue

            short_detail = status.get("shortDetail") or status.get("detail") or ""
            home, away = _extract_competitors(competition.get("competitors", []) or [])
            if not home or not away:
                continue

            is_favorite = _match_favorite(home, away, fav_set)
            if show_only_favorites and not is_favorite:
                continue

            line = f"{label}: {away['abbr']} {away['score']} @ {home['abbr']} {home['score']}"
            if short_detail:
                line += f" ({short_detail})"
            last_play = _extract_last_play(competition)
            if last_play:
                line += f" | Last: {last_play}"
            if highlight_favorites and is_favorite:
                line += " [fav]"
            lines.append(line)

        return lines


class EspnSummarySource(DataSource):
    async def fetch(self) -> DataPoint:
        leagues = _resolve_leagues(self.options)
        if not leagues:
            return DataPoint(title=self.name, value="No leagues configured", status="error")

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [self._count_league(client, league) for league in leagues]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        lines: list[str] = []
        total = 0
        for result in results:
            if isinstance(result, Exception):
                continue
            label, count = result
            total += count
            lines.append(f"{label}: {count}")

        if not lines:
            return DataPoint(title=self.name, value="No data", status="warn")

        lines.insert(0, f"Live games: {total}")
        return DataPoint(title=self.name, value="\n".join(lines), status="ok")

    async def _count_league(self, client: httpx.AsyncClient, league: dict[str, Any]) -> tuple[str, int]:
        sport = league.get("sport")
        league_code = league.get("league")
        label = league.get("label", league_code or sport or "league").upper()
        if not sport or not league_code:
            return label, 0

        url = f"https://site.web.api.espn.com/apis/v2/sports/{sport}/{league_code}/scoreboard"
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()

        events = payload.get("events", []) or []
        count = 0
        for event in events:
            competitions = event.get("competitions", []) or []
            if not competitions:
                continue
            competition = competitions[0]
            status = (competition.get("status", {}) or {}).get("type", {}) or {}
            if status.get("state") == "in":
                count += 1

        return label, count


def _extract_competitors(competitors: list[dict[str, Any]]):
    home = None
    away = None
    for item in competitors:
        team = item.get("team", {}) or {}
        abbr = team.get("abbreviation") or team.get("shortDisplayName") or team.get("displayName")
        name = team.get("displayName") or team.get("name") or abbr or "TBD"
        score = item.get("score", "0")
        entry = {"abbr": abbr or "TBD", "score": score, "name": name}
        if item.get("homeAway") == "home":
            home = entry
        elif item.get("homeAway") == "away":
            away = entry
    return home, away


def _resolve_leagues(options: dict[str, Any]) -> list[dict[str, Any]]:
    leagues = options.get("leagues")
    if leagues:
        return leagues
    preset = options.get("preset", "all_major")
    return PRESETS.get(preset, [])


def _resolve_favorites(options: dict[str, Any]) -> dict[str, set[str]]:
    favorites = options.get("favorites", {}) or {}
    normalized: dict[str, set[str]] = {}
    for key, value in favorites.items():
        if not isinstance(value, list):
            continue
        normalized[key.lower()] = {v.strip().lower() for v in value if isinstance(v, str)}
    return normalized


def _favorite_set_for_league(favorites: dict[str, set[str]], league_code: str, label: str) -> set[str]:
    combined = set()
    combined.update(favorites.get("all", set()))
    combined.update(favorites.get(league_code.lower(), set()))
    combined.update(favorites.get(label.lower(), set()))
    return combined


def _match_favorite(home: dict[str, Any], away: dict[str, Any], favorites: set[str]) -> bool:
    if not favorites:
        return False
    for team in (home, away):
        if team["abbr"].lower() in favorites:
            return True
        if team["name"].lower() in favorites:
            return True
    return False


def _extract_last_play(competition: dict[str, Any]) -> str:
    situation = competition.get("situation", {}) or {}
    last_play = situation.get("lastPlay", {}) or {}
    text = last_play.get("text")
    if text:
        return str(text)
    alt = competition.get("lastPlay", {}) or {}
    return str(alt.get("text", "")).strip()
