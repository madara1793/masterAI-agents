from contextlib import AsyncExitStack
from accounts_client import read_accounts_resource, read_strategy_resource
from tracers import make_trace_id
from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel, trace
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from agents.mcp import MCPServerStdio
from templates import researcher_instructions, trader_instructions, trade_message, rebalance_message, research_tool
from mcp_params import trader_mcp_server_params, researcher_mcp_server_params
load_dotenv(override=True)

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MAX_TURNS = 30

openrouter_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=openrouter_api_key)
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)
def get_model(model_name: str):
    if "/" in model_name:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=openrouter_client)
    elif "deepseek" in model_name:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=deepseek_client)
    else:
        return model_name

async def get_researcher(mcp_servers, model_name) -> Agent:
    researcher = Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )
    return researcher

async def get_researcher_tool(mcp_servers, model_name) -> Tool:
    researcher = await get_researcher(mcp_servers, model_name)
    return researcher.as_tool(
            tool_name="Researcher",
            tool_description=research_tool()
        )


class Trader:
    def __init__(self, name: str, lastname="Trader", model_name="gpt-4o-mini"):
        self.name = name
        self.lastname = lastname
        self.agent = None
        self.model_name = model_name
        self.do_trade = True

    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        tool = await get_researcher_tool(researcher_mcp_servers, self.model_name)
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions(self.name),
            model=get_model(self.model_name),
            tools=[tool],
            mcp_servers=trader_mcp_servers
        )
        return self.agent
    
    async def get_account_report(self) -> str:
        account = await read_accounts_resource(self.name)
        account_json = json.loads(account)
        account_json.pop("portfolio_value_time_series", None)
        return json.dumps(account_json)
    
    async def trade(self):
        with trace(f"{self.name}-trading", trace_id=make_trace_id(f"{self.name.lower()}")):
            async with AsyncExitStack() as stack:
                trader_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params)) for params in trader_mcp_server_params]
                async with AsyncExitStack() as stack:
                    researcher_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params)) for params in researcher_mcp_server_params]
                    self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
                    account = await self.get_account_report()
                    strategy = await read_strategy_resource(self.name)
                    message = trade_message(self.name, strategy, account)
                    await Runner.run(self.agent, message, max_turns=MAX_TURNS)

    async def rebalance(self):
        with trace(f"{self.name}-rebalancing", trace_id=make_trace_id(f"{self.name.lower()}")):
            async with AsyncExitStack() as stack:
                trader_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params)) for params in trader_mcp_server_params]
                async with AsyncExitStack() as stack:
                    researcher_mcp_servers = [await stack.enter_async_context(MCPServerStdio(params)) for params in researcher_mcp_server_params]
                    self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
                    account = await self.get_account_report()
                    strategy = await read_strategy_resource(self.name)
                    message = rebalance_message(self.name, strategy, account)
                    await Runner.run(self.agent, message, max_turns=MAX_TURNS)
    
    async def run(self):
        try:
            if self.do_trade:
                await self.trade()
            else:
                await self.rebalance()
        except Exception as e:
            print(f"Error running trader {self.name}: {e}")
        self.do_trade = not self.do_trade

