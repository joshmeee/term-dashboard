import respx
from httpx import Response

from termdash.sources.espn_scores import EspnSummarySource


@respx.mock
async def test_espn_summary_counts():
    payload = {
        "events": [
            {
                "competitions": [
                    {"status": {"type": {"state": "in"}}}
                ]
            },
            {
                "competitions": [
                    {"status": {"type": {"state": "post"}}}
                ]
            },
        ]
    }
    respx.get("https://site.web.api.espn.com/apis/v2/sports/football/nfl/scoreboard").mock(
        return_value=Response(200, json=payload)
    )

    source = EspnSummarySource(
        "Summary",
        120,
        {"leagues": [{"label": "NFL", "sport": "football", "league": "nfl"}]},
    )
    data = await source.fetch()

    assert data.status == "ok"
    assert "Live games: 1" in data.value
    assert "NFL: 1" in data.value
