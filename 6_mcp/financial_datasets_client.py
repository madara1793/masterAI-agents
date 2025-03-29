import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from agents import FunctionTool
import json
from dotenv import load_dotenv
import os
from agents import FunctionTool

load_dotenv(override=True)

params = StdioServerParameters(command="uv", args=["--directory", "/Users/ed/projects/mcp-server", "run", "server.py"],
                               env={"FINANCIAL_DATASETS_API_KEY": os.getenv("FINANCIAL_DATASETS_API_KEY")})


async def list_financial_datasets_tools():
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_financial_datasets_tool(tool_name, tool_args):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result
            

async def get_financial_datasets_tools_openai():
    openai_tools = []
    for tool in await list_financial_datasets_tools():
        schema = {**tool.inputSchema, "additionalProperties": False}
        required = schema["required"]
        new_properties = {key:value for key, value in schema["properties"].items() if key in required}
        schema["properties"] = new_properties
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description,
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_financial_datasets_tool(toolname, json.loads(args))
                
        )
        openai_tools.append(openai_tool)
    return openai_tools