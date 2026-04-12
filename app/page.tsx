"use client"

import { useState } from "react"
import {
  IconBolt,
  IconTrendingUp,
  IconTrendingDown,
  IconChartBar,
  IconAlertCircle,
} from "@tabler/icons-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { EquityChart } from "@/components/chart-1"
import { StrategyForm } from "@/components/strategy-form"
import { runSimulation } from "@/lib/api"
import { QUICK_PRESET } from "@/types/simulation"
import type { SimulationRequest, SimulationResult } from "@/types/simulation"

function pct(n: number) {
  const sign = n >= 0 ? "+" : ""
  return `${sign}${(n * 100).toFixed(2)}%`
}
function dollar(n: number) {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function ratio(n: number) {
  return n.toFixed(3)
}

interface MetricCardProps {
  label: string
  value: string
  sub?: string
  positive?: boolean
  negative?: boolean
}
function MetricCard({ label, value, sub, positive, negative }: MetricCardProps) {
  return (
    <Card size="sm" className="min-w-0">
      <CardHeader>
        <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p
          className={`text-xl font-semibold tabular-nums ${
            positive ? "text-green-500" : negative ? "text-red-500" : ""
          }`}
        >
          {value}
        </p>
        {sub && (
          <p className="text-[10px] text-muted-foreground">{sub}</p>
        )}
      </CardContent>
    </Card>
  )
}

export default function Page() {
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<SimulationRequest>(QUICK_PRESET)

  async function simulate(req: SimulationRequest) {
    setLoading(true)
    setError(null)
    setLastRequest(req)
    try {
      const data = await runSimulation(req)
      setResult(data)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const finalValue =
    result && result.equity_curve.length > 0
      ? result.equity_curve[result.equity_curve.length - 1]
      : null

  return (
    <div className="flex min-h-svh flex-col gap-0">
      {/* Terminal */}
      <header className="flex items-center justify-between border-b bg-card px-6 py-3">
        <div className="flex items-center gap-3">
          <IconChartBar className="size-5 text-primary" />
          <span className="text-sm font-semibold tracking-widest">
            ASV <span className="text-muted-foreground">-</span> APEX STOCK VIEW
          </span>
          <Badge variant="outline" className="text-[10px] uppercase">
            Backtester V1
          </Badge>
        </div>
        <Button
          size="sm"
          className="gap-1.5 text-xs"
          disabled={loading}
          onClick={() => simulate(QUICK_PRESET)}
        >
          <IconBolt className="size-3.5" />
          {loading ? "RUNNING…" : "QUICK SIMULATION"}
        </Button>
      </header>

      <div className="flex flex-1 flex-col gap-6 p-6">
        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            <IconAlertCircle className="mt-0.5 size-4 shrink-0" />
            <pre className="whitespace-pre-wrap text-xs">{error}</pre>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center gap-3 py-16">
            <div className="size-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-xs text-muted-foreground">
              RUNNING BACKTEST — PLEASE WAIT…
            </p>
          </div>
        )}

        {/* Empty / welcome */}
        {!loading && !result && !error && (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 py-16 text-center">
            <div className="flex flex-col items-center gap-2">
              <IconChartBar className="size-10 text-muted-foreground/40" />
              <h2 className="text-sm font-medium">NO SIMULATION DATA</h2>
              <p className="max-w-sm text-xs text-muted-foreground">
                Click{" "}
                <span className="rounded border px-1 text-foreground">
                  QUICK SIMULATION
                </span>{" "}
                to run a pre-configured backtest instantly, or fill in the form
                below to customise your strategy.
              </p>
            </div>
            <Button
              size="lg"
              className="gap-2 text-sm"
              disabled={loading}
              onClick={() => simulate(QUICK_PRESET)}
            >
              <IconBolt className="size-4" />
              QUICK SIMULATION
            </Button>
            <p className="text-[10px] text-muted-foreground">
              PRESET: {QUICK_PRESET.tickers.join(", ")} · {QUICK_PRESET.strategy.toUpperCase()} ·{" "}
              {QUICK_PRESET.start_date} → {QUICK_PRESET.end_date}
            </p>
          </div>
        )}

        {/* Results */}
        {!loading && result && (
          <>
            {/* Simulation context */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>
                {lastRequest.tickers.join(" · ")}
              </span>
              <Separator orientation="vertical" className="h-3" />
              <span>{lastRequest.strategy.toUpperCase()}</span>
              <Separator orientation="vertical" className="h-3" />
              <span>
                LOOKBACK {lastRequest.lookback}D
              </span>
              <Separator orientation="vertical" className="h-3" />
              <span>
                {lastRequest.start_date} → {lastRequest.end_date}
              </span>
              {lastRequest.use_regime && (
                <>
                  <Separator orientation="vertical" className="h-3" />
                  <Badge variant="outline" className="text-[10px]">
                    REGIME FILTER
                  </Badge>
                </>
              )}
            </div>

            {/* Metric cards */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
              <MetricCard
                label="Total Return"
                value={pct(result.total_return)}
                sub={`Final: ${dollar(finalValue!)}`}
                positive={result.total_return >= 0}
                negative={result.total_return < 0}
              />
              <MetricCard
                label="Sharpe Ratio"
                value={result.sharpe.toFixed(3)}
                sub="Annualised (RF=0)"
                positive={result.sharpe >= 1}
                negative={result.sharpe < 0}
              />
              <MetricCard
                label="Max Drawdown"
                value={pct(result.max_drawdown)}
                sub="Peak-to-trough"
                negative={result.max_drawdown < 0}
              />
              <MetricCard
                label="Initial Capital"
                value={dollar(lastRequest.initial_cash)}
                sub={`${result.dates.length} trading days`}
              />
              {typeof result.mean_oos_sharpe === "number" && (
                <MetricCard
                  label="Mean OOS Sharpe"
                  value={ratio(result.mean_oos_sharpe)}
                  sub={`Positive windows: ${result.positive_windows ?? 0}/6`}
                  positive={result.mean_oos_sharpe >= 1}
                />
              )}
              {typeof result.mean_ic === "number" && (
                <MetricCard
                  label="Mean IC"
                  value={result.mean_ic >= 0 ? `+${ratio(result.mean_ic)}` : ratio(result.mean_ic)}
                  sub={
                    typeof result.deflated_sharpe_ratio === "number"
                      ? `Deflated Sharpe: ${ratio(result.deflated_sharpe_ratio)}`
                      : "Cross-sectional rank IC"
                  }
                  positive={result.mean_ic > 0}
                  negative={result.mean_ic < 0}
                />
              )}
            </div>

            {/* Equity curve */}
            <Card>
              <CardHeader className="border-b pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-xs uppercase tracking-widest">
                    {result.total_return >= 0 ? (
                      <IconTrendingUp className="size-4 text-green-500" />
                    ) : (
                      <IconTrendingDown className="size-4 text-red-500" />
                    )}
                    EQUITY CURVE — PORTFOLIO VALUE OVER TIME
                  </CardTitle>
                  <span className="text-[10px] text-muted-foreground">
                    {result.equity_curve.length} bars
                  </span>
                </div>
              </CardHeader>
              <CardContent className="pb-2 pt-4">
                <EquityChart
                  dates={result.dates}
                  equityCurve={result.equity_curve}
                  initialCash={lastRequest.initial_cash}
                />
              </CardContent>
            </Card>
          </>
        )}

        {/* Strategy configuration */}
        {!loading && (
          <Card>
            <CardHeader className="border-b pb-4">
              <CardTitle className="text-xs uppercase tracking-widest">
                STRATEGY CONFIGURATION
              </CardTitle>
            </CardHeader>
            <CardContent>
              <StrategyForm
                defaults={lastRequest}
                loading={loading}
                onSubmit={simulate}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

