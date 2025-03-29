from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("server")

@mcp.tool()
async def get_balance(name: str) -> float:
    """Get the cash balance of the given account name.

    Args:
        name: The name of the account holder
    """

    return 1000.0

if __name__ == "__main__":
    mcp.run(transport='stdio')