The strategy used in the provided code use data from Yahoo Finance and a daily data the code is best suited for a tick-data and to be used for HFT.
For the sake of simplicity I have used yfinance library and to access the tick-data one can plug in its API

**Quote Class:**
This class represents the bid/ask spread. It keeps track of bid and ask prices, bid and ask sizes, spread, and other relevant information.
The update method is called whenever there's a quote update. It checks for a level change (a move of exactly 1 penny in the bid/ask spread) and updates the attributes accordingly.
The reset method is called when a level change happens, resetting certain attributes.

**Position Class:**
This class tracks the position of shares in the portfolio. It keeps track of orders filled, pending buy/sell shares, total shares, and trades.
Methods like update_pending_buy_shares, update_pending_sell_shares, update_filled_amount, and remove_pending_order are used to update the position based on order fills and cancellations.
The add_trade method adds a trade to the list of trades.
The calculate_metrics method calculates performance metrics such as the number of winning and losing trades and the win rate.

**Performance Calculation:**
The calculate_performance function calculates various performance metrics using the historical price data.
It calculates daily returns, cumulative returns, annualized mean return, annualized volatility, Sharpe ratio, Sortino ratio, and maximum drawdown.
Main Run Function:

**Run function:**
Historical price data for the specified symbol (e.g., 'AAPL') is fetched using Yahoo Finance API.
The required position size is calculated based on the latest closing price and an example cash balance.
Quote and trade update functions are defined (currently not implemented) to handle updates.
Performance metrics are calculated using historical price data and position metrics.
Performance metrics are printed, and strategy signals and drawdown are plotted.

Overall, the strategy seems to be focused on tracking bid/ask spreads and making trades based on certain conditions related to bid/ask sizes, spread levels, and position sizes. However, the implementation is incomplete as the quote and trade update functions are placeholders and not implemented yet. 
Therefore, the actual trading logic based on bid/ask spread dynamics and position management is not executed in the provided code.
