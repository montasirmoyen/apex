from typing import Literal

import pandas as pd

Regime = Literal["bull", "bear"]


class RegimeDetector:
    """Simple moving-average-based market regime detector.

    Compares the latest price to its ``window``-day simple moving average:
    - price > MA  →  ``"bull"``
    - price <= MA →  ``"bear"``

    When there is insufficient history the regime defaults to ``"bull"`` so
    the strategy is not suppressed during the warm-up period.

    Parameters
    ----------
    window:
        Look-back period for the moving average. Default: 200 days.
    """

    def __init__(self, window: int = 200) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        self.window = window

    def detect(self, prices: pd.Series) -> Regime:
        """Detect the current market regime.

        Parameters
        ----------
        prices:
            Close price series indexed by date (most recent last).

        Returns
        -------
        ``"bull"`` or ``"bear"``
        """
        if len(prices) < self.window:
            return "bull"  # not enough history, stay neutral/bullish

        ma = float(prices.rolling(self.window).mean().iloc[-1])
        latest = float(prices.iloc[-1])
        return "bull" if latest > ma else "bear"
