from accounts_client import get_accounts_tools_openai, read_accounts_resource
from alpha_client import get_stock_tools_openai
from brave_client import get_search_tools_openai
from financial_datasets_client import get_financial_datasets_tools_openai
from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import json
from typing import Dict, Any

load_dotenv(override=True)

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

MAX_TURNS = 30

gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)


def get_model(model_name: str):
    if model_name == "deepseek-chat":
        deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=deepseek_api_key)
        return OpenAIChatCompletionsModel(model=model_name, openai_client=deepseek_client)
    elif model_name == "gemini-2.0-flash":
        return OpenAIChatCompletionsModel(model=model_name, openai_client=gemini_client)
    else:
        return model_name

async def get_researcher() -> Agent:
    instructions = f"""You are a financial researcher. You are able to search the web for interesting financial news,
look for possible trading opportunities, and help with research.
Based on the request, you carry out necessary research and respond with your findings.
Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    tools = await get_search_tools_openai()
    researcher = Agent(
        name="Researcher",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=tools,
        handoff_description="The research is complete and available for use."
    )
    return researcher

async def get_researcher_tool() -> Tool:
    researcher = await get_researcher()
    return researcher.as_tool(
            tool_name="Researcher",
            tool_description="Research online for news and opportunities, \
                either based on your specific request to look into a certain stock, \
                or generally for notable financial news and opportunities."
        )

class Trader:
    def __init__(self, name: str, thesis: str, model_name: str="gpt-4o-mini"):
        self.name = name
        self.thesis = thesis
        self.agent = None
        self.model_name = model_name
        self.trading = ""
        self.account = {}
        self.do_trade = True

    async def get_instructions(self) -> str:
        return f"""
You are {self.name}, a trader on the stock market. Your account is under your name, {self.name}.
This is your investment thesis.
{self.thesis}
You always act according to your thesis.
You have access to tools including a researcher to research online for news and opportunities, based on your request.
You also have tools to access to the latest financial data for stocks, via a financial data API.
And you have tools to buy and sell stocks using your account name {self.name}.
Use these tools to carry out research, make decisions, and execute trades.
Your goal is to maximize your profits according to your thesis.
"""
    
    async def get_tools(self) -> list[Tool]:
        tools = await get_financial_datasets_tools_openai() + await get_accounts_tools_openai()
        researcher_tool = await get_researcher_tool()
        tools += [researcher_tool]
        return tools

    async def init_agent(self) -> Agent:
        instructions = await self.get_instructions()
        tools = await self.get_tools()
        self.agent = Agent(
            name=self.name,
            instructions=instructions,
            model=get_model(self.model_name),
            tools=tools
        )
        self.account = await self.get_account()
        return self.agent
    
    async def get_account_report(self) -> str:
        account = await self.get_account()
        account.pop("portfolio_value_time_series", None)
        return json.dumps(account)
    
    async def trade(self):
        account = await self.get_account_report()
        message = f"""Based on your investment thesis, you should now look for new opportunities.
        Use the research tool to find news and opportunities consistent with your thesis.
        Use the tools to research stock price and other company information.
        Finally, make you decision, then execute trades using the tools.
        You do not need to rebalance your portfolio; you will be asked to do so later.
        Just make trades based on your thesis as needed.
        A reminder of your investment thesis:
        {self.thesis}
        Here is your current account:
        {account}
        Here is the current datetime:
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
        After you've made your trades, respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
        """
        result = await Runner.run(self.agent, message, max_turns=MAX_TURNS)
        self.trading = result.final_output
        self.account = await self.get_account()
        return self.trading

    async def rebalance(self):
        account = await self.get_account_report()
        message = f"""Based on your investment thesis, you should now examine your portfolio and decide if you need to rebalance.
        Use the research tool to find news and opportunities affecting your existing portfolio.
        Use the tools to research stock price and other company information affecting your existing portfolio.
        Finally, make you decision, then execute trades using the tools as needed.
        You do not need to identify new investment opportunities at this time; you will be asked to do so later.
        Just rebalance your portfolio based on your thesis as needed.
        A reminder of your investment thesis:
        {self.thesis}
        Here is your current account:
        {account}
        Here is the current datetime:
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Now, carry out analysis, make your decision and execute trades. Your account name is {self.name}.
        After you've made your rebalancing, respond with a brief 2-3 sentence appraisal of your portfolio and its outlook.
        """

        result = await Runner.run(self.agent, message, max_turns=MAX_TURNS)
        self.trading = result.final_output
        self.account = await self.get_account()
        return self.trading
    
    async def run(self):
        if self.do_trade:
            return await self.trade()
        else:
            return await self.rebalance()
        self.do_trade = not self.do_trade
    
    async def get_account(self) -> Dict[str, Any]:
        account = await read_accounts_resource(self.name)
        return json.loads(account)



