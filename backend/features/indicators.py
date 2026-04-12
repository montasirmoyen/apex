# moving avg, returns, volatility
def moving_average(prices, window):
    return prices.rolling(window).mean()

def returns(prices):
    return prices.pct_change()