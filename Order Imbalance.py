import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Quote():
    """
    We use Quote objects to represent the bid/ask spread. When we encounter a
    'level change', a move of exactly 1 penny, we may attempt to make one
    trade. Whether or not the trade is successfully filled, we do not submit
    another trade until we see another level change.

    Note: Only moves of 1 penny are considered eligible because larger moves
    could potentially indicate some newsworthy event for the stock, which this
    algorithm is not tuned to trade.
    """

    def __init__(self):
        self.prev_bid = 0
        self.prev_ask = 0
        self.prev_spread = 0
        self.bid = 0
        self.ask = 0
        self.bid_size = 0
        self.ask_size = 0
        self.spread = 0
        self.traded = True
        self.level_ct = 1
        self.time = 0

    def reset(self):
        # Called when a level change happens
        self.traded = False
        self.level_ct += 1

    def update(self, data):
        # Update bid and ask sizes and timestamp
        self.bid_size = data.bid_size
        self.ask_size = data.ask_size

        # Check if there has been a level change
        if (
            self.bid != data.bid_price
            and self.ask != data.ask_price
            and round(data.ask_price - data.bid_price, 2) == .01
        ):
            # Update bids and asks and time of level change
            self.prev_bid = self.bid
            self.prev_ask = self.ask
            self.bid = data.bid_price
            self.ask = data.ask_price
            self.time = data.timestamp
            # Update spreads
            self.prev_spread = round(self.prev_ask - self.prev_bid, 3)
            self.spread = round(self.ask - self.bid, 3)
            print('Level: bid', 
                    self.bid, ', ask', self.ask, flush=True
            )
            # If change is from one penny spread level to a different penny
            # spread level, then initialize for new level (reset stale vars)
            if self.prev_spread == 0.01:
                self.reset()


class Position():
    """
    The position object is used to track how many shares we have. We need to
    keep track of this so our position size doesn't inflate beyond the level
    we're willing to trade with. Because orders may sometimes be partially
    filled, we need to keep track of how many shares are "pending" a buy or
    sell as well as how many have been filled into our account.
    """

    def __init__(self):
        self.orders_filled_amount = {}
        self.pending_buy_shares = 0
        self.pending_sell_shares = 0
        self.total_shares = 0
        self.trades = []  # Initialize trades attribute

    def update_pending_buy_shares(self, quantity):
        self.pending_buy_shares += quantity

    def update_pending_sell_shares(self, quantity):
        self.pending_sell_shares += quantity

    def update_filled_amount(self, order_id, new_amount, side):
        old_amount = self.orders_filled_amount[order_id]
        if new_amount > old_amount:
            if side == 'buy':
                self.update_pending_buy_shares(old_amount - new_amount)
                self.update_total_shares(new_amount - old_amount)
            else:
                self.update_pending_sell_shares(old_amount - new_amount)
                self.update_total_shares(old_amount - new_amount)
            self.orders_filled_amount[order_id] = new_amount

    def remove_pending_order(self, order_id, side):
        old_amount = self.orders_filled_amount[order_id]
        if side == 'buy':
            self.update_pending_buy_shares(old_amount - 100)
        else:
            self.update_pending_sell_shares(old_amount - 100)
        del self.orders_filled_amount[order_id]

    def update_total_shares(self, quantity):
        self.total_shares += quantity

    def add_trade(self, trade):  # Update trades attribute when a trade is added
        self.trades.append(trade)

    def calculate_metrics(self):
        # Calculate number of winning and losing trades
        num_winning_trades = sum(1 for trade in self.trades if trade > 0)
        num_losing_trades = sum(1 for trade in self.trades if trade < 0)

        # Calculate win rate
        total_trades = len(self.trades)
        win_rate = num_winning_trades / total_trades if total_trades > 0 else 0

        return num_winning_trades, num_losing_trades, win_rate


def calculate_performance(data):
    # Calculate daily returns
    data['Daily Return'] = data['Close'].pct_change()

    # Calculate cumulative returns
    data['Cumulative Return'] = (1 + data['Daily Return']).cumprod()

    # Calculate annualized mean return and volatility
    annualized_return = data['Daily Return'].mean() * 252
    annualized_volatility = data['Daily Return'].std() * np.sqrt(252)

    # Calculate Sharpe ratio (assuming risk-free rate of 0)
    sharpe_ratio = annualized_return / annualized_volatility

    # Calculate Sortino ratio
    negative_returns = data['Daily Return'][data['Daily Return'] < 0]
    semi_deviation = negative_returns.std() * np.sqrt(252)
    sortino_ratio = annualized_return / semi_deviation if semi_deviation != 0 else np.nan

    # Calculate maximum drawdown
    data['Rolling Max'] = data['Close'].rolling(window=252, min_periods=1).max()
    data['Drawdown'] = data['Close'] / data['Rolling Max'] - 1
    max_drawdown = data['Drawdown'].min()

    return annualized_return, annualized_volatility, sharpe_ratio, sortino_ratio, max_drawdown




def run():
    symbol = 'AAPL'
    
    # Fetch historical data to calculate required position size
    data = yf.download(symbol, start='2020-03-01', end='2024-03-10')
    cashBalance = 10000  # Example cash balance
    price_stock = data['Close'].iloc[-1]  # Latest closing price
    max_shares = cashBalance / price_stock
    
    quote = Quote()
    position = Position()

    # Define our quote and trade update functions
    def on_quote_update(quote_data):
        quote.update(quote_data)

    def on_trade_update(trade_data):
        if quote.traded:
            return
        # We've received a trade and might be ready to follow it
        if (
            data.timestamp <= (
                quote.time + pd.Timedelta(np.timedelta64(50, 'ms'))
            )
        ):
            # The trade came too close to the quote update
            # and may have been for the previous level
            return
        if data.size >= 100:
            # The trade was large enough to follow, so we check to see if
            # we're ready to trade. We also check to see that the
            # bid vs ask quantities (order book imbalance) indicate
            # a movement in that direction. We also want to be sure that
            # we're not buying or selling more than we should.
            if (
                data.price == quote.ask
                and quote.bid_size > (quote.ask_size * 2)
                and (
                    position.total_shares + position.pending_buy_shares
                ) < max_shares - 100
            ):
                # Everything looks right, so we submit our buy at the ask
                try:
                    print("Atemptibg Buy")
                    o = api.submit_order(
                        symbol=symbol, qty='100', side='buy',
                        type='limit', time_in_force='day',
                        limit_price=str(quote.ask)
                    )
                    # Approximate an IOC order by immediately cancelling
                    #api.cancel_order(o.id)
                    position.update_pending_buy_shares(100)
                    position.orders_filled_amount[o.id] = 0
                    print('Buy at', quote.ask, flush=True)
                    quote.traded = True
                except Exception as e:
                    print(e)
            if (
                data.price == quote.bid
                and quote.ask_size > (quote.bid_size * 2)
                and (
                    position.total_shares - position.pending_sell_shares
                ) >= 100 - max_shares
            ):
                # Everything looks right, so we submit our sell at the bid
                try:
                    print("Atempting Sell")
                    o = api.submit_order(
                        symbol=symbol, qty='100', side='sell',
                        type='limit', time_in_force='day',
                        limit_price=str(quote.bid)
                    )
                    # Approximate an IOC order by immediately cancelling
                    # api.cancel_order(o.id)
                    position.update_pending_sell_shares(100)
                    position.orders_filled_amount[o.id] = 0
                    print('Sell at', quote.bid, flush=True)
                    quote.traded = True
                except Exception as e:
                    print(e)

    # @conn.on_trade_update(on_trade)
    async def on_trade_update(data):
        # We got an update on one of the orders we submitted. We need to
        # update our position with the new information.
        event = data.event
        if event == 'fill':
            if data.order['side'] == 'buy':
                position.update_total_shares(
                    int(data.order['filled_qty'])
                )
            else:
                position.update_total_shares(
                    -1 * int(data.order['filled_qty'])
                )
            position.remove_pending_order(
                data.order['id'], data.order['side']
            )
        elif event == 'partial_fill':
            position.update_filled_amount(
                data.order['id'], int(data.order['filled_qty']),
                data.order['side']
            )
        elif event == 'canceled' or event == 'rejected':
            position.remove_pending_order(
                data.order['id'], data.order['side']
            )

    # Calculate performance metrics
    annualized_return, annualized_volatility, sharpe_ratio, sortino_ratio, max_drawdown = calculate_performance(data)
    num_winning_trades, num_losing_trades, win_rate = position.calculate_metrics()

    # Print performance metrics
    print("Annualized Return:", annualized_return)
    print("Annualized Volatility:", annualized_volatility)
    print("Sharpe Ratio:", sharpe_ratio)
    print("Sortino Ratio:", sortino_ratio)
    print("Maximum Drawdown:", max_drawdown)
    print("Number of Winning Trades:", num_winning_trades)
    print("Number of Losing Trades:", num_losing_trades)
    print("Win Rate:", win_rate)

    # Plot strategy signals
    plt.figure(figsize=(10, 6))
    # Plot your strategy signals here
    plt.title('Strategy Signals')
    plt.xlabel('Date')
    plt.ylabel('Signal')
    plt.grid(True)
    plt.show()

    # Plot drawdown
    plt.figure(figsize=(10, 6))
    data['Drawdown'].plot()
    plt.title('Drawdown')
    plt.xlabel('Date')
    plt.ylabel('Drawdown')
    plt.grid(True)
    plt.show()

if __name__ == '__main__':
    run()
