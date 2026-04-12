from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from features.pipeline import FeaturePipeline
from ml.ensemble import EnsembleScorer, ICTracker, RegimeConditionalCalibrator
from risk.manager import RiskManager, classify_market_regime
from strategies.base import Strategy


@dataclass
class PendingSnapshot:
    features: pd.DataFrame
    scores: pd.Series
    prices: Dict[str, float]
    regime: str


class EnsembleLongShortStrategy(Strategy):
    """Cross-sectional long/short strategy with ensemble model scoring."""

    def __init__(
        self,
        lookback: int = 63,
        long_short_quantile: float = 0.2,
        min_train_rows: int = 500,
        training_window: int = 5000,
    ) -> None:
        self.lookback = max(lookback, 20)
        self.long_short_quantile = float(np.clip(long_short_quantile, 0.05, 0.45))
        self.min_train_rows = min_train_rows
        self.training_window = training_window

        self.pipeline = FeaturePipeline()
        self.scorer = EnsembleScorer()
        self.calibrator = RegimeConditionalCalibrator()
        self.risk_manager = RiskManager()
        self.ic_tracker = ICTracker()

        self._pending: Optional[PendingSnapshot] = None
        self._training_rows = pd.DataFrame()
        self._regime_counts: Dict[str, int] = {"bull": 0, "bear": 0, "highvol": 0, "normal": 0}

    def supports_cross_sectional(self) -> bool:
        return True

    def generate_target_weights(
        self,
        date: pd.Timestamp,
        data_by_ticker: Dict[str, pd.DataFrame],
        prices: Dict[str, float],
        portfolio=None,
    ) -> Dict[str, float]:
        features = self.pipeline.build_cross_section(data_by_ticker)
        tickers = list(prices)

        if features.empty:
            return {t: 0.0 for t in tickers}

        market_returns = _market_returns(data_by_ticker)
        regime = classify_market_regime(market_returns)
        self._regime_counts[regime] = self._regime_counts.get(regime, 0) + 1

        self._realize_pending_labels(prices)
        self._fit_models_if_ready(features.columns)

        base_scores = self.scorer.predict(features)
        scaled_scores = base_scores * self.calibrator.scale(regime)

        target_weights = self._scores_to_dollar_neutral_weights(scaled_scores)

        drawdown = _current_drawdown(prices, portfolio)
        target_weights = self.risk_manager.apply(target_weights, features, market_returns, drawdown)

        self._pending = PendingSnapshot(
            features=features.copy(),
            scores=base_scores.copy(),
            prices={k: float(v) for k, v in prices.items()},
            regime=regime,
        )

        return {t: float(target_weights.get(t, 0.0)) for t in tickers}

    def get_diagnostics(self) -> Dict[str, object]:
        availability = self.scorer.availability()
        return {
            "ensemble": {
                "models": {
                    "lgbm_ranker": availability.lgbm_ranker,
                    "ridge": availability.ridge,
                    "xgboost": availability.xgboost,
                },
                "mean_ic": self.ic_tracker.mean(),
                "ic_values": list(self.ic_tracker.values()),
            },
            "regimes": {
                "counts": dict(self._regime_counts),
                "scalers": self.calibrator.strengths(),
            },
        }

    def _realize_pending_labels(self, current_prices: Dict[str, float]) -> None:
        if self._pending is None:
            return

        prev = self._pending
        shared = [t for t in prev.features.index if t in current_prices and t in prev.prices]
        if not shared:
            self._pending = None
            return

        next_returns = pd.Series(
            {
                t: float(current_prices[t]) / float(prev.prices[t]) - 1.0
                for t in shared
                if prev.prices[t] > 0.0
            }
        )

        realized_scores = prev.scores.reindex(next_returns.index).dropna()
        next_returns = next_returns.reindex(realized_scores.index).dropna()
        self.ic_tracker.update(realized_scores, next_returns)

        rows = prev.features.reindex(realized_scores.index).copy()
        rows["target"] = next_returns
        rows["score"] = realized_scores
        rows["regime"] = prev.regime

        self._training_rows = pd.concat([self._training_rows, rows], axis=0)
        if len(self._training_rows) > self.training_window:
            self._training_rows = self._training_rows.tail(self.training_window)

        self.calibrator.fit(self._training_rows[["regime", "score", "target"]].dropna())
        self._pending = None

    def _fit_models_if_ready(self, feature_cols: pd.Index) -> None:
        if self._training_rows.empty:
            return

        train = self._training_rows.dropna()
        if len(train) < self.min_train_rows:
            return

        x = train[list(feature_cols)]
        y = train["target"]
        self.scorer.fit(x, y)

    def _scores_to_dollar_neutral_weights(self, scores: pd.Series) -> pd.Series:
        if scores.empty:
            return pd.Series(dtype=float)

        ranks = scores.rank(pct=True)
        longs = ranks >= (1.0 - self.long_short_quantile)
        shorts = ranks <= self.long_short_quantile

        weights = pd.Series(0.0, index=scores.index, dtype=float)

        long_scores = scores[longs].clip(lower=0.0)
        if long_scores.abs().sum() <= 1e-12 and len(long_scores) > 0:
            long_scores = pd.Series(1.0, index=long_scores.index)

        short_scores = (-scores[shorts]).clip(lower=0.0)
        if short_scores.abs().sum() <= 1e-12 and len(short_scores) > 0:
            short_scores = pd.Series(1.0, index=short_scores.index)

        if len(long_scores) > 0:
            weights.loc[long_scores.index] = 0.5 * long_scores / long_scores.abs().sum()
        if len(short_scores) > 0:
            weights.loc[short_scores.index] = -0.5 * short_scores / short_scores.abs().sum()

        return weights.fillna(0.0)


def _market_returns(data_by_ticker: Dict[str, pd.DataFrame]) -> pd.Series:
    closes = pd.DataFrame(
        {ticker: df["Close"].astype(float) for ticker, df in data_by_ticker.items() if "Close" in df.columns}
    ).dropna(how="all")
    if closes.empty:
        return pd.Series(dtype=float)
    market_close = closes.mean(axis=1)
    return market_close.pct_change().dropna()


def _current_drawdown(prices: Dict[str, float], portfolio) -> float:
    if portfolio is None:
        return 0.0
    current = float(portfolio.total_value(prices))
    history = list(portfolio.equity_curve)
    if not history:
        return 0.0
    peak = max(max(history), current)
    if peak <= 0.0:
        return 0.0
    return current / peak - 1.0
