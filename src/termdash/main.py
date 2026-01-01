from __future__ import annotations

import argparse
import asyncio
import importlib
import os
from pathlib import Path

import yaml

from termdash.config import load_config
from termdash.dashboard import Dashboard
from termdash.sources import create_source
from termdash.setup import ensure_user_config


def load_mcp_client() -> object | None:
    spec = os.getenv("TERMDASH_MCP_CLIENT")
    if not spec:
        return None

    if ":" not in spec:
        raise ValueError("TERMDASH_MCP_CLIENT must be in module:function format")

    module_name, factory_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name)
    return factory()


def build_sources(config, mcp_client=None):
    sources = []
    for source_config in config.sources:
        sources.append(create_source(source_config, mcp_client=mcp_client))
    return sources


def run() -> None:
    parser = argparse.ArgumentParser(description="Terminal dashboard")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to config YAML",
    )
    parser.add_argument(
        "--block-source",
        type=str,
        default=None,
        help="Block a news source in rss_ticker options and exit",
    )
    args = parser.parse_args()

    config_path = ensure_user_config(args.config)
    if args.block_source:
        _block_source(config_path, args.block_source)
        return

    config = load_config(config_path)
    mcp_client = load_mcp_client()
    sources = build_sources(config, mcp_client=mcp_client)
    dashboard = Dashboard(config, sources)
    asyncio.run(dashboard.run())


def _block_source(config_path: Path, source_name: str) -> None:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    updated = False
    for source in sources:
        if source.get("type") != "rss_ticker":
            continue
        options = source.setdefault("options", {})
        block_sources = options.get("block_sources")
        if not isinstance(block_sources, list):
            block_sources = []
        if source_name.lower() not in {str(item).lower() for item in block_sources}:
            block_sources.append(source_name)
        options["block_sources"] = block_sources
        updated = True

    if not updated:
        raise SystemExit("No rss_ticker sources found in config")

    config_path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Blocked source added: {source_name}")


if __name__ == "__main__":
    run()
