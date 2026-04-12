from typing import Any, Dict, List, Optional

import pandas as pd


class Portfolio:
    """Tracks cash, share positions, and equity value over a backtest.

    Execution model
    ---------------
    On each bar the portfolio is fully rebalanced:
    1. All existing positions are liquidated at the current close price.
    2. The freed cash is split equally among every ticker whose signal is > 0,
       and the corresponding shares are purchased at the current close price.

    This keeps the allocation simple (equal-weight long-only) while remaining
    easy to swap for more sophisticated models later.

    Parameters
    ----------
    tickers:
        List of ticker symbols tracked by the portfolio.
    initial_cash:
        Starting capital in currency units. Default: 100 000.
    """

    def __init__(self, tickers: List[str], initial_cash: float = 100_000.0) -> None:
        self.tickers = tickers
        self.cash: float = initial_cash
        self.positions: Dict[str, float] = {t: 0.0 for t in tickers}
        self.equity_curve: List[float] = []
        self.dates: List[pd.Timestamp] = []
        self.daily_turnover: List[float] = []
        self.daily_costs: List[float] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(
        self,
        date: pd.Timestamp,
        prices: Dict[str, float],
        signals: Dict[str, float],
        cost_model: Optional[Any] = None,
        market_state: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """Rebalance the portfolio for *date* and record the equity snapshot.

        Parameters
        ----------
        date:
            The current trading date.
        prices:
            Mapping of ticker → close price for the current bar.
        signals:
            Mapping of ticker → signal (> 0 = buy, <= 0 = flat).
        """
        buy_tickers = [
            t
            for t in self.tickers
            if signals.get(t, 0.0) > 0.0 and t in prices and prices[t] > 0.0
        ]
        if not buy_tickers:
            target_weights = {t: 0.0 for t in self.tickers}
        else:
            w = 1.0 / len(buy_tickers)
            target_weights = {t: (w if t in buy_tickers else 0.0) for t in self.tickers}

        self.rebalance_to_weights(
            date=date,
            prices=prices,
            target_weights=target_weights,
            cost_model=cost_model,
            market_state=market_state,
        )

    def rebalance_to_weights(
        self,
        date: pd.Timestamp,
        prices: Dict[str, float],
        target_weights: Dict[str, float],
        cost_model: Optional[Any] = None,
        market_state: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """Rebalance portfolio to target notional weights (supports long/short)."""
        equity_before = self.total_value(prices)
        if equity_before <= 0.0:
            self.equity_curve.append(equity_before)
            self.dates.append(date)
            self.daily_turnover.append(0.0)
            self.daily_costs.append(0.0)
            return

        turnover = 0.0
        total_cost = 0.0

        for ticker in self.tickers:
            price = float(prices.get(ticker, 0.0))
            if price <= 0.0:
                continue

            target_weight = float(target_weights.get(ticker, 0.0))
            target_shares = (target_weight * equity_before) / price
            current_shares = float(self.positions.get(ticker, 0.0))
            trade_shares = target_shares - current_shares

            if abs(trade_shares) <= 1e-12:
                continue

            trade_notional = abs(trade_shares * price)
            turnover += trade_notional

            trade_cost = 0.0
            if cost_model is not None:
                ticker_state = (market_state or {}).get(ticker, {})
                breakdown = cost_model.estimate(
                    trade_shares=trade_shares,
                    price=price,
                    market_state=ticker_state,
                )
                trade_cost = float(getattr(breakdown, "total", 0.0))

            self.cash -= trade_shares * price
            self.cash -= trade_cost
            total_cost += trade_cost
            self.positions[ticker] = target_shares

        self.equity_curve.append(self.total_value(prices))
        self.dates.append(date)
        self.daily_turnover.append(turnover)
        self.daily_costs.append(total_cost)

    def total_value(self, prices: Dict[str, float]) -> float:
        """Return total portfolio value (cash + open positions)."""
        position_value = sum(
            self.positions[t] * prices[t]
            for t in self.tickers
            if t in prices
        )
        return self.cash + position_value

    # keeping legacy helper structure intentionally minimal, weighted rebalancing
    # now handles both the old long only flow and the new long/short flow