import pandas as pd

from .base import Strategy


class MomentumStrategy(Strategy):
    """N-day price-momentum strategy.

    Generates a **buy** signal (1.0) when the return over the past
    ``lookback`` days is positive; otherwise stays **flat** (0.0).

    Parameters
    ----------
    lookback:
        Number of trading days used to measure momentum. Default: 20.
    """

    def __init__(self, lookback: int = 20) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        self.lookback = lookback

    def generate_signals(self, data: pd.DataFrame) -> float:
        """Return 1.0 if past-``lookback`` return > 0, else 0.0."""
        if len(data) < self.lookback + 1:
            return 0.0  # not enough history

        close = data["Close"]
        past_return = close.iloc[-1] / close.iloc[-(self.lookback + 1)] - 1
        return 1.0 if past_return > 0 else 0.0