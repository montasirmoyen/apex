from math import erf, sqrt
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from portfolio.portfolio import Portfolio


def compute_metrics(
    portfolio: Portfolio,
    diagnostics: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute summary statistics from a completed backtest.

    Parameters
    ----------
    portfolio:
        A ``Portfolio`` instance after the backtest loop has finished.

    Returns
    -------
    Dict with keys:
    - ``equity_curve``  : list of daily portfolio values
    - ``dates``         : list of date strings (ISO format)
    - ``total_return``  : total return as a decimal (e.g. 0.25 = 25 %)
    - ``sharpe``        : annualised Sharpe ratio (risk-free rate = 0)
    - ``max_drawdown``  : maximum drawdown as a negative decimal
    """
    equity = pd.Series(
        portfolio.equity_curve,
        index=pd.DatetimeIndex(portfolio.dates),
        dtype=float,
    )

    if equity.empty:
        return {
            "equity_curve": [],
            "dates": [],
            "total_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "deflated_sharpe_ratio": 0.0,
            "walk_forward": [],
            "mean_oos_sharpe": 0.0,
            "positive_windows": 0,
            "mean_ic": 0.0,
            "mean_turnover": 0.0,
            "total_cost": 0.0,
        }

    daily_returns = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    sharpe = _sharpe_ratio(daily_returns)
    walk_forward = _walk_forward_stats(equity, windows=6)
    oos_sharpes = [w["sharpe"] for w in walk_forward]

    strategy_diag = (diagnostics or {}).get("strategy", {}) if diagnostics else {}
    ensemble_diag = strategy_diag.get("ensemble", {}) if isinstance(strategy_diag, dict) else {}
    ic_values = ensemble_diag.get("ic_values", []) if isinstance(ensemble_diag, dict) else []

    mean_turnover = float(np.mean(portfolio.daily_turnover)) if portfolio.daily_turnover else 0.0
    total_cost = float(np.sum(portfolio.daily_costs)) if portfolio.daily_costs else 0.0

    out = {
        "equity_curve": [round(v, 4) for v in equity.tolist()],
        "dates": [str(d.date()) for d in portfolio.dates],
        "total_return": round(total_return, 6),
        "sharpe": round(sharpe, 6),
        "max_drawdown": round(_max_drawdown(equity), 6),
        "deflated_sharpe_ratio": round(_deflated_sharpe_ratio(daily_returns, sharpe), 6),
        "walk_forward": walk_forward,
        "mean_oos_sharpe": round(float(np.mean(oos_sharpes)) if oos_sharpes else 0.0, 6),
        "positive_windows": int(sum(1 for w in walk_forward if w["total_return"] > 0.0)),
        "mean_ic": round(float(np.mean(ic_values)) if ic_values else 0.0, 6),
        "mean_turnover": round(mean_turnover, 4),
        "total_cost": round(total_cost, 4),
    }

    if diagnostics:
        out["diagnostics"] = diagnostics

    return out


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualisation: int = 252,
) -> float:
    """Annualised Sharpe ratio assuming a given risk-free rate (default 0)."""
    if daily_returns.empty:
        return 0.0
    excess = daily_returns - risk_free_rate / annualisation
    std = float(excess.std())
    if std == 0 or np.isnan(std):
        return 0.0
    return float(excess.mean() / std * np.sqrt(annualisation))


def _max_drawdown(equity: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a negative decimal."""
    if equity.empty:
        return 0.0
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    return float(drawdown.min())


def _walk_forward_stats(equity: pd.Series, windows: int = 6) -> List[Dict[str, Any]]:
    if len(equity) < windows * 20:
        windows = max(1, min(windows, len(equity) // 20))
    if windows <= 0:
        return []

    idx_chunks = np.array_split(np.arange(len(equity)), windows)
    out: List[Dict[str, Any]] = []

    for i, idx in enumerate(idx_chunks, start=1):
        if len(idx) < 2:
            continue
        sub = equity.iloc[idx]
        sub_returns = sub.pct_change().dropna()
        total_return = float(sub.iloc[-1] / sub.iloc[0] - 1.0)
        out.append(
            {
                "window": i,
                "start": str(sub.index[0].date()),
                "end": str(sub.index[-1].date()),
                "total_return": round(total_return, 6),
                "sharpe": round(_sharpe_ratio(sub_returns), 6),
            }
        )

    return out


def _deflated_sharpe_ratio(
    daily_returns: pd.Series,
    sharpe: float,
    num_trials: int = 6,
) -> float:
    """Approximate Deflated Sharpe Ratio in [0, 1]."""
    if daily_returns.empty:
        return 0.0

    n = len(daily_returns)
    if n < 3:
        return 0.0

    skew = float(daily_returns.skew())
    kurt = float(daily_returns.kurt()) + 3.0

    variance_sr = (1 - skew * sharpe + ((kurt - 1.0) / 4.0) * (sharpe**2)) / max(n - 1, 1)
    variance_sr = max(variance_sr, 1e-12)

    sr_star = float(np.sqrt(2.0 * np.log(max(num_trials, 1))))
    z = (sharpe - sr_star) / np.sqrt(variance_sr)
    return float(0.5 * (1.0 + erf(z / sqrt(2.0))))
