import os
from typing import Dict, List

import pandas as pd

# map common csv column name variants to canonical names
_COLUMN_ALIASES: Dict[str, str] = {
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "adj close": "Close",
    "adjusted close": "Close",
    "volume": "Volume",
}


def load_price_data(tickers: List[str], data_dir: str) -> Dict[str, pd.DataFrame]:
    """Load OHLCV data from CSV files, one file per ticker.

    Each CSV must have a date column as its first column (used as index)
    and at minimum a 'Close' column. Column names are case-insensitive.

    Parameters
    ----------
    tickers:
        List of ticker symbols, e.g. ["AAPL", "MSFT"].
    data_dir:
        Directory that contains ``<TICKER>.csv`` files.

    Returns
    -------
    Dict mapping ticker → DataFrame with DatetimeIndex and columns
    Open, High, Low, Close, Volume (subset may be present).
    """
    data: Dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        path = os.path.join(data_dir, f"{ticker}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Data file not found: {path}")

        df = pd.read_csv(path, parse_dates=True, index_col=0)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)

        # normalise column names
        df.columns = [
            _COLUMN_ALIASES.get(c.strip().lower(), c.strip().title())
            for c in df.columns
        ]

        if "Close" not in df.columns:
            raise ValueError(f"No 'Close' column found in {path}. Columns: {list(df.columns)}")

        data[ticker] = df

    return data