from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from termdash.config import DashboardConfig
from termdash.sources.base import DataPoint, DataSource

STATUS_STYLES = {
    "ok": "green",
    "warn": "yellow",
    "error": "red",
    "loading": "cyan",
}


@dataclass
class TileState:
    source: DataSource
    data: DataPoint


class Dashboard:
    def __init__(self, config: DashboardConfig, sources: Iterable[DataSource]) -> None:
        self.config = config
        self.console = Console()
        self.sources = list(sources)
        self._lock = asyncio.Lock()
        self._state: dict[str, DataPoint] = {
            source.name: DataPoint(title=source.name, value="Loading...", status="loading")
            for source in self.sources
        }

    async def run(self) -> None:
        tasks = [asyncio.create_task(self._poll_source(source)) for source in self.sources]

        try:
            with Live(
                self._render(self._state),
                refresh_per_second=4,
                screen=True,
                console=self.console,
            ) as live:
                while True:
                    await asyncio.sleep(self.config.refresh_ui_seconds)
                    snapshot = await self._snapshot()
                    live.update(self._render(snapshot))
        except KeyboardInterrupt:
            pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _snapshot(self) -> dict[str, DataPoint]:
        async with self._lock:
            return dict(self._state)

    async def _poll_source(self, source: DataSource) -> None:
        while True:
            try:
                data = await source.fetch()
            except Exception as exc:  # noqa: BLE001
                data = DataPoint(title=source.name, value=str(exc), status="error")

            async with self._lock:
                self._state[source.name] = data

            await asyncio.sleep(source.refresh_seconds)

    def _render(self, snapshot: dict[str, DataPoint]):
        header = Panel(
            Align.center(Text(self.config.title, style="bold white"), vertical="middle"),
            style="bold blue",
        )

        panels = []
        for source in self.sources:
            data = snapshot.get(
                source.name,
                DataPoint(title=source.name, value="Loading...", status="loading"),
            )
            panels.append(self._render_tile(data))

        grid = Columns(panels, equal=True, expand=True)
        return Align.center(Group(header, grid), vertical="top")

    def _render_tile(self, data: DataPoint) -> Panel:
        style = STATUS_STYLES.get(data.status, "white")
        body = Text(data.value, style=style)
        if data.detail:
            body.append("\n")
            body.append(data.detail, style="dim")
        return Panel(body, title=data.title, border_style=style)
