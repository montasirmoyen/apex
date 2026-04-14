export interface SimulationRequest {
  tickers: string[]
  strategy: "momentum" | "mean_reversion" | "ml_ensemble"
  lookback: number
  initial_cash: number
  start_date: string
  end_date: string
  use_regime: boolean
}

export interface WalkForwardWindow {
  window: number
  start: string
  end: string
  total_return: number
  sharpe: number
}

export interface SimulationResult {
  equity_curve: number[]
  dates: string[]
  total_return: number
  sharpe: number
  max_drawdown: number
  deflated_sharpe_ratio?: number
  walk_forward?: WalkForwardWindow[]
  mean_oos_sharpe?: number
  positive_windows?: number
  mean_ic?: number
  mean_turnover?: number
  total_cost?: number
  diagnostics?: Record<string, unknown>
}

// preset used by the quick simulation button
export const QUICK_PRESET: SimulationRequest = {
  tickers: ["NVDA", "TSLA"],
  strategy: "momentum",
  lookback: 20,
  initial_cash: 100_000,
  start_date: "2026-01-01",
  end_date: "2026-02-25",
  use_regime: false,
}
