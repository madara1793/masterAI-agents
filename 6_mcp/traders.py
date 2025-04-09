from accounts_client import read_accounts_resource, read_strategy_resource
from alpha_client import get_stock_tools_openai

from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel, trace
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from typing import Dict, Any
from agents.mcp import MCPServerStdio
load_dotenv(override=True)

DIRECTORY_FOR_PAID_MARKET_DATA_MCP_SERVER = "/Users/ed/projects/mcp-server"
USE_FREE_MARKET_DATA = not os.getenv("FINANCIAL_DATASETS_API_KEY")

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

MAX_TURNS = 30

gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)

brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
trader_mcp_server_params = [
    {"command": "uv", "args": ["run", "accounts_server.py"]},
    {"command": "uv", "args": ["run", "push_server.py"]},
]
if not USE_FREE_MARKET_DATA:
    directory = DIRECTORY_FOR_PAID_MARKET_DATA_MCP_SERVER
    env = {"FINANCIAL_DATASETS_API_KEY": os.getenv("FINANCIAL_DATASETS_API_KEY")}
    trader_mcp_server_params.append({"command": "uv", "args": ["--directory", directory, "run", "server.py"], "env": env})

researcher_mcp_server_params = [
    {"command": "uvx", "args": ["mcp-server-fetch"]},
    {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-brave-search"], "env": brave_env},
    {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]}
]



def get_model(model_name: str):
    if model_name == "deepseek-chat":
        return OpenAIChatCompletionsModel(model=model_name, openai_client=deepseek_client)
    elif model_name == "gemini-2.0-flash":
        return OpenAIChatCompletionsModel(model=model_name, openai_client=gemini_client)
    else:
        return model_name

async def get_researcher(mcp_servers) -> Agent:
    instructions = f"""You are a financial researcher. You are able to search the web for interesting financial news,
look for possible trading opportunities, and help with research.
Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
If the web search tool raises an error due to rate limits, then use your other tool that fetches web pages instead.

Important: making use of your knowledge graph to retrieve and store information on companies, websites and market conditions:

Make use of your knowledge graph tools to store and recall entity information; use it to retrieve information that
you have worked on previously, and store new information about companies, stocks and market conditions.
Also use it to store web addresses that you find interesting so you can check them later.
Draw on your knowledge graph to build your expertise over time.

If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    researcher = Agent(
        name="Researcher",
        instructions=instructions,
        model="gpt-4o-mini",
        mcp_servers=mcp_servers,
    )
    return researcher

async def get_researcher_tool(mcp_servers) -> Tool:
    researcher = await get_researcher(mcp_servers)
    return researcher.as_tool(
            tool_name="Researcher",
            tool_description="This tool researches online for news and opportunities, \
either based on your specific request to look into a certain stock, \
or generally for notable financial news and opportunities. \
Describe what kind of research you're looking for."
        )

class Trader:
    def __init__(self, name: str, model_name: str="gpt-4o-mini"):
        self.name = name
        self.agent = None
        self.model_name = model_name
        self.trading = ""
        self.account = {}
        self.do_trade = True
        self.trader_mcp_servers = [MCPServerStdio(params) for params in trader_mcp_server_params]
        self.research_mcp_servers = [MCPServerStdio(params) for params in researcher_mcp_server_params]
        self.mcp_servers = self.trader_mcp_servers + self.research_mcp_servers

    async def get_instructions(self) -> str:
        return f"""
You are {self.name}, a trader on the stock market. Your account is under your name, {self.name}.
You actively manage your portfolio according to your strategy.
You have access to tools including a researcher to research online for news and opportunities, based on your request.
You also have tools to access to the latest financial data for stocks, via a financial data API.
And you have tools to buy and sell stocks using your account name {self.name}.
You can use your entity tools as a persistent memory to store and recall information; you share
this memory with other traders and can benefit from the group's knowledge.
Use these tools to carry out research, make decisions, and execute trades.
After you've completed trading, send a push notification with a brief summary of activity, then reply with a 2-3 sentence appraisal.
Your goal is to maximize your profits according to your strategy.
"""
    
    async def get_tools(self) -> list[Tool]:
        tools = await get_stock_tools_openai() if USE_FREE_MARKET_DATA else []
        researcher_tool = await get_researcher_tool(self.research_mcp_servers)
        tools += [researcher_tool]
        return tools
    
    async def connect_mcp_servers(self):
        for server in self.mcp_servers:
            await server.connect()

    async def init_agent(self) -> Agent:
        await self.connect_mcp_servers()
        instructions = await self.get_instructions()
        tools = await self.get_tools()
        self.agent = Agent(
            name=self.name,
            instructions=instructions,
            model=get_model(self.model_name),
            tools=tools,
            mcp_servers=self.trader_mcp_servers
        )
        self.account = await self.get_account()
        return self.agent
    
    async def get_account_report(self) -> str:
        account = await self.get_account()
        account.pop("portfolio_value_time_series", None)
        return json.dumps(account)
    
    async def trade(self):
        account = await self.get_account_report()
        strategy = await read_strategy_resource(self.name)
        message = f"""Based on your investment strategy, you should now look for new opportunities.
        Use the research tool to find news and opportunities consistent with your strategy.
        Do not use the 'get company news' tool; use the research tool instead.
        Use the tools to research stock price and other company information.
        Finally, make you decision, then execute trades using the tools.
        You do not need to rebalance your portfolio; you will be asked to do so later.
        Just make trades based on your strategy as needed.
        Your investment strategy:
        {strategy}
        Here is your current account:
        {account}
        Here is the current datetime:
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
        After you've executed your trades, send a push notification with a brief sumnmary of trades and the health of the portfolio, then
        respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
        """
        with trace(f"{self.name}-trading"):
            result = await Runner.run(self.agent, message, max_turns=MAX_TURNS)
        self.trading = result.final_output
        self.account = await self.get_account()
        return self.trading

    async def rebalance(self):
        await self.connect_mcp_servers()
        account = await self.get_account_report()
        strategy = await read_strategy_resource(self.name)
        message = f"""Based on your investment strategy, you should now examine your portfolio and decide if you need to rebalance.
        Use the research tool to find news and opportunities affecting your existing portfolio.
        Use the tools to research stock price and other company information affecting your existing portfolio.
        Finally, make you decision, then execute trades using the tools as needed.
        You do not need to identify new investment opportunities at this time; you will be asked to do so later.
        Just rebalance your portfolio based on your strategy as needed.
        Your investment strategy:
        {strategy}
        You also have a tool to change your strategy if you wish; you can decide at any time that you would like to evolve
        or even switch your strategy.
        Here is your current account:
        {account}
        Here is the current datetime:
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
        After you've executed your trades, send a push notification with a brief sumnmary of trades and the health of the portfolio, then
        respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
        """
        with trace(f"{self.name}-rebalancing"):
            result = await Runner.run(self.agent, message, max_turns=MAX_TURNS)
        self.trading = result.final_output
        self.account = await self.get_account()
        return self.trading
    
    async def run(self):
        await self.init_agent()
        if self.do_trade:
            result = await self.trade()
        else:
            result = await self.rebalance()
        self.do_trade = not self.do_trade
        return result
    
    async def get_account(self) -> Dict[str, Any]:
        account = await read_accounts_resource(self.name)
        return json.loads(account)
    
    async def cleanup(self):
        for server in self.mcp_servers:
            await server.cleanup()



