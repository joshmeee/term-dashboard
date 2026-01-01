from __future__ import annotations

from typing import Any, Protocol

from termdash.sources.base import DataPoint, DataSource


class MCPClient(Protocol):
    async def call(self, server: str, method: str, params: dict[str, Any]) -> Any:
        ...


class MCPSource(DataSource):
    async def fetch(self) -> DataPoint:
        client = self.options.get("client")
        if client is None:
            return DataPoint(
                title=self.name,
                value="MCP client not configured",
                status="error",
                detail="Provide an MCP client instance at runtime.",
            )

        server = self.options.get("server")
        method = self.options.get("method")
        params = self.options.get("params", {})
        if not server or not method:
            return DataPoint(
                title=self.name,
                value="Missing MCP configuration",
                status="error",
            )

        try:
            result = await client.call(server, method, params)
        except Exception as exc:  # noqa: BLE001
            return DataPoint(title=self.name, value=str(exc), status="error")

        if isinstance(result, dict) and "value" in result:
            value = str(result.get("value"))
        else:
            value = str(result)

        return DataPoint(title=self.name, value=value, status="ok")
