from __future__ import annotations

import asyncio
from typing import Any

import httpx

from termdash.sources.base import DataPoint, DataSource


class EspnScoresSource(DataSource):
    async def fetch(self) -> DataPoint:
        leagues = self.options.get("leagues", [])
        if not leagues:
            return DataPoint(title=self.name, value="No leagues configured", status="error")

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [self._fetch_league(client, league) for league in leagues]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        lines: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            lines.extend(result)

        if not lines:
            return DataPoint(title=self.name, value="No live games", status="ok")

        return DataPoint(title=self.name, value="\n".join(lines), status="ok")

    async def _fetch_league(self, client: httpx.AsyncClient, league: dict[str, Any]) -> list[str]:
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

            line = f"{label}: {away['abbr']} {away['score']} @ {home['abbr']} {home['score']}"
            if short_detail:
                line += f" ({short_detail})"
            lines.append(line)

        return lines


def _extract_competitors(competitors: list[dict[str, Any]]):
    home = None
    away = None
    for item in competitors:
        team = item.get("team", {}) or {}
        abbr = team.get("abbreviation") or team.get("shortDisplayName") or team.get("displayName")
        score = item.get("score", "0")
        entry = {"abbr": abbr or "TBD", "score": score}
        if item.get("homeAway") == "home":
            home = entry
        elif item.get("homeAway") == "away":
            away = entry
    return home, away
