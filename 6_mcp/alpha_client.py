import smithery
import mcp
from mcp.client.websocket import websocket_client
from dotenv import load_dotenv
import os
from agents import FunctionTool
import json 

load_dotenv(override=True)

# Create Smithery URL with server endpoint
url = smithery.create_smithery_url("wss://server.smithery.ai/@qubaomingg/stock-analysis-mcp/ws", {
  "alphaVantageApiKey": os.getenv("ALPHA_VANTAGE_API_KEY")
})

import base64

alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
smithery_api_key = os.getenv("SMITHERY_API_KEY")

config = {"alphaVantageApiKey": alpha_vantage_api_key}
config_b64 = base64.b64encode(json.dumps(config).encode()).decode()
url = f"wss://server.smithery.ai/@qubaomingg/stock-analysis-mcp/ws?config={config_b64}&api_key={smithery_api_key}"

async def list_stock_tools():
    async with websocket_client(url) as streams:
        async with mcp.ClientSession(*streams) as session:
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_stock_tool(tool_name, tool_args):
    print(f"Calling {tool_name} with {tool_args}")
    async with websocket_client(url) as streams:
        async with mcp.ClientSession(*streams) as session:
            result = await session.call_tool(tool_name, tool_args)
            print(f"Result: {result}")
            return result
        
async def get_stock_tools_openai():
    openai_tools = []
    for tool in await list_stock_tools():
        schema = {**tool.inputSchema, "additionalProperties": False}
        schema["properties"] = {"symbol":schema["properties"]["symbol"]}
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.name.replace("-", " "),
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_stock_tool(toolname, json.loads(args))
                
        )
        openai_tools.append(openai_tool)
    return openai_tools