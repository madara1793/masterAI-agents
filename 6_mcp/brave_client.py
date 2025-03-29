import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from dotenv import load_dotenv
import os
from agents import FunctionTool
import json

load_dotenv(override=True)

params = StdioServerParameters(command="npx", args=["-y", "@modelcontextprotocol/server-brave-search"], env={
        "BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")
      })

async def list_search_tools():
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_search_tool(tool_name, tool_args):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result
        
async def get_search_tools_openai():
    openai_tools = []
    for tool in await list_search_tools():
        schema = {**tool.inputSchema, "additionalProperties": False}
        schema["properties"] = {"query": schema["properties"]["query"]}
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description,
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_search_tool(toolname, json.loads(args))
        )
        openai_tools.append(openai_tool)

    return openai_tools
            