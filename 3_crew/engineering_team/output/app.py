from accounts import Account, get_share_price  
import gradio as gr  

def create_account():  
    global account  
    account.create_account()  
    return "Account created for " + account.owner  

def deposit_funds(amount):  
    try:  
        account.deposit(amount)  
        return f"Deposited ${amount}. New balance: ${account.balance}"  
    except ValueError as e:  
        return str(e)  

def withdraw_funds(amount):  
    try:  
        account.withdraw(amount)  
        return f"Withdrew ${amount}. New balance: ${account.balance}"  
    except ValueError as e:  
        return str(e)  

def buy_shares(symbol, quantity):  
    try:  
        account.buy_shares(symbol, quantity)  
        return f"Bought {quantity} shares of {symbol}. Remaining balance: ${account.balance}"  
    except ValueError as e:  
        return str(e)  

def sell_shares(symbol, quantity):  
    try:  
        account.sell_shares(symbol, quantity)  
        return f"Sold {quantity} shares of {symbol}. New balance: ${account.balance}"  
    except ValueError as e:  
        return str(e)  

def show_holdings():  
    return str(account.get_holdings())  

def show_profit_loss():  
    return f"Profit/Loss: ${account.get_profit_loss()}"  

def show_transactions():  
    return str(account.list_transactions())  

account = Account("Demo User")  
create_account()  

with gr.Blocks() as demo:  
    gr.Markdown("### Account Management System")  
    deposit_input = gr.Number(label="Deposit Amount")  
    gr.Button("Deposit").click(deposit_funds, inputs=deposit_input, outputs=None)  
    withdraw_input = gr.Number(label="Withdraw Amount")  
    gr.Button("Withdraw").click(withdraw_funds, inputs=withdraw_input, outputs=None)  
    buy_symbol = gr.Textbox(label="Stock Symbol (e.g. AAPL)")  
    buy_quantity = gr.Number(label="Quantity to Buy")  
    gr.Button("Buy Shares").click(buy_shares, inputs=[buy_symbol, buy_quantity], outputs=None)  
    sell_symbol = gr.Textbox(label="Stock Symbol (e.g. AAPL)")  
    sell_quantity = gr.Number(label="Quantity to Sell")  
    gr.Button("Sell Shares").click(sell_shares, inputs=[sell_symbol, sell_quantity], outputs=None)  
    gr.Button("Show Holdings").click(show_holdings, outputs=None)  
    gr.Button("Show Profit/Loss").click(show_profit_loss, outputs=None)  
    gr.Button("Show Transactions").click(show_transactions, outputs=None)  

demo.launch()