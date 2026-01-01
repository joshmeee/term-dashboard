from __future__ import annotations

import argparse
import asyncio
import importlib
import os
from pathlib import Path

from termdash.config import load_config
from termdash.dashboard import Dashboard
from termdash.sources import create_source


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
    args = parser.parse_args()

    config = load_config(args.config)
    mcp_client = load_mcp_client()
    sources = build_sources(config, mcp_client=mcp_client)
    dashboard = Dashboard(config, sources)
    asyncio.run(dashboard.run())


if __name__ == "__main__":
    run()
