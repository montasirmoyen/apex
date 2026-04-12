import pandas as pd

from .base import Strategy


class MeanReversionStrategy(Strategy):
    """Simple z-score mean-reversion strategy.

    Generates a **buy** signal (1.0) when the latest close price is more than
    ``threshold`` standard deviations *below* its ``lookback``-day moving
    average (i.e. the asset has reverted and is cheap relative to its recent
    history). Otherwise stays **flat** (0.0).

    Parameters
    ----------
    lookback:
        Rolling window length for the mean and standard deviation. Default: 20.
    threshold:
        Z-score threshold below which a buy is triggered. Default: -1.0.
    """

    def __init__(self, lookback: int = 20, threshold: float = -1.0) -> None:
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        self.lookback = lookback
        self.threshold = threshold

    def generate_signals(self, data: pd.DataFrame) -> float:
        """Return 1.0 if z-score < threshold (oversold), else 0.0."""
        if len(data) < self.lookback:
            return 0.0

        close = data["Close"].iloc[-self.lookback :]
        mean = float(close.mean())
        std = float(close.std())

        if std == 0:
            return 0.0

        z_score = (float(data["Close"].iloc[-1]) - mean) / std
        return 1.0 if z_score < self.threshold else 0.0
