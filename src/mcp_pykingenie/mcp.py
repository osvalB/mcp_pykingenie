from mcp.server.mcpserver import MCPServer

from .config import SERVER_INSTRUCTIONS


mcp: MCPServer = MCPServer(
    name="mcp_pykingenie",
    instructions=SERVER_INSTRUCTIONS,
)