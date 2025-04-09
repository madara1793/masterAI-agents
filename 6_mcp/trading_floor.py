from traders import Trader
from typing import List
import asyncio

def traders() -> List[Trader]:


    alice = Trader("Alice",  model_name="deepseek-chat")
    bob = Trader("Bob")
    carol = Trader("Carol", model_name="deepseek-chat")

    return [alice, bob, carol]


async def run_every_30_minutes():
    while True:
        for trader in traders():
            await trader.run()
        
        await asyncio.sleep(30 * 60)

if __name__ == "__main__":
    print("Starting scheduler...")
    asyncio.run(run_every_30_minutes())
