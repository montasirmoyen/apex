"""Entry point called by the Next.js API route via a subprocess or HTTP call."""

from typing import Any, Dict

from backtest.engine import run_backtest
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.ensemble import EnsembleLongShortStrategy
from regime.regime_detector import RegimeDetector


_STRATEGIES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "ml_ensemble": EnsembleLongShortStrategy,
}


def simulate(request_json: Dict[str, Any]) -> Dict[str, Any]:
    """Run a backtest from a JSON request payload.

    Expected keys in *request_json*:
    - ``tickers``       : list of ticker symbols, e.g. ["AAPL", "MSFT"]
    - ``data_dir``      : path to directory containing CSV files
    - ``strategy``      : strategy name ("momentum" or "mean_reversion")
    - ``initial_cash``  : starting capital (optional, default 100 000)
    - ``lookback``      : strategy look-back window (optional, default 20)
    - ``use_regime``    : bool — whether to apply regime filter (optional)
    """
    tickers: list = request_json["tickers"]
    data_dir: str = request_json["data_dir"]
    strategy_name: str = request_json.get("strategy", "momentum")
    initial_cash: float = float(request_json.get("initial_cash", 100_000.0))
    lookback: int = int(request_json.get("lookback", 20))
    use_regime: bool = bool(request_json.get("use_regime", False))

    strategy_cls = _STRATEGIES.get(strategy_name)
    if strategy_cls is None:
        raise ValueError(f"Unknown strategy '{strategy_name}'. Choose from: {list(_STRATEGIES)}.")

    strategy = strategy_cls(lookback=lookback)
    regime_detector = RegimeDetector() if use_regime else None

    return run_backtest(
        tickers=tickers,
        data_dir=data_dir,
        strategy=strategy,
        initial_cash=initial_cash,
        regime_detector=regime_detector,
    )
