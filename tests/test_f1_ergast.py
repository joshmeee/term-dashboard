import respx
from httpx import Response

from termdash.sources.f1_ergast import F1ErgastSource


@respx.mock
async def test_f1_ergast_next_race():
    payload = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "raceName": "Example GP",
                        "date": "2030-05-01",
                        "time": "14:00:00Z",
                        "Circuit": {
                            "Location": {"locality": "Austin", "country": "USA"}
                        },
                    }
                ]
            }
        }
    }
    respx.get("http://ergast.com/api/f1/current/next.json").mock(
        return_value=Response(200, json=payload)
    )

    source = F1ErgastSource("F1 Status", 300, {})
    data = await source.fetch()

    assert data.status == "ok"
    assert "Next: Example GP" in data.value
