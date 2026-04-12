"""Live market data helper for Next.js API routes.

Reads JSON from stdin and writes JSON to stdout.

Supported modes:
  - search: {"mode": "search", "query": "apple", "limit": 8}
  - live:   {"mode": "live", "ticker": "AAPL", "period": "1d", "interval": "5m"}
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


def _error(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}), flush=True)
    sys.exit(code)


def _extract_live_price(ticker_obj: Any) -> float | None:
    fast_info = getattr(ticker_obj, "fast_info", None)
    if fast_info:
        for key in ("lastPrice", "regularMarketPrice", "previousClose"):
            value = fast_info.get(key)
            if value is not None:
                return float(value)

    info = getattr(ticker_obj, "info", None)
    if info:
        for key in ("regularMarketPrice", "currentPrice", "previousClose"):
            value = info.get(key)
            if value is not None:
                return float(value)

    return None


def _extract_currency(ticker_obj: Any) -> str | None:
    fast_info = getattr(ticker_obj, "fast_info", None)
    if fast_info:
        value = fast_info.get("currency")
        if isinstance(value, str) and value:
            return value

    info = getattr(ticker_obj, "info", None)
    if info:
        value = info.get("currency")
        if isinstance(value, str) and value:
            return value

    return None


def handle_search(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    limit = int(payload.get("limit", 8))
    if not query:
        return {"results": []}

    search = yf.Search(query, max_results=max(1, min(limit, 20)))
    quotes = getattr(search, "quotes", []) or []

    results: list[dict[str, Any]] = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue

        results.append(
            {
                "symbol": str(symbol).upper(),
                "name": quote.get("shortname") or quote.get("longname") or symbol,
                "exchange": quote.get("exchange") or quote.get("exchDisp") or "",
                "type": quote.get("quoteType") or "",
            }
        )

    return {"results": results}


def handle_live(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = str(payload.get("ticker", "")).strip().upper()
    if not ticker:
        raise ValueError("'ticker' is required")

    period = str(payload.get("period", "1d"))
    interval = str(payload.get("interval", "5m"))

    ticker_obj = yf.Ticker(ticker)
    history = ticker_obj.history(
        period=period,
        interval=interval,
        auto_adjust=False,
        actions=False,
        prepost=False,
    )

    if history.empty:
        raise ValueError(f"No market data returned for ticker '{ticker}'.")

    points: list[dict[str, Any]] = []
    close_series = history["Close"].dropna()
    for idx, value in close_series.items():
        ts = pd.to_datetime(idx)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC")
        points.append({"ts": ts.isoformat(), "price": float(value)})

    live_price = _extract_live_price(ticker_obj)
    last_close = float(close_series.iloc[-1]) if not close_series.empty else None
    previous_close = float(close_series.iloc[-2]) if len(close_series) > 1 else None

    return {
        "ticker": ticker,
        "currency": _extract_currency(ticker_obj) or "USD",
        "live_price": live_price,
        "last_close": last_close,
        "previous_close": previous_close,
        "points": points,
        "updated_at": pd.Timestamp.now("UTC").isoformat(),
    }


def main() -> None:
    if yf is None:
        _error("Missing Python dependency 'yfinance'. Install with pip install yfinance")

    raw = sys.stdin.read()
    if not raw:
        _error("Missing JSON payload")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        _error("Invalid JSON payload")

    mode = str(payload.get("mode", "")).strip().lower()

    try:
        if mode == "search":
            data = handle_search(payload)
        elif mode == "live":
            data = handle_live(payload)
        else:
            raise ValueError("Unsupported mode. Use 'search' or 'live'.")
    except Exception as exc:  # noqa: BLE001
        _error(str(exc))

    print(json.dumps({"ok": True, "data": data}), flush=True)


if __name__ == "__main__":
    main()
