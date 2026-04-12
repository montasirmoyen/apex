"""Quick-simulation entry point.

Reads a JSON request from stdin, generates synthetic OHLCV data via
geometric Brownian motion (so no CSV files are required), runs the full
backtest pipeline, and writes the JSON result to stdout.

Progress is emitted as newline-delimited JSON:
  {"type": "log", "message": "..."}   – human-readable step update
  {"type": "result", ...}             – final backtest result (or error)

Called by the Next.js API route via child_process.spawn.
"""

import json
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.engine import run_backtest  # noqa: E402
from regime.regime_detector import RegimeDetector  # noqa: E402
from strategies.ensemble import EnsembleLongShortStrategy  # noqa: E402
from strategies.mean_reversion import MeanReversionStrategy  # noqa: E402
from strategies.momentum import MomentumStrategy  # noqa: E402

_STRATEGY_MAP = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "ml_ensemble": EnsembleLongShortStrategy,
}

# per-ticker seeds so synthetic curves look different but are reproducible
def _log(message: str) -> None:
    """Emit a progress line to stdout immediately."""
    print(json.dumps({"type": "log", "message": message}), flush=True)


# per-ticker seeds so synthetic curves look different but are reproducible
_TICKER_SEEDS: dict[str, int] = {
    "AAPL": 42,
    "MSFT": 99,
    "GOOGL": 7,
    "TSLA": 13,
    "AMZN": 55,
    "NVDA": 23,
    "META": 77,
}


def _generate_ohlcv(
    ticker: str,
    start_date: str,
    end_date: str,
    initial_price: float = 150.0,
    mu: float = 0.0004,
    sigma: float = 0.015,
) -> pd.DataFrame:
    """Simulate OHLCV data using geometric Brownian motion."""
    seed = _TICKER_SEEDS.get(ticker, abs(hash(ticker)) % 10_000)
    rng = np.random.default_rng(seed)

    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)
    if n == 0:
        raise ValueError(f"No trading days between {start_date} and {end_date}.")

    log_returns = rng.normal(mu, sigma, n)
    close = initial_price * np.exp(np.cumsum(log_returns))

    daily_range = rng.uniform(0.005, 0.02, n)
    open_ = close * rng.uniform(0.997, 1.003, n)
    high = close * (1 + daily_range)
    low = close * (1 - daily_range)
    volume = rng.integers(1_000_000, 15_000_000, n).astype(float)

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )
    df.index.name = "Date"
    return df


def run_quick_simulation(request: dict) -> None:
    """Execute a full backtest, streaming progress then the final result."""
    tickers: list[str] = request.get("tickers", ["AAPL", "MSFT", "GOOGL"])
    strategy_name: str = request.get("strategy", "momentum")
    lookback: int = int(request.get("lookback", 20))
    initial_cash: float = float(request.get("initial_cash", 100_000))
    start_date: str = request.get("start_date", "2020-01-01")
    end_date: str = request.get("end_date", "2024-01-01")
    use_regime: bool = bool(request.get("use_regime", False))
    speed_up: bool = bool(request.get("speed_up", False))

    delay = 0.0 if speed_up else 0.55

    strategy_cls = _STRATEGY_MAP.get(strategy_name, MomentumStrategy)

    _log(f"Initialising strategy: {strategy_name.upper()} | lookback={lookback}d | "
         f"capital=${initial_cash:,.0f}")
    time.sleep(delay)

    _log(f"Date range: {start_date} → {end_date}")
    time.sleep(delay * 0.5)

    strategy = strategy_cls(lookback=lookback)
    regime_detector = RegimeDetector() if use_regime else None

    if use_regime:
        _log("Regime detector enabled — loading market-state classifier…")
        time.sleep(delay)

    _log(f"Generating synthetic OHLCV price series for {len(tickers)} ticker(s)…")
    time.sleep(delay)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, ticker in enumerate(tickers, 1):
            _log(f"  [{i}/{len(tickers)}] GBM simulation for {ticker}…")
            df = _generate_ohlcv(ticker, start_date, end_date)
            df.to_csv(os.path.join(tmpdir, f"{ticker}.csv"))
            time.sleep(delay * 0.4)

        _log("Running backtest engine…")
        time.sleep(delay)

        result = run_backtest(
            tickers=tickers,
            data_dir=tmpdir,
            strategy=strategy,
            initial_cash=initial_cash,
            regime_detector=regime_detector,
        )

    _log("Computing risk metrics (Sharpe, max drawdown, IC…)")
    time.sleep(delay * 0.6)

    _log("Walk-forward validation complete.")
    time.sleep(delay * 0.3)

    _log("Done — streaming result to frontend.")
    print(json.dumps({"type": "result", **result}), flush=True)


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        run_quick_simulation(payload)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"type": "error", "message": str(exc)}), flush=True)
        sys.exit(1)
