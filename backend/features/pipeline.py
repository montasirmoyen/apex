from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


_MIN_HISTORY = 80


@dataclass
class FeatureSnapshot:
    date: pd.Timestamp
    features: pd.DataFrame
    prices: Dict[str, float]


class FeaturePipeline:
    """Build a robust cross-sectional feature table without lookahead leakage."""

    def __init__(self, zscore_clip: float = 5.0) -> None:
        self.zscore_clip = zscore_clip

    def build_cross_section(self, data_by_ticker: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows: List[Dict[str, float]] = []

        for ticker, history in data_by_ticker.items():
            if len(history) < _MIN_HISTORY:
                continue
            row = self._feature_row(history)
            if row is None:
                continue
            row["ticker"] = ticker
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        raw = pd.DataFrame(rows).set_index("ticker")
        return self._cross_sectional_zscore(raw)

    def _feature_row(self, history: pd.DataFrame) -> Dict[str, float] | None:
        close = history["Close"].astype(float)
        volume = history["Volume"].astype(float) if "Volume" in history else pd.Series(index=close.index, dtype=float)

        if close.isna().all():
            return None

        r1 = close.pct_change(1)
        r2 = close.pct_change(2)
        r3 = close.pct_change(3)
        r5 = close.pct_change(5)
        r10 = close.pct_change(10)
        r21 = close.pct_change(21)
        r42 = close.pct_change(42)
        r63 = close.pct_change(63)

        vol5 = r1.rolling(5).std()
        vol10 = r1.rolling(10).std()
        vol21 = r1.rolling(21).std()
        vol63 = r1.rolling(63).std()

        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()

        bb_mid = ma20
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        gains = r1.clip(lower=0)
        losses = -r1.clip(upper=0)
        avg_gain = gains.rolling(14).mean()
        avg_loss = losses.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi14 = 100.0 - (100.0 / (1.0 + rs))

        rolling_max20 = close.rolling(20).max()
        rolling_min20 = close.rolling(20).min()
        stoch = (close - rolling_min20) / (rolling_max20 - rolling_min20).replace(0.0, np.nan)

        dollar_volume = (close * volume).rolling(20).mean() if not volume.empty else pd.Series(np.nan, index=close.index)

        features = {
            "ret_1d": r1.iloc[-1],
            "ret_2d": r2.iloc[-1],
            "ret_3d": r3.iloc[-1],
            "ret_5d": r5.iloc[-1],
            "ret_10d": r10.iloc[-1],
            "ret_21d": r21.iloc[-1],
            "ret_42d": r42.iloc[-1],
            "ret_63d": r63.iloc[-1],
            "ret_5_21_ratio": _safe_div(r5.iloc[-1], r21.iloc[-1]),
            "vol_5d": vol5.iloc[-1],
            "vol_10d": vol10.iloc[-1],
            "vol_21d": vol21.iloc[-1],
            "vol_63d": vol63.iloc[-1],
            "vol_5_21_ratio": _safe_div(vol5.iloc[-1], vol21.iloc[-1]),
            "vol_10_63_ratio": _safe_div(vol10.iloc[-1], vol63.iloc[-1]),
            "price_vs_ma5": _safe_div(close.iloc[-1], ma5.iloc[-1]) - 1.0,
            "price_vs_ma10": _safe_div(close.iloc[-1], ma10.iloc[-1]) - 1.0,
            "price_vs_ma20": _safe_div(close.iloc[-1], ma20.iloc[-1]) - 1.0,
            "price_vs_ma50": _safe_div(close.iloc[-1], ma50.iloc[-1]) - 1.0,
            "ma5_vs_ma20": _safe_div(ma5.iloc[-1], ma20.iloc[-1]) - 1.0,
            "ma10_vs_ma50": _safe_div(ma10.iloc[-1], ma50.iloc[-1]) - 1.0,
            "ema12_vs_ema26": _safe_div(ema12.iloc[-1], ema26.iloc[-1]) - 1.0,
            "macd": macd.iloc[-1],
            "macd_signal_gap": (macd - macd_signal).iloc[-1],
            "rsi14": rsi14.iloc[-1],
            "rsi14_centered": rsi14.iloc[-1] - 50.0,
            "bb_pos": _safe_div(close.iloc[-1] - bb_lower.iloc[-1], (bb_upper - bb_lower).iloc[-1]),
            "bb_width": _safe_div((bb_upper - bb_lower).iloc[-1], bb_mid.iloc[-1]),
            "stoch20": stoch.iloc[-1],
            "dollar_volume_20": dollar_volume.iloc[-1],
            "volume_change_5": _safe_div(volume.iloc[-1], volume.rolling(5).mean().iloc[-1]) - 1.0 if not volume.empty else np.nan,
            "lag_ret_1": r1.shift(1).iloc[-1],
            "lag_ret_2": r1.shift(2).iloc[-1],
            "lag_ret_3": r1.shift(3).iloc[-1],
            "lag_ret_4": r1.shift(4).iloc[-1],
            "lag_ret_5": r1.shift(5).iloc[-1],
            "downside_vol_21": r1.clip(upper=0).rolling(21).std().iloc[-1],
            "upside_vol_21": r1.clip(lower=0).rolling(21).std().iloc[-1],
        }

        out = {k: _finite(v) for k, v in features.items()}
        return out

    def _cross_sectional_zscore(self, frame: pd.DataFrame) -> pd.DataFrame:
        zs = frame.copy()
        for col in zs.columns:
            series = zs[col]
            mean = float(series.mean())
            std = float(series.std(ddof=0))
            if std <= 1e-12 or not np.isfinite(std):
                zs[col] = 0.0
                continue
            z = (series - mean) / std
            zs[col] = z.clip(-self.zscore_clip, self.zscore_clip).fillna(0.0)

        return zs.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    @staticmethod
    def feature_names() -> Iterable[str]:
        return [
            "ret_1d",
            "ret_2d",
            "ret_3d",
            "ret_5d",
            "ret_10d",
            "ret_21d",
            "ret_42d",
            "ret_63d",
            "ret_5_21_ratio",
            "vol_5d",
            "vol_10d",
            "vol_21d",
            "vol_63d",
            "vol_5_21_ratio",
            "vol_10_63_ratio",
            "price_vs_ma5",
            "price_vs_ma10",
            "price_vs_ma20",
            "price_vs_ma50",
            "ma5_vs_ma20",
            "ma10_vs_ma50",
            "ema12_vs_ema26",
            "macd",
            "macd_signal_gap",
            "rsi14",
            "rsi14_centered",
            "bb_pos",
            "bb_width",
            "stoch20",
            "dollar_volume_20",
            "volume_change_5",
            "lag_ret_1",
            "lag_ret_2",
            "lag_ret_3",
            "lag_ret_4",
            "lag_ret_5",
            "downside_vol_21",
            "upside_vol_21",
        ]


def _safe_div(a: float, b: float) -> float:
    if b is None or not np.isfinite(b) or abs(b) < 1e-12:
        return np.nan
    return float(a) / float(b)


def _finite(v: float) -> float:
    if v is None or not np.isfinite(v):
        return 0.0
    return float(v)
