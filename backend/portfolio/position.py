from dataclasses import dataclass, field


@dataclass
class Position:
    """Represents an open position in a single asset.

    Parameters
    ----------
    ticker:
        The asset's ticker symbol.
    shares:
        Number of shares held. Use fractional shares for simplicity.
    avg_cost:
        Average cost basis per share (purchase price). Used for P&L tracking.
    """

    ticker: str
    shares: float = 0.0
    avg_cost: float = 0.0

    def market_value(self, current_price: float) -> float:
        """Return the current market value of this position."""
        return self.shares * current_price

    def unrealised_pnl(self, current_price: float) -> float:
        """Return unrealised profit/loss against the average cost basis."""
        return (current_price - self.avg_cost) * self.shares