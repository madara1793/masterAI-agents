import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

params = StdioServerParameters(command="python", args=["server.py"], env=None)

async def list_tools():
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_tool(tool_name, tool_args):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            print(f"Calling {tool_name} with {tool_args}")
            result = await session.call_tool(tool_name, tool_args)
            return result
            