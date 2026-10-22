from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient


def chronogrid_mcp_client(url: str, token: str | None) -> MCPClient:
    """ChronoGrid's self-hosted MCP server, reached over Streamable HTTP like Alexa+ would."""
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return MCPClient(lambda: streamablehttp_client(url, headers=headers))
