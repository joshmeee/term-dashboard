import respx
from httpx import Response

from termdash.sources.open_meteo import OpenMeteoSource


@respx.mock
async def test_open_meteo_fetch():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=Response(
            200,
            json={"current_weather": {"temperature": 22.5, "windspeed": 8, "weathercode": 1}},
        )
    )

    source = OpenMeteoSource(
        "Weather",
        300,
        {"latitude": 1, "longitude": 2, "timezone": "auto"},
    )
    data = await source.fetch()

    assert "22.5" in data.value
    assert "F" in data.value
    assert data.status == "ok"
