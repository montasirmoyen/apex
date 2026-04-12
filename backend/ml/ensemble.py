from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge
except Exception:  # noqa: BLE001
    Ridge = None

try:
    from lightgbm import LGBMRanker
except Exception:  # noqa: BLE001
    LGBMRanker = None

try:
    from xgboost import XGBRegressor
except Exception:  # noqa: BLE001
    XGBRegressor = None


@dataclass
class ModelAvailability:
    lgbm_ranker: bool
    ridge: bool
    xgboost: bool


class EnsembleScorer:
    """Blend LGBMRanker, Ridge and XGBoost predictions into one score."""

    def __init__(self, random_state: int = 7) -> None:
        self.random_state = random_state
        self._ridge = None
        self._lgbm = None
        self._xgb = None
        self._fit = False
        self._feature_mean: Optional[np.ndarray] = None

    def availability(self) -> ModelAvailability:
        return ModelAvailability(
            lgbm_ranker=LGBMRanker is not None,
            ridge=Ridge is not None,
            xgboost=XGBRegressor is not None,
        )

    def fit(self, x: pd.DataFrame, y: pd.Series) -> None:
        if x.empty or y.empty:
            return

        x_np = x.to_numpy(dtype=float)
        y_np = y.to_numpy(dtype=float)
        self._feature_mean = np.nanmean(x_np, axis=0)

        if Ridge is not None:
            self._ridge = Ridge(alpha=1.0, random_state=self.random_state)
            self._ridge.fit(x_np, y_np)

        if LGBMRanker is not None:
            # use one ranking group, for cross-sectional alpha this is still useful
            self._lgbm = LGBMRanker(
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=31,
                objective="lambdarank",
                random_state=self.random_state,
                min_data_in_leaf=10,
                verbosity=-1,
            )
            self._lgbm.fit(x_np, y_np, group=[len(y_np)])

        if XGBRegressor is not None:
            self._xgb = XGBRegressor(
                n_estimators=120,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=self.random_state,
                n_jobs=1,
                objective="reg:squarederror",
                verbosity=0,
            )
            self._xgb.fit(x_np, y_np)

        self._fit = True

    def predict(self, x: pd.DataFrame) -> pd.Series:
        if x.empty:
            return pd.Series(dtype=float)

        if not self._fit:
            # fallback if not enough training samples yet
            return x.mean(axis=1)

        x_np = x.to_numpy(dtype=float)
        preds: Dict[str, np.ndarray] = {}

        if self._ridge is not None:
            preds["ridge"] = self._ridge.predict(x_np)
        if self._lgbm is not None:
            preds["lgbm"] = self._lgbm.predict(x_np)
        if self._xgb is not None:
            preds["xgb"] = self._xgb.predict(x_np)

        if not preds:
            return x.mean(axis=1)

        frame = pd.DataFrame(preds, index=x.index)
        blended = frame.mean(axis=1)

        std = float(blended.std(ddof=0))
        if std <= 1e-12 or not np.isfinite(std):
            return pd.Series(0.0, index=x.index)

        return ((blended - blended.mean()) / std).fillna(0.0)


class RegimeConditionalCalibrator:
    """Regime-specific score scaling from historical rank IC."""

    def __init__(self) -> None:
        self._regime_strength: Dict[str, float] = {
            "bull": 1.0,
            "bear": 1.0,
            "highvol": 0.8,
            "normal": 1.0,
        }

    def fit(self, history: pd.DataFrame) -> None:
        if history.empty:
            return
        for regime, grp in history.groupby("regime"):
            if len(grp) < 10:
                continue
            corr = float(grp["score"].corr(grp["target"]))
            if np.isnan(corr):
                continue
            # keep multiplier bounded so one regime cannot dominate position sizing
            self._regime_strength[regime] = float(np.clip(1.0 + corr, 0.4, 1.6))

    def scale(self, regime: str) -> float:
        return self._regime_strength.get(regime, 1.0)

    def strengths(self) -> Dict[str, float]:
        return dict(self._regime_strength)


class ICTracker:
    """Tracks cross-sectional IC over time."""

    def __init__(self) -> None:
        self._ic: list[float] = []

    def update(self, scores: pd.Series, next_returns: pd.Series) -> None:
        aligned = pd.concat([scores, next_returns], axis=1, join="inner").dropna()
        if len(aligned) < 3:
            return
        ic = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
        if np.isfinite(ic):
            self._ic.append(ic)

    def values(self) -> Iterable[float]:
        return list(self._ic)

    def mean(self) -> float:
        if not self._ic:
            return 0.0
        return float(np.mean(self._ic))
