from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class CostBreakdown:
    slippage: float
    commission: float
    impact: float

    @property
    def total(self) -> float:
        return self.slippage + self.commission + self.impact


class CostModel:
    """Simple realistic execution costs with an Almgren-Chriss-style impact term."""

    def __init__(
        self,
        slippage_bps: float = 1.0,
        commission_per_trade: float = 1.0,
        impact_eta: float = 0.06,
    ) -> None:
        self.slippage_bps = slippage_bps
        self.commission_per_trade = commission_per_trade
        self.impact_eta = impact_eta

    def estimate(
        self,
        trade_shares: float,
        price: float,
        market_state: Dict[str, float],
    ) -> CostBreakdown:
        if abs(trade_shares) <= 1e-12:
            return CostBreakdown(0.0, 0.0, 0.0)

        notional = abs(trade_shares * price)
        slippage = notional * (self.slippage_bps / 10_000.0)
        commission = self.commission_per_trade

        sigma = float(market_state.get("sigma_20", 0.02))
        adv = float(market_state.get("adv_20", max(notional, 1.0)))
        adv = max(adv, 1.0)

        participation = np.sqrt(notional / adv)
        impact = float(self.impact_eta * sigma * participation * notional)
        return CostBreakdown(slippage, commission, impact)
