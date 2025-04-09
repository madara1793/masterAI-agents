import random
from pydantic import BaseModel
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import sqlite3

load_dotenv(override=True)

DB = "accounts.db"
INITIAL_BALANCE = 10_000.0
SPREAD = 0.002

with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
    conn.commit()

def write_account(name, account_dict):
    json_data = json.dumps(account_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        ''', (name, json_data))
        conn.commit()

def read_account(name):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT account FROM accounts WHERE name = ?', (name,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def get_share_price_free(symbol):
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
    r = requests.get(url)
    data = r.json()
    return float(data.get("Global Quote", {}).get("05. price", "0.0"))

def get_share_price_paid(symbol):
    headers = {"X-API-KEY": os.getenv("FINANCIAL_DATASETS_API_KEY")}
    url = f'https://api.financialdatasets.ai/prices/snapshot?ticker={symbol}'
    response = requests.get(url, headers=headers)
    price = response.json().get('snapshot', {}).get('price', 0.0)
    return float(price)

def get_share_price(symbol):
    if os.getenv("FINANCIAL_DATASETS_API_KEY"):
        try:
            return get_share_price_paid(symbol)
        except Exception as e:
            print(f"Was not able to use the paid API; using the free one")
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        try:
            return get_share_price_free(symbol)
        except Exception as e:
            print(f"Was not able to use the free API; a random number will be returned")
    print("Using a random share price as no financial data provider is set up yet")
    return random.randint(1, 100)

class Transaction(BaseModel):
    symbol: str
    quantity: int
    price: float
    timestamp: str
    rationale: str

    def total(self) -> float:
        return self.quantity * self.price
    
    def __repr__(self):
        return f"{abs(self.quantity)} shares of {self.symbol} at {self.price} each."


class Account(BaseModel):
    name: str
    balance: float
    strategy: str
    holdings: dict[str, int]
    transactions: list[Transaction]
    portfolio_value_time_series: list[tuple[str, float]]

    @classmethod
    def get(cls, name: str):
        fields = read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account(name, fields)
        return cls(**fields)
    
    
    def save(self):
        write_account(self.name.lower(), self.model_dump())

    def reset(self, strategy: str):
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        self.save()

    def deposit(self, amount: float):
        """ Deposit funds into the account. """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        print(f"Deposited ${amount}. New balance: ${self.balance}")
        self.save()

    def withdraw(self, amount: float):
        """ Withdraw funds from the account, ensuring it doesn't go negative. """
        if amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal.")
        self.balance -= amount
        print(f"Withdrew ${amount}. New balance: ${self.balance}")
        self.save()

    def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """ Buy shares of a stock if sufficient funds are available. """
        price = get_share_price(symbol)
        buy_price = price * (1 + SPREAD)
        total_cost = buy_price * quantity
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        
        # Update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=quantity, price=buy_price, timestamp=timestamp, rationale=rationale)
        self.transactions.append(transaction)
        
        # Update balance
        self.balance -= total_cost
        self.save()
        return "Completed. Latest details:\n" + self.report()

    def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """ Sell shares of a stock if the user has enough shares. """
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}. Not enough shares held.")
        
        price = get_share_price(symbol)
        sell_price = price * (1 - SPREAD)
        total_proceeds = sell_price * quantity
        
        # Update holdings
        self.holdings[symbol] -= quantity
        
        # If shares are completely sold, remove from holdings
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=-quantity, price=sell_price, timestamp=timestamp, rationale=rationale)  # negative quantity for sell
        self.transactions.append(transaction)

        # Update balance
        self.balance += total_proceeds
        self.save()
        return "Completed. Latest details:\n" + self.report()

    def calculate_portfolio_value(self):
        """ Calculate the total value of the user's portfolio. """
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            total_value += get_share_price(symbol) * quantity
        return total_value

    def calculate_profit_loss(self, portfolio_value: float):
        """ Calculate profit or loss from the initial spend. """
        initial_spend = sum(transaction.total() for transaction in self.transactions)
        return portfolio_value - initial_spend - self.balance

    def get_holdings(self):
        """ Report the current holdings of the user. """
        return self.holdings

    def get_profit_loss(self):
        """ Report the user's profit or loss at any point in time. """
        return self.calculate_profit_loss()

    def list_transactions(self):
        """ List all transactions made by the user. """
        return self.transactions
    
    def report(self) -> str:
        """ Return a json string representing the account.  """
        portfolio_value = self.calculate_portfolio_value()
        self.portfolio_value_time_series.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), portfolio_value))
        self.save()
        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump()
        data["total_portfolio_value"] = portfolio_value
        data["total_profit_loss"] = pnl
        return json.dumps(data)
    
    def get_strategy(self) -> str:
        """ Return the strategy of the account """
        return self.strategy
    
    def change_strategy(self, strategy: str):
        """ At your discretion, if you choose to, call this to change your investment strategy for the future """
        self.strategy = strategy
        self.save()

# Example of usage:
if __name__ == "__main__":
    account = Account("John Doe")
    account.deposit(1000)
    account.buy_shares("AAPL", 5)
    account.sell_shares("AAPL", 2)
    print(f"Current Holdings: {account.get_holdings()}")
    print(f"Total Portfolio Value: {account.calculate_portfolio_value()}")
    print(f"Profit/Loss: {account.get_profit_loss()}")
    print(f"Transactions: {account.list_transactions()}")