from typing import Any, Dict, List, Optional

import pandas as pd

from data.loader import load_price_data
from strategies.base import Strategy
from portfolio.portfolio import Portfolio
from backtest.metrics import compute_metrics
from regime.regime_detector import RegimeDetector
from execution.costs import CostModel


def run_backtest(
    tickers: List[str],
    data_dir: str,
    strategy: Strategy,
    initial_cash: float = 100_000.0,
    regime_detector: Optional[RegimeDetector] = None,
) -> Dict[str, Any]:
    """Run a day-by-day backtest over historical OHLCV data.

    The engine is strict about lookahead bias: on each bar *t*, only data up
    to and including bar *t* is visible to the strategy. Trades are executed
    at the close price of bar *t*.

    Parameters
    ----------
    tickers:
        List of ticker symbols to include.
    data_dir:
        Directory containing ``<TICKER>.csv`` files.
    strategy:
        A ``Strategy`` instance (e.g. ``MomentumStrategy``).
    initial_cash:
        Starting capital. Default: 100 000.
    regime_detector:
        Optional ``RegimeDetector``. When supplied and the detected regime is
        ``"bear"``, all signals for that ticker are overridden to 0 (flat).

    Returns
    -------
    Dict with keys: ``equity_curve``, ``dates``, ``total_return``,
    ``sharpe``, ``max_drawdown``.
    """
    price_data = load_price_data(tickers, data_dir)

    # align all tickers to dates where every ticker has a close price
    all_closes = pd.DataFrame(
        {ticker: df["Close"] for ticker, df in price_data.items()}
    ).dropna()

    if all_closes.empty:
        raise ValueError("No overlapping dates found across the provided tickers.")

    common_dates = all_closes.index
    portfolio = Portfolio(tickers=tickers, initial_cash=initial_cash)
    cost_model = CostModel(slippage_bps=1.0, commission_per_trade=1.0, impact_eta=0.06)
    is_cross_sectional = strategy.supports_cross_sectional()

    for date in common_dates:
        prices: Dict[str, float] = {}
        histories: Dict[str, pd.DataFrame] = {}
        signals: Dict[str, float] = {}
        market_state: Dict[str, Dict[str, float]] = {}

        for ticker in tickers:
            # slice history up to and including the current bar, no lookahead
            df_history = price_data[ticker].loc[:date]
            histories[ticker] = df_history
            current_price = float(df_history["Close"].iloc[-1])
            prices[ticker] = current_price

            returns = df_history["Close"].pct_change().dropna()
            sigma_20 = float(returns.tail(20).std()) if len(returns) >= 2 else 0.02
            if "Volume" in df_history.columns:
                adv_20 = float((df_history["Volume"] * df_history["Close"]).tail(20).mean())
            else:
                adv_20 = float(current_price * 1_000_000)
            market_state[ticker] = {
                "sigma_20": sigma_20 if sigma_20 > 0 else 0.02,
                "adv_20": adv_20 if adv_20 > 1 else float(current_price * 1_000_000),
            }

            if not is_cross_sectional:
                # Regime gate: suppress long signals in bear markets
                if regime_detector is not None:
                    regime = regime_detector.detect(df_history["Close"])
                    if regime == "bear":
                        signals[ticker] = 0.0
                        continue

                signals[ticker] = strategy.generate_signals(df_history)

        if is_cross_sectional:
            target_weights = strategy.generate_target_weights(
                date=date,
                data_by_ticker=histories,
                prices=prices,
                portfolio=portfolio,
            )

            portfolio.rebalance_to_weights(
                date=date,
                prices=prices,
                target_weights=target_weights,
                cost_model=cost_model,
                market_state=market_state,
            )
        else:
            portfolio.update(
                date=date,
                prices=prices,
                signals=signals,
                cost_model=cost_model,
                market_state=market_state,
            )

    return compute_metrics(
        portfolio,
        diagnostics={
            "strategy": strategy.get_diagnostics(),
        },
    )
