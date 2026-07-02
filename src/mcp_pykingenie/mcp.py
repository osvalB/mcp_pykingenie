from fastmcp import FastMCP

mcp: FastMCP = FastMCP(
    name="mcp_pykingenie",
    instructions=(
        "MCP_PYKINGENIE is a MCP server that provides tools for the analysis "
        "of surface-based binding kinetics data only."
    ),
    on_duplicate="error"
)
