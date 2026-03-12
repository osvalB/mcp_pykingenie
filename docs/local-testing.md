# Local Testing

This page explains how to run tests locally for `mcp_pykingenie`.

## Prerequisites

Install dependencies including test extras:

```bash
cd mcp_pykingenie
uv sync --extra test
```

## Run all tests

```bash
uv run pytest -vv
```

## Run a specific test

```bash
uv run pytest tests/test_app.py::test_mcp_server -vv
```

## Inspect registered MCP tools

To verify which tools are registered on the live `mcp` instance:

```bash
uv run python - <<'PY'
import asyncio
from fastmcp import Client
import mcp_pykingenie

async def main():
    async with Client(mcp_pykingenie.mcp) as c:
        tools = await c.list_tools()
        print([t.name for t in tools])

asyncio.run(main())
PY
```

## Test the server interactively with FastMCP Inspector

```bash
fastmcp dev src/mcp_pykingenie/main.py:mcp
```