from fastmcp import FastMCP

mcp: FastMCP = FastMCP(
    name="mcp_pykingenie",
    instructions="MCP_PYKINGENIE is a MCP server that provides tools for the analysis of binding kinetics data.",
    on_duplicate="error"
)
