import pytest
from fastmcp import Client

import mcp_pykingenie


def test_package_has_version():
    """Testing package version exist."""
    assert mcp_pykingenie.__version__ is not None

"
@pytest.mark.asyncio
async def test_mcp_server():
    """Testing MCP server."""
    async with Client(mcp_pykingenie.mcp) as client:
        result = await client.call_tool("import_gator_experiment", {})
        assert "Gator experiment added from" in result.data


