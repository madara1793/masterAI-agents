from traders import Trader
from typing import List
from agents import trace
import asyncio

def traders() -> List[Trader]:

    alice_thesis = """You are an aggressive day-trader.
You hunt for great opportunities and you take decisive action.
You buy and sell regularly to maximize profits and limit losses.
You are constantly seeking out new opportunities based on the latest news in the market."""

    alice = Trader("Alice", alice_thesis, model_name="deepseek-chat")

    bob_thesis = """You are an investor that looks for long-term value.
You search for companies that are undervalued and have a strong business model.
You buy and hold for sufficient time to realize a profit.
You like to research news to find companies that might be under the radar, 
and you like to research fundamentals to find companies that are undervalued.
You pride yourself on the quality of your research and the long-term success of your investments.
"""

    bob = Trader("Bob", bob_thesis)

    carol_thesis = """You are an investor that looks for technical indicators to find trading opportunities.
You use technical indicators to find companies that are overbought or oversold.
You buy and sell based on these indicators to maximize profits and limit losses.
You are constantly seeking out new opportunities based on the latest technical indicators in the market."""

    carol = Trader("Carol", carol_thesis, model_name="gemini-2.0-flash")

    return [alice, bob, carol]


async def run_every_30_minutes():
    
    trading_agent = traders()
    for trader in trading_agent:
        await trader.init_agent()
    
    while True:
        for trader in trading_agent:
            with trace(f"{trader.name} trading"):
                await trader.run()
        
        await asyncio.sleep(30 * 60)

if __name__ == "__main__":
    print("Starting scheduler...")
    asyncio.run(run_every_30_minutes())
