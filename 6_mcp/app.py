import gradio as gr
import asyncio
from typing import Dict, List, Tuple, Optional
import pandas as pd
from traders import Trader
from agents import trace
from trading_floor import traders
import plotly.express as px

class TraderView:
    def __init__(self, trader: Trader):
        self.trader = trader

    def get_portfolio_value_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self.trader.account.get("portfolio_value_time_series"), columns=["datetime", "value"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    

    def get_portfolio_value_chart(self):

        df = self.get_portfolio_value_df()
        # Create a Plotly figure
        fig = px.line(df, x="datetime", y="value")
        
        # Customize the layout for a compact size
        fig.update_layout(
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis_title=None,  # Remove x-axis title to save space
            yaxis_title=None,  # Remove y-axis title to save space
            paper_bgcolor="#bbb",
            plot_bgcolor="#dde",
        )
        
        # Format the x-axis to show dates more compactly
        fig.update_xaxes(
            tickformat="%m/%d",
            tickangle=45,
            tickfont=dict(size=8)
        )
        
        # Format the y-axis
        fig.update_yaxes(
            tickfont=dict(size=8),
            range=[0, None],
            tickformat=",.0f",
        )
        
        return fig
        
    def get_holdings_df(self) -> pd.DataFrame:
        """Convert holdings to DataFrame for display"""
        holdings = self.trader.account.get("holdings")
        if not self.trader.account.get("holdings"):
            return pd.DataFrame(columns=["Symbol", "Quantity"])
        
        df = pd.DataFrame([
            {"Symbol": symbol, "Quantity": quantity} 
            for symbol, quantity in holdings.items()
        ])
        return df
    
    def get_transactions_df(self) -> pd.DataFrame:
        """Convert transactions to DataFrame for display"""
        transactions = self.trader.account.get("transactions")
        if not transactions:
            return pd.DataFrame(columns=["Timestamp", "Symbol", "Quantity", "Price", "Rationale"])
        
        return pd.DataFrame(transactions)
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value based on current prices"""
        result = self.trader.account.get("total_portfolio_value") or 0.0
        pnl = self.trader.account.get("total_profit_loss") or 0.0
        return f"<div style='text-align: center;font-size:36px'>${result:,.0f}</div>"
    
    def get_balance(self) -> float:
        result = self.trader.account.get("balance") or 0.0
        return f"<div style='text-align: center;font-size:16px'>Cash ${result:,.0f}</div>"
    
    def get_pnl(self) -> float:
        """Calculate profit/loss"""
        result = self.trader.account.get("total_profit_loss") or 0.0
        color = "green" if result >= 0 else "red"
        return f"<div style='text-align: center;font-size:16px;color:{color}'>P&L ${result:,.0f}</div>"
    
    async def run(self) -> str:
        """Run the agent's trading strategy and return thoughts as markdown"""
        with trace(f"{self.trader.name} trading"):
            await self.trader.run()
        return self.trader.trading
    
    def all_components(self):
        return [
            self.get_portfolio_value(),
            self.get_balance(),
            self.get_pnl(),
            self.get_portfolio_value_chart(),
            self.get_holdings_df(),
            self.get_transactions_df(),
            self.trader.trading,
        ]

def agent_ui_component(view: TraderView) -> List[gr.components.Component]:
    """Create UI components for a single trader"""
    with gr.Column() as agent_column:
        gr.Markdown(f"# {view.trader.name}")
        gr.Markdown(f"*Model: {view.trader.model_name}*")
        
        with gr.Column(variant="panel"):
            gr.Markdown("### Investment Thesis")
            thesis_md = gr.Markdown(view.trader.thesis, height=150)
        
        with gr.Row():
            portfolio_value = gr.HTML('<div style="text-align: center;font-size:36px">$...</div>')
            
        with gr.Row():
            cash_balance = gr.HTML('<div style="text-align: center;font-size:14px">$...</div>')
            pnl = gr.HTML('<div style="text-align: center;font-size:14px">$...</div>')

        with gr.Row():
            chart = gr.Plot(container=True, show_label=False)
        
        with gr.Row():
            holdings_table = gr.Dataframe(
                value=view.get_holdings_df(),
                label="Holdings",
                headers=["Symbol", "Quantity"],
                row_count=(5, "dynamic"),
                col_count=2,
                max_height=300,
                elem_classes=["dataframe-fix-small"]
            )

        with gr.Row():
            transactions_table = gr.Dataframe(
                value=view.get_transactions_df(),
                label="Recent Transactions",
                headers=["Timestamp", "Symbol", "Quantity", "Price", "Rationale"],
                row_count=(5, "dynamic"),
                col_count=5,
                max_height=300,
                elem_classes=["dataframe-fix"]
            )
        
        with gr.Row():
            thoughts_md = gr.Markdown(
                value="*Waiting for agent to execute trades...*",
                label="Portfolio appraisal and outlook"
            )

    
    return [portfolio_value, cash_balance, pnl, chart,holdings_table, transactions_table, thoughts_md]

async def ui_refresh(*agents: List[TraderView]) -> Tuple:
    return tuple([component for agent in agents for component in agent.all_components()])

async def start_all_agents(*agents: List[TraderView]) -> Tuple:
    """Start all agents and update their UI components"""

    for agent in agents:
        await agent.trader.init_agent()

    return await ui_refresh(*agents)

async def run_all_agents(*agents: List[TraderView]) -> Tuple:
    """Run all agents and update their UI components"""

    for agent in agents:
        await agent.run()
    
    return await ui_refresh(*agents)

# Main UI construction
def create_ui():
    """Create the main Gradio UI for the trading simulation"""
    
    # Initialize default agents
    views = [TraderView(trader) for trader in traders()]    
    # Custom CSS for displaying P&L in green/red
    css = """
    .positive-pnl {
        color: green !important;
        font-weight: bold;
    }
    .negative-pnl {
        color: red !important;
        font-weight: bold;
    }
    .dataframe-fix-small .table-wrap {
    min-height: 150px;
    max-height: 150px;
    }
    .dataframe-fix .table-wrap {
    min-height: 200px;
    max-height: 200px;
    }
    footer{display:none !important}
    """


    js = """
    function refresh() {
        const url = new URL(window.location);

        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """
    
    
    with gr.Blocks(title="Agent Trading Floor", css=css, js=js, theme=gr.themes.Default(primary_hue="sky")) as ui:
        gr.HTML('<div style="text-align: center;font-size:24px">Autonomous Agentic AI Trading Simulator</div>')
        
        # Create states to store agents
        states = [gr.State(value=view) for view in views]

        components = []
        
        with gr.Row():
            for view in views:
                components.extend(agent_ui_component(view))

        with gr.Row():
            with gr.Column():
                refresh_btn = gr.Button("Refresh now")
            with gr.Column():
                run_btn = gr.Button("Ask traders to trade now", variant="primary")
        
        # Connect the run button to the run_all_agents function
        run_btn.click(fn=run_all_agents, inputs=states, outputs=components)
        refresh_btn.click(fn=ui_refresh, inputs=states, outputs=components) 
        ui.load(fn=start_all_agents,inputs=states, outputs=components)
        # Refresh the UI r
        timer = gr.Timer(value=30*60)
        timer.tick(fn=ui_refresh, inputs=states, outputs=components)
        
    return ui

# Create and launch the UI
if __name__ == "__main__":
    ui = create_ui()
    ui.launch(inbrowser=True)