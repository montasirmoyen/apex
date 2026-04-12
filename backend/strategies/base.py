from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class Strategy(ABC):
    """Abstract base class for all trading strategies.

    Sub-classes must implement ``generate_signals``, which receives the full
    historical OHLCV DataFrame for a single ticker (up to and including the
    current bar) and returns a scalar signal for that bar.
    """

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> float:
        """Generate a trading signal from historical OHLCV data.

        Parameters
        ----------
        data:
            Historical OHLCV DataFrame indexed by date. The last row
            represents the current bar. Only past data is visible — no
            future information is leaked by the engine.

        Returns
        -------
        float
            ``1.0``  → buy / hold long
            ``0.0``  → flat / no position
            ``-1.0`` → sell / go short (not yet used by the portfolio)
        """
        raise NotImplementedError

    def supports_cross_sectional(self) -> bool:
        """Whether the strategy can generate multi-asset target weights."""
        return False

    def generate_target_weights(
        self,
        date: pd.Timestamp,
        data_by_ticker: Dict[str, pd.DataFrame],
        prices: Dict[str, float],
        portfolio: Any = None,
    ) -> Dict[str, float]:
        """Generate target portfolio weights for all tickers on the current bar.

        Default behavior keeps existing strategies compatible by deriving equal-
        weight long-only targets from per-ticker scalar signals.
        """
        if not data_by_ticker:
            return {}

        signals: Dict[str, float] = {}
        for ticker, history in data_by_ticker.items():
            signals[ticker] = self.generate_signals(history)

        longs = [t for t, s in signals.items() if s > 0.0]
        if not longs:
            return {t: 0.0 for t in data_by_ticker}

        weight = 1.0 / len(longs)
        out = {t: 0.0 for t in data_by_ticker}
        for ticker in longs:
            out[ticker] = weight
        return out

    def get_diagnostics(self) -> Dict[str, Any]:
        """Optional strategy-level diagnostics returned by the engine."""
        return {}