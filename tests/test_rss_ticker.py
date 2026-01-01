import respx
from httpx import Response

from termdash.sources.rss_ticker import RssTickerSource


@respx.mock
async def test_rss_ticker_rotates():
    feed = """
    <rss version="2.0">
      <channel>
        <item><title>Item A</title></item>
        <item><title>Item B</title></item>
      </channel>
    </rss>
    """
    respx.get("https://example.com/feed").mock(return_value=Response(200, text=feed))

    source = RssTickerSource("Ticker", 10, {"url": "https://example.com/feed"})
    first = await source.fetch()
    second = await source.fetch()

    assert first.value == "Item A"
    assert second.value == "Item B"


@respx.mock
async def test_rss_ticker_filters_and_lines():
    feed = """
    <rss version="2.0">
      <channel>
        <item><title>Keep This</title><source>Fox News</source></item>
        <item><title>Skip This</title><source>MSNBC</source></item>
      </channel>
    </rss>
    """
    respx.get("https://example.com/feed").mock(return_value=Response(200, text=feed))

    source = RssTickerSource(
        "Ticker",
        10,
        {
            "url": "https://example.com/feed",
            "block_sources": ["msnbc"],
            "lines": 2,
            "show_source": True,
        },
    )
    data = await source.fetch()

    assert data.value == "Keep This (Fox News)\nKeep This (Fox News)"
