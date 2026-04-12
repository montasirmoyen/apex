"use client"

import { useEffect, useMemo, useState } from "react"
import { Search } from "lucide-react"
import {
	Area,
	AreaChart,
	CartesianGrid,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"

interface StockSearchResult {
	symbol: string
	name: string
	exchange: string
	type: string
}

interface StockPoint {
	ts: string
	price: number
}

interface LiveStockPayload {
	ticker: string
	currency: string
	live_price: number | null
	last_close: number | null
	previous_close: number | null
	points: StockPoint[]
	updated_at: string
}

const REFRESH_MS = 30_000

function formatMoney(value: number | null, currency = "USD") {
	if (value == null || Number.isNaN(value)) return "N/A"
	return new Intl.NumberFormat("en-US", {
		style: "currency",
		currency,
		maximumFractionDigits: 2,
	}).format(value)
}

function formatAxisTime(ts: string) {
	const date = new Date(ts)
	if (Number.isNaN(date.getTime())) return ts
	return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
}

export default function LibraryPage() {
	const [query, setQuery] = useState("")
	const [results, setResults] = useState<StockSearchResult[]>([])
	const [selectedTicker, setSelectedTicker] = useState("AAPL")
	const [liveData, setLiveData] = useState<LiveStockPayload | null>(null)
	const [searchLoading, setSearchLoading] = useState(false)
	const [chartLoading, setChartLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		const term = query.trim()
		if (!term) {
			setResults([])
			return
		}

		const timer = setTimeout(async () => {
			setSearchLoading(true)
			try {
				const response = await fetch(`/api/stocks/search?q=${encodeURIComponent(term)}&limit=8`)
				const data = (await response.json()) as { results?: StockSearchResult[]; error?: string }
				if (!response.ok) {
					throw new Error(data.error ?? "Failed to search stocks")
				}
				setResults(Array.isArray(data.results) ? data.results : [])
			} catch (err) {
				setError(err instanceof Error ? err.message : "Failed to search stocks")
			} finally {
				setSearchLoading(false)
			}
		}, 350)

		return () => clearTimeout(timer)
	}, [query])

	useEffect(() => {
		let cancelled = false

		async function fetchLive() {
			if (!selectedTicker) return
			setChartLoading(true)
			setError(null)

			try {
				const response = await fetch(
					`/api/stocks/live?ticker=${encodeURIComponent(selectedTicker)}&period=1d&interval=5m`,
				)
				const data = (await response.json()) as LiveStockPayload & { error?: string }
				if (!response.ok) {
					throw new Error(data.error ?? "Failed to fetch live stock data")
				}

				if (!cancelled) {
					setLiveData(data)
				}
			} catch (err) {
				if (!cancelled) {
					setError(err instanceof Error ? err.message : "Failed to fetch live stock data")
				}
			} finally {
				if (!cancelled) {
					setChartLoading(false)
				}
			}
		}

		void fetchLive()
		const intervalId = setInterval(() => {
			void fetchLive()
		}, REFRESH_MS)

		return () => {
			cancelled = true
			clearInterval(intervalId)
		}
	}, [selectedTicker])

	const chartData = useMemo(() => {
		if (!liveData?.points) return []
		return liveData.points.map((point) => ({
			time: formatAxisTime(point.ts),
			rawTime: point.ts,
			price: point.price,
		}))
	}, [liveData])

	const delta =
		liveData?.live_price != null && liveData?.previous_close != null
			? liveData.live_price - liveData.previous_close
			: null
	const deltaPct =
		delta != null && liveData?.previous_close
			? (delta / liveData.previous_close) * 100
			: null

	return (
		<main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 md:px-6">
			<section className="space-y-3">
				<h1 className="text-2xl font-semibold tracking-tight">Live Market Library</h1>
				<p className="text-sm text-muted-foreground">
					Search stocks, view live prices from Yahoo Finance, and auto-refresh charts every 30 seconds.
				</p>
			</section>

			<section className="grid gap-6 lg:grid-cols-[340px_1fr]">
				<Card>
					<CardHeader>
						<CardTitle className="text-base">Stock Search</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="w-full max-w-sm space-y-2">
							<Label htmlFor="search-input">Search</Label>
							<div className="relative">
								<Search className="-translate-y-1/2 absolute top-1/2 left-3 h-4 w-4 text-muted-foreground" />
								<Input
									className="bg-background pl-9"
									id="search-input"
									placeholder="Search symbol or company..."
									type="search"
									value={query}
									onChange={(e) => setQuery(e.target.value)}
								/>
							</div>
						</div>

						{searchLoading && <p className="text-xs text-muted-foreground">Searching...</p>}

						<div className="space-y-2">
							{results.map((item) => (
								<button
									key={`${item.symbol}-${item.exchange}`}
									type="button"
									onClick={() => {
										setSelectedTicker(item.symbol)
										setQuery(item.symbol)
										setResults([])
									}}
									className="flex w-full items-start justify-between rounded-md border px-3 py-2 text-left transition-colors hover:bg-muted"
								>
									<div className="min-w-0">
										<p className="text-sm font-medium">{item.symbol}</p>
										<p className="truncate text-xs text-muted-foreground">{item.name}</p>
									</div>
									<div className="ml-3 flex shrink-0 gap-1">
										{item.exchange && <Badge variant="outline">{item.exchange}</Badge>}
										{item.type && <Badge variant="secondary">{item.type}</Badge>}
									</div>
								</button>
							))}
						</div>

						{!searchLoading && query.trim().length > 0 && results.length === 0 && (
							<p className="text-xs text-muted-foreground">No matching symbols found.</p>
						)}
					</CardContent>
				</Card>

				<Card>
					<CardHeader className="space-y-3">
						<div className="flex flex-wrap items-center justify-between gap-3">
							<div>
								<CardTitle className="text-xl">{selectedTicker}</CardTitle>
								<p className="text-xs text-muted-foreground">
									Refresh interval: 30s | Last update:{" "}
									{liveData?.updated_at
										? new Date(liveData.updated_at).toLocaleTimeString("en-US")
										: "-"}
								</p>
							</div>

							<div className="text-right">
								<p className="text-2xl font-semibold tabular-nums">
									{formatMoney(liveData?.live_price ?? liveData?.last_close ?? null, liveData?.currency ?? "USD")}
								</p>
								<p
									className={`text-sm tabular-nums ${
										delta == null ? "text-muted-foreground" : delta >= 0 ? "text-green-600" : "text-red-600"
									}`}
								>
									{delta == null || deltaPct == null
										? "-"
										: `${delta >= 0 ? "+" : ""}${formatMoney(delta, liveData?.currency ?? "USD")} (${deltaPct.toFixed(2)}%)`}
								</p>
							</div>
						</div>
						<Separator />
					</CardHeader>

					<CardContent>
						{chartLoading && chartData.length === 0 ? (
							<div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
								Loading live chart...
							</div>
						) : chartData.length === 0 ? (
							<div className="flex h-80 items-center justify-center text-sm text-muted-foreground">
								No chart data available for this ticker.
							</div>
						) : (
							<ResponsiveContainer width="100%" height={320}>
								<AreaChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
									<defs>
										<linearGradient id="liveStockGrad" x1="0" y1="0" x2="0" y2="1">
											<stop offset="0%" stopColor="#22c55e" stopOpacity={0.25} />
											<stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
										</linearGradient>
									</defs>
									<CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
									<XAxis dataKey="time" tickLine={false} axisLine={false} minTickGap={36} />
									<YAxis
										tickLine={false}
										axisLine={false}
										width={72}
										tickFormatter={(v) => formatMoney(v, liveData?.currency ?? "USD")}
									/>
									<Tooltip
										formatter={(value) => [formatMoney(Number(value), liveData?.currency ?? "USD"), "Price"]}
										labelFormatter={(_, payload) => {
											const item = payload?.[0]?.payload as { rawTime?: string } | undefined
											if (!item?.rawTime) return ""
											return new Date(item.rawTime).toLocaleString("en-US")
										}}
										contentStyle={{
											background: "hsl(var(--card))",
											border: "1px solid hsl(var(--border))",
											borderRadius: 8,
										}}
									/>
									<Area
										type="monotone"
										dataKey="price"
										stroke="#22c55e"
										strokeWidth={2}
										fill="url(#liveStockGrad)"
										dot={false}
										isAnimationActive={false}
									/>
								</AreaChart>
							</ResponsiveContainer>
						)}

						{chartLoading && chartData.length > 0 && (
							<p className="mt-3 text-xs text-muted-foreground">Refreshing live price data...</p>
						)}
					</CardContent>
				</Card>
			</section>

			{error && (
				<Card className="border-destructive/40">
					<CardContent className="pt-4">
						<p className="text-sm text-destructive">{error}</p>
					</CardContent>
				</Card>
			)}
		</main>
	)
}
