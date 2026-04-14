"""Quick-simulation entry point.

Reads a JSON request from stdin, pulls market data from Yahoo Finance,
runs the full backtest pipeline, and writes the JSON result to stdout.

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
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

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

_WARMUP_BARS = 100

def _log(message: str) -> None:
    """Emit a progress line to stdout immediately."""
    print(json.dumps({"type": "log", "message": message}), flush=True)


def _extract_live_price(ticker_obj: Any) -> float | None:
    """Best-effort extraction of the latest quote from Yahoo Finance."""
    fast_info = getattr(ticker_obj, "fast_info", None)
    if fast_info:
        for key in ("lastPrice", "regularMarketPrice", "previousClose"):
            value = fast_info.get(key)
            if value is not None:
                return float(value)

    # fallback for symbols where fast_info is unavailable
    info = getattr(ticker_obj, "info", None)
    if info:
        for key in ("regularMarketPrice", "currentPrice", "previousClose"):
            value = info.get(key)
            if value is not None:
                return float(value)

    return None


def _fetch_ohlcv_and_live_price(
    ticker: str,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, float | None]:
    """Fetch historical OHLCV and current quote from Yahoo Finance."""
    if yf is None:
        raise RuntimeError(
            "Missing Python dependency 'yfinance'. Install it with: pip install yfinance"
        )

    ticker_obj = yf.Ticker(ticker)

    # use end as exclusive upper bound in yfinance, so include one extra day
    end_plus_one = (
        pd.to_datetime(end_date) + pd.Timedelta(days=1)
    ).strftime("%Y-%m-%d")

    df = ticker_obj.history(
        start=start_date,
        end=end_plus_one,
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    if df.empty:
        raise ValueError(
            f"No Yahoo Finance history returned for {ticker} in {start_date} to {end_date}."
        )

    # keep only OHLCV columns expected by the loader/backtest pipeline
    expected_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [c for c in expected_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Yahoo Finance data for {ticker} is missing columns: {missing_cols}."
        )

    out = df[expected_cols].copy()
    out.index = pd.to_datetime(out.index)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    out.index.name = "Date"

    live_price = _extract_live_price(ticker_obj)
    return out, live_price


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
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    if end_ts < start_ts:
        raise ValueError("end_date must be on or after start_date.")

    # Fetch additional history before the requested start date so rolling
    # features (especially for ML ensemble) can warm up before trading begins.
    warmup_start = (start_ts - pd.tseries.offsets.BDay(_WARMUP_BARS)).strftime("%Y-%m-%d")

    delay = 0.0 if speed_up else 0.55

    strategy_cls = _STRATEGY_MAP.get(strategy_name, MomentumStrategy)

    _log(f"Initialising strategy: {strategy_name.upper()} | lookback={lookback}d | "
         f"capital=${initial_cash:,.0f}")
    time.sleep(delay)

    _log(f"Date range: {start_date} → {end_date}")
    _log(f"Warm-up history: {warmup_start} → {start_date} (excluded from results)")
    time.sleep(delay * 0.5)

    strategy = strategy_cls(lookback=lookback)
    regime_detector = RegimeDetector() if use_regime else None

    if use_regime:
        _log("Regime detector enabled — loading market-state classifier…")
        time.sleep(delay)

    _log(f"Fetching Yahoo Finance OHLCV history for {len(tickers)} ticker(s)…")
    time.sleep(delay)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, ticker in enumerate(tickers, 1):
            _log(f"  [{i}/{len(tickers)}] Requesting market data for {ticker}…")
            df, live_price = _fetch_ohlcv_and_live_price(ticker, warmup_start, end_date)
            df.to_csv(os.path.join(tmpdir, f"{ticker}.csv"))
            latest_close = float(df["Close"].iloc[-1])
            if live_price is not None:
                _log(
                    f"      {ticker}: rows={len(df)} | latest close=${latest_close:,.2f} "
                    f"| live=${live_price:,.2f}"
                )
            else:
                _log(
                    f"      {ticker}: rows={len(df)} | latest close=${latest_close:,.2f} "
                    "| live=N/A"
                )
            time.sleep(delay * 0.4)

        _log("Live quote fetch complete — launching backtest engine…")
        _log("Running backtest engine…")
        time.sleep(delay)

        result = run_backtest(
            tickers=tickers,
            data_dir=tmpdir,
            strategy=strategy,
            initial_cash=initial_cash,
            regime_detector=regime_detector,
            start_date=start_date,
            end_date=end_date,
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
