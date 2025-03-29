from pydantic import BaseModel
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime


load_dotenv(override=True)

DB = "db"
INITIAL_BALANCE = 10_000.0

def get_share_price_free(symbol):
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
    r = requests.get(url)
    data = r.json()
    return float(data.get("Global Quote", {}).get("05. price", "0.0"))

def get_share_price(symbol):
    headers = {"X-API-KEY": os.getenv("FINANCIAL_DATASETS_API_KEY")}
    url = f'https://api.financialdatasets.ai/prices/snapshot?ticker={symbol}'
    response = requests.get(url, headers=headers)
    price = response.json().get('snapshot', {}).get('price', 0.0)
    return float(price)

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
    holdings: dict[str, int]
    transactions: list[Transaction]
    portfolio_value_time_series: list[tuple[str, float]]

    
    @classmethod
    def get(cls, name: str):
        filename = os.path.join(DB, f"{name.lower()}.json")
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                fields = json.load(f)
        else:
            fields = {
                "name": name,
                "balance": INITIAL_BALANCE,
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(fields, f)
        return cls(**fields)
    
    def save(self):
        filename = os.path.join(DB, f"{self.name.lower()}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f)


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
        total_cost = price * quantity
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        
        # Update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=quantity, price=price, timestamp=timestamp, rationale=rationale)
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
        total_proceeds = price * quantity
        
        # Update holdings
        self.holdings[symbol] -= quantity
        
        # If shares are completely sold, remove from holdings
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=-quantity, price=price, timestamp=timestamp, rationale=rationale)  # negative quantity for sell
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