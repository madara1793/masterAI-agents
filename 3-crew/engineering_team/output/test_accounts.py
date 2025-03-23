import unittest
from accounts import Account, Transaction, get_share_price

class TestAccount(unittest.TestCase):
    
    def setUp(self):
        self.account = Account('Test User')
        self.account.create_account()  # Simulating account creation

    def test_initial_balance(self):
        self.assertEqual(self.account.balance, 0.0)

    def test_deposit(self):
        self.account.deposit(100)
        self.assertEqual(self.account.balance, 100)

    def test_withdraw(self):
        self.account.deposit(100)
        self.account.withdraw(50)
        self.assertEqual(self.account.balance, 50)
        
    def test_withdraw_insufficient_funds(self):
        with self.assertRaises(ValueError):
            self.account.withdraw(100)

    def test_buy_shares(self):
        self.account.deposit(1000)
        self.account.buy_shares('AAPL', 5)
        self.assertEqual(self.account.holdings['AAPL'], 5)
        self.assertEqual(self.account.balance, 1000 - (5 * 150.00))  # 150 is the price of AAPL

    def test_buy_shares_insufficient_funds(self):
        self.account.deposit(100)
        with self.assertRaises(ValueError):
            self.account.buy_shares('AAPL', 1)

    def test_sell_shares(self):
        self.account.deposit(1000)
        self.account.buy_shares('AAPL', 5)
        self.account.sell_shares('AAPL', 2)
        self.assertEqual(self.account.holdings['AAPL'], 3)
        self.assertEqual(self.account.balance, 1000 - (5 * 150.00) + (2 * 150.00))

    def test_sell_shares_insufficient_holdings(self):
        with self.assertRaises(ValueError):
            self.account.sell_shares('AAPL', 1)

    def test_calculate_portfolio_value(self):
        self.account.deposit(1000)
        self.account.buy_shares('AAPL', 5)
        self.assertEqual(self.account.calculate_portfolio_value(), 1000 - (5 * 150.0) + (5 * 150.0))

    def test_calculate_profit_loss(self):
        self.account.deposit(1000)
        self.account.buy_shares('AAPL', 5)
        self.account.sell_shares('AAPL', 2)
        self.assertAlmostEqual(self.account.get_profit_loss(), 0.0)  # Initially, profit/loss should be zero.

    def test_list_transactions(self):
        self.account.deposit(1000)
        self.account.buy_shares('AAPL', 5)
        transactions = self.account.list_transactions()
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].type, 'buy')

if __name__ == '__main__':
    unittest.main()