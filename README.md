# Term Dashboard

A cross-platform terminal dashboard that refreshes near-real-time data in a responsive layout.
Designed for Linux (Kali), macOS, and Windows terminals.

## Features
- Responsive tile layout that adapts to terminal size and orientation
- Pluggable data sources (weather, RSS news, MCP-backed personal data)
- Simple YAML configuration
- Async refresh loops per data source

## Quickstart

```powershell
# From the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

# Or using uv
uv venv
uv pip install -e .
```

Run with the example config:

```powershell
termdash -c configs\example.yaml
```

## Configuration

See `configs/example.yaml` for a template.

Key fields:
- `dashboard.title`: Title displayed in the header
- `dashboard.refresh_ui_seconds`: UI refresh interval
- `sources`: List of data sources with `type`, `refresh_seconds`, and `options`

## First Run Setup

If you run `termdash` without a config, it creates one at `~/.termdash/config.yaml`
and prompts for location and favorite teams. It can optionally detect city/state
and latitude/longitude from your IP address (no API key required).

The generated config contains no API keys. Personal preferences are stored only
in the local `~/.termdash/config.yaml`, which is not committed to git.

You can also pre-fill defaults by creating `~/.termdash/defaults.yaml`. Example:

```yaml
favorites:
  nfl: ["TEAM_ABBR"]
  nba: ["TEAM_ABBR"]
  mlb: ["TEAM_ABBR"]
  nhl: ["TEAM_ABBR"]
  college-football: ["TEAM_ABBR"]
  mens-college-basketball: ["TEAM_ABBR"]
news_topics:
  - TopicA
  - TopicB
sports_topics:
  - Team Name A
  - Team Name B
prefer_sources: ["source name"]
block_sources: ["blocked source"]
```

## ESPN Sports Options

`type: espn_scores` options:
- `preset`: `all_major` (NFL/NHL/MLB/NBA/NCAAF/NCAAM) or omit and provide `leagues`
- `leagues`: list of `{label, sport, league}` (overrides `preset`)
- `show_only_favorites`: show only live games with favorite teams (default false)
- `highlight_favorites`: append `[fav]` marker (default true)
- `favorites`: map of league code/label to team abbreviations (or `all`)

`type: espn_summary` options:
- `preset` or `leagues` same as above; shows counts per league

## RSS Ticker

`type: rss_ticker` rotates headlines each refresh:
- `url` or `urls`: one or many RSS feed URLs
- `lines`: number of lines to show per refresh
- `auto_lines`: derive `lines` from terminal height
- `min_lines` / `max_lines`: clamp auto-derived lines
- `max_items`: number of headlines to cycle (default 20)
- `include_keywords` / `exclude_keywords`: filter by keywords
- `block_sources`: list of source names or domains to skip
- `only_sources`: allowlist of source names or domains
- `prefer_sources`: prioritize matching sources
- `show_source`: append source name in parentheses

Google News RSS templates (edit `YOUR_CITY`, `YOUR_STATE`):
- `https://news.google.com/rss/search?q=YOUR_CITY+YOUR_STATE&hl=en-US&gl=US&ceid=US:en`
- `https://news.google.com/rss/search?q=YOUR_STATE+government&hl=en-US&gl=US&ceid=US:en`
- `https://news.google.com/rss/search?q=US+federal+government&hl=en-US&gl=US&ceid=US:en`

To block a source in all tickers:

```powershell
termdash --block-source "MSNBC"
```

## MCP Sources

MCP-backed sources are configured using `type: mcp` and an MCP client must be provided
at runtime. The default implementation returns an error until a client is injected.

Set `TERMDASH_MCP_CLIENT` to `module:function` that returns an MCP client instance:

```powershell
$env:TERMDASH_MCP_CLIENT = "my_mcp_factory:get_client"
```

Example MCP source configuration:

```yaml
- name: GitHub Notifications
  type: mcp
  refresh_seconds: 120
  options:
    server: github
    method: notifications.count
    params:
      participating: true
```


## Running as a Service (Linux)

Create a systemd unit at `/etc/systemd/system/termdash.service`:

```ini
[Unit]
Description=Term Dashboard
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/term-dashboard
ExecStart=/path/to/term-dashboard/.venv/bin/termdash -c configs/example.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

## Testing

```powershell
pip install -e .[dev]
pytest
```

## Notes
- For real-time sources (email, messaging, packages), prefer MCP servers where available.
- Playwright MCP can be used to validate render output if you add a capture harness.
