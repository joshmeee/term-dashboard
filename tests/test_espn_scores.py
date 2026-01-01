import respx
from httpx import Response

from termdash.sources.espn_scores import EspnScoresSource


@respx.mock
async def test_espn_scores_live_game():
    payload = {
        "events": [
            {
                "competitions": [
                    {
                        "status": {"type": {"state": "in", "shortDetail": "Q3 05:32"}},
                        "competitors": [
                            {"homeAway": "away", "score": "14", "team": {"abbreviation": "DAL"}},
                            {"homeAway": "home", "score": "21", "team": {"abbreviation": "PHI"}},
                        ],
                    }
                ]
            }
        ]
    }
    respx.get("https://site.web.api.espn.com/apis/v2/sports/football/nfl/scoreboard").mock(
        return_value=Response(200, json=payload)
    )

    source = EspnScoresSource(
        "Live Sports",
        60,
        {"leagues": [{"label": "NFL", "sport": "football", "league": "nfl"}]},
    )
    data = await source.fetch()

    assert data.status == "ok"
    assert "NFL:" in data.value
    assert "DAL 14 @ PHI 21" in data.value


@respx.mock
async def test_espn_scores_favorites_filter():
    payload = {
        "events": [
            {
                "competitions": [
                    {
                        "status": {"type": {"state": "in", "shortDetail": "Q1 10:00"}},
                        "competitors": [
                            {"homeAway": "away", "score": "0", "team": {"abbreviation": "NYJ"}},
                            {"homeAway": "home", "score": "3", "team": {"abbreviation": "NE"}},
                        ],
                    }
                ]
            }
        ]
    }
    respx.get("https://site.web.api.espn.com/apis/v2/sports/football/nfl/scoreboard").mock(
        return_value=Response(200, json=payload)
    )

    source = EspnScoresSource(
        "Live Sports",
        60,
        {
            "leagues": [{"label": "NFL", "sport": "football", "league": "nfl"}],
            "favorites": {"nfl": ["DAL"]},
            "show_only_favorites": True,
        },
    )
    data = await source.fetch()

    assert data.status == "ok"
    assert data.value == "No live games"
