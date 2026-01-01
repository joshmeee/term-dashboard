import respx
from httpx import Response

from termdash.sources.rss import RssSource


@respx.mock
async def test_rss_fetch():
    feed = """
    <rss version="2.0">
      <channel>
        <title>Example</title>
        <item>
          <title>First Item</title>
        </item>
      </channel>
    </rss>
    """
    respx.get("https://example.com/feed").mock(return_value=Response(200, text=feed))

    source = RssSource("News", 300, {"url": "https://example.com/feed"})
    data = await source.fetch()

    assert data.value == "First Item"
    assert data.status == "ok"
