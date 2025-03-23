# accounts.py

def get_share_price(symbol):
    prices = {
        'AAPL': 150.00,
        'TSLA': 700.00,
        'GOOGL': 2800.00
    }
    return prices.get(symbol, 0.0)

class Transaction:
    def __init__(self, symbol: str, quantity: int, price: float):
        self.symbol = symbol          # the symbol of the stock
        self.quantity = quantity      # amount of shares bought or sold
        self.price = price            # price per share at the time of transaction
        self.total = quantity * price  # total value of the transaction
        self.type = 'buy' if quantity > 0 else 'sell'  # type of transaction

    def __repr__(self):
        return f"{self.type.capitalize()} {abs(self.quantity)} shares of {self.symbol} at {self.price} each."


class Account:
    def __init__(self, owner: str):
        self.owner = owner                    # the name of the account owner
        self.balance = 0.0                    # current cash balance of the account
        self.holdings = {}                    # dictionary to hold stocks and their quantities
        self.transactions = []                # list to track all transactions made

    def create_account(self):
        """ Initializes a new account for the user. """
        print(f"Account for {self.owner} created.")

    def deposit(self, amount: float):
        """ Deposit funds into the account. """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        print(f"Deposited ${amount}. New balance: ${self.balance}")

    def withdraw(self, amount: float):
        """ Withdraw funds from the account, ensuring it doesn't go negative. """
        if amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal.")
        self.balance -= amount
        print(f"Withdrew ${amount}. New balance: ${self.balance}")

    def buy_shares(self, symbol: str, quantity: int):
        """ Buy shares of a stock if sufficient funds are available. """
        price = get_share_price(symbol)
        total_cost = price * quantity
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        
        # Update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        
        # Record transaction
        transaction = Transaction(symbol, quantity, price)
        self.transactions.append(transaction)
        
        # Update balance
        self.balance -= total_cost
        print(f"Bought {quantity} shares of {symbol} for ${total_cost}. Remaining balance: ${self.balance}")

    def sell_shares(self, symbol: str, quantity: int):
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

        # Record transaction
        transaction = Transaction(symbol, -quantity, price)  # negative quantity for sell
        self.transactions.append(transaction)

        # Update balance
        self.balance += total_proceeds
        print(f"Sold {quantity} shares of {symbol} for ${total_proceeds}. New balance: ${self.balance}")

    def calculate_portfolio_value(self):
        """ Calculate the total value of the user's portfolio. """
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            total_value += get_share_price(symbol) * quantity
        return total_value

    def calculate_profit_loss(self):
        """ Calculate profit or loss from the initial deposit. """
        initial_deposit = sum(transaction.total for transaction in self.transactions if transaction.type == "buy") - \
                          sum(abs(transaction.total) for transaction in self.transactions if transaction.type == "sell")
        current_value = self.calculate_portfolio_value()
        return current_value - initial_deposit

    def get_holdings(self):
        """ Report the current holdings of the user. """
        return self.holdings

    def get_profit_loss(self):
        """ Report the user's profit or loss at any point in time. """
        return self.calculate_profit_loss()

    def list_transactions(self):
        """ List all transactions made by the user. """
        return self.transactions

# Example of usage:
if __name__ == "__main__":
    account = Account("John Doe")
    account.create_account()
    account.deposit(1000)
    account.buy_shares("AAPL", 5)
    account.sell_shares("AAPL", 2)
    print(f"Current Holdings: {account.get_holdings()}")
    print(f"Total Portfolio Value: {account.calculate_portfolio_value()}")
    print(f"Profit/Loss: {account.get_profit_loss()}")
    print(f"Transactions: {account.list_transactions()}")