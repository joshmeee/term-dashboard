from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from termdash.sources.base import DataPoint, DataSource


class F1ErgastSource(DataSource):
    async def fetch(self) -> DataPoint:
        async with httpx.AsyncClient(timeout=10) as client:
            next_race = await _fetch_race(client, "next")

        if not next_race:
            return DataPoint(title=self.name, value="No race data", status="warn")

        race_name = next_race.get("raceName", "Race")
        location = _race_location(next_race)
        start = _race_datetime(next_race)

        now = datetime.now(timezone.utc)
        if start and now.date() == start.date():
            value = f"Race day: {race_name} {location} (UTC {start.strftime('%H:%M')})"
            return DataPoint(title=self.name, value=value, status="ok")

        date_str = next_race.get("date", "")
        value = f"Next: {race_name} {location} on {date_str}"
        return DataPoint(title=self.name, value=value, status="ok")


async def _fetch_race(client: httpx.AsyncClient, which: str) -> dict[str, Any] | None:
    url = f"http://ergast.com/api/f1/current/{which}.json"
    response = await client.get(url)
    response.raise_for_status()
    data = response.json()

    race_table = (
        data.get("MRData", {})
        .get("RaceTable", {})
        .get("Races", [])
    )
    if not race_table:
        return None
    return race_table[0]


def _race_datetime(race: dict[str, Any]) -> datetime | None:
    date = race.get("date")
    time = race.get("time")
    if not date:
        return None
    if time:
        return datetime.fromisoformat(f"{date}T{time}".replace("Z", "+00:00"))
    return datetime.fromisoformat(f"{date}T00:00:00+00:00")


def _race_location(race: dict[str, Any]) -> str:
    circuit = race.get("Circuit", {}) or {}
    location = circuit.get("Location", {}) or {}
    locality = location.get("locality")
    country = location.get("country")
    parts = [p for p in [locality, country] if p]
    if not parts:
        return ""
    return f"({', '.join(parts)})"
