from __future__ import annotations

from typing import Any

import httpx

from termdash.sources.base import DataPoint, DataSource


class OpenMeteoSource(DataSource):
    async def fetch(self) -> DataPoint:
        latitude = float(self.options.get("latitude", 0))
        longitude = float(self.options.get("longitude", 0))
        timezone = self.options.get("timezone", "auto")

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": True,
            "timezone": timezone,
            "temperature_unit": "fahrenheit",
            "windspeed_unit": "mph",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        current = payload.get("current_weather", {})
        temperature = current.get("temperature")
        windspeed = current.get("windspeed")
        weathercode = current.get("weathercode")

        value_parts: list[str] = []
        if temperature is not None:
            value_parts.append(f"{temperature} F")
        if windspeed is not None:
            value_parts.append(f"wind {windspeed} mph")
        if weathercode is not None:
            value_parts.append(f"code {weathercode}")

        value = ", ".join(value_parts) if value_parts else "No data"
        return DataPoint(title=self.name, value=value, status="ok")
