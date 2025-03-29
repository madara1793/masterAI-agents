from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import gradio as gr
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import os
import asyncio
from langchain.agents import Tool
from playwright.async_api import async_playwright
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[list, add_messages]

def push(text: str):
    """Send a push notification to the user"""
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

push_tool = Tool(
    name="send_push_notification",
    func=push,
    description="useful for when you want to send a push notification"
)

class Sidekick:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.playwright = None
        self.browser = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self.sidekick_id = "1"

    async def ensure_initialized(self):
        """Ensure Playwright, browser, and tools are initialized asynchronously."""
        if self.browser is None:
            # Start Playwright fully async
            self.playwright = await async_playwright().start()
            # Launch a browser (Chromium) in non-headless mode:
            self.browser = await self.playwright.chromium.launch(headless=False)

            from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
            toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=self.browser)
            self.tools = toolkit.get_tools() + [push_tool]
            self.llm_with_tools = self.llm.bind_tools(self.tools)

            # Build the state graph
            self.graph = await self.build_graph()

    async def chatbot(self, state: State):
        """Call the tools-bound LLM on the conversation messages."""
        return {"messages": [await self.llm_with_tools.ainvoke(state["messages"])]}

    async def build_graph(self):
        graph_builder = StateGraph(State)
        memory = MemorySaver()
        graph_builder.add_node("chatbot", self.chatbot)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_conditional_edges("chatbot", tools_condition, "tools")
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        return graph_builder.compile(checkpointer=memory)

    async def invoke_graph(self, user_input: str, history):
        """Async function to invoke the graph (used by Gradio ChatInterface)."""
        await self.ensure_initialized()
        config = {"configurable": {"thread_id": self.sidekick_id}}
        result = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config
        )
        return result["messages"][-1].content

# Instantiate your Sidekick
sidekick = Sidekick()

# Gradio supports async functions, so pass the async method directly:
gr.ChatInterface(sidekick.invoke_graph, type="messages").launch()

# Cleanup handler to close the browser and optionally stop Playwright
import atexit

@atexit.register
def cleanup():
    if sidekick.browser:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(sidekick.browser.close())
            if sidekick.playwright:
                loop.create_task(sidekick.playwright.stop())
        except RuntimeError:
            # If no loop is running, do a direct run
            asyncio.run(sidekick.browser.close())
            if sidekick.playwright:
                asyncio.run(sidekick.playwright.stop())
