from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def classify_market_regime(market_returns: pd.Series) -> str:
    if len(market_returns) < 30:
        return "normal"

    recent = market_returns.tail(20)
    drift = float(recent.mean())
    vol = float(recent.std(ddof=0))

    if vol > 0.022:
        return "highvol"
    if drift > 0.0008:
        return "bull"
    if drift < -0.0008:
        return "bear"
    return "normal"


class RiskManager:
    """Apply VIX-style deleveraging, neutralisation, dynamic sizing and circuit breaker."""

    def __init__(self, max_gross: float = 1.4, circuit_breaker_dd: float = 0.18) -> None:
        self.max_gross = max_gross
        self.circuit_breaker_dd = circuit_breaker_dd

    def apply(
        self,
        weights: pd.Series,
        features: pd.DataFrame,
        market_returns: pd.Series,
        current_drawdown: float,
    ) -> pd.Series:
        if weights.empty:
            return weights

        out = weights.copy().astype(float)
        out = self._dynamic_position_sizing(out, features)
        out = self._factor_neutralize(out, features)

        deleverage = self._vix_proxy_deleverage(market_returns)
        out *= deleverage

        if abs(current_drawdown) >= self.circuit_breaker_dd:
            out *= 0.15

        gross = float(out.abs().sum())
        if gross > self.max_gross and gross > 0.0:
            out *= self.max_gross / gross

        return out.fillna(0.0)

    def _vix_proxy_deleverage(self, market_returns: pd.Series) -> float:
        if len(market_returns) < 25:
            return 1.0
        vol = float(market_returns.tail(20).std(ddof=0))
        # maps higher market volatility to lower gross leverage
        return float(np.clip(0.03 / max(vol, 1e-6), 0.35, 1.0))

    def _dynamic_position_sizing(self, weights: pd.Series, features: pd.DataFrame) -> pd.Series:
        if "vol_21d" not in features.columns:
            return weights

        inv_vol = 1.0 / features["vol_21d"].replace(0.0, np.nan)
        inv_vol = inv_vol.replace([np.inf, -np.inf], np.nan).fillna(inv_vol.median())
        inv_vol = inv_vol / max(float(inv_vol.mean()), 1e-12)

        adjusted = weights * inv_vol
        gross = float(adjusted.abs().sum())
        if gross <= 1e-12:
            return weights
        return adjusted / gross * float(weights.abs().sum())

    def _factor_neutralize(self, weights: pd.Series, features: pd.DataFrame) -> pd.Series:
        # use a lightweight factor set available from current features
        factor_cols = [c for c in ["vol_63d", "dollar_volume_20", "ret_63d"] if c in features.columns]
        if not factor_cols:
            return weights

        x = features.loc[weights.index, factor_cols].copy()
        x = x.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        w = weights.to_numpy(dtype=float)
        x_np = x.to_numpy(dtype=float)
        # remove linear factor exposure: w' = w - X (X'X)^-1 X' w
        xtx = x_np.T @ x_np
        ridge = np.eye(xtx.shape[0]) * 1e-6

        try:
            beta = np.linalg.solve(xtx + ridge, x_np.T @ w)
        except np.linalg.LinAlgError:
            return weights

        residual = w - x_np @ beta
        return pd.Series(residual, index=weights.index)
