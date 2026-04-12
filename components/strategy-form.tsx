"use client"

import { useEffect, useState } from "react"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Calendar } from "@/components/ui/calendar"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import type { SimulationRequest } from "@/types/simulation"

interface StrategyFormProps {
  defaults: SimulationRequest
  loading: boolean
  onSubmit: (req: SimulationRequest) => void
}

function formatDisplayDate(date: Date | undefined) {
  if (!date) return ""
  return date.toLocaleDateString("en-US", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function toIsoDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function fromIsoDate(value: string) {
  if (!value) return undefined
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) return undefined

  const parsed = new Date(year, month - 1, day)
  return Number.isNaN(parsed.getTime()) ? undefined : parsed
}

function isValidDate(date: Date | undefined) {
  if (!date) return false
  return !Number.isNaN(date.getTime())
}

interface DatePickerFieldProps {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
}

function DatePickerField({ id, label, value, onChange }: DatePickerFieldProps) {
  const [open, setOpen] = useState(false)
  const selectedDate = fromIsoDate(value)
  const [month, setMonth] = useState<Date | undefined>(selectedDate)
  const [displayValue, setDisplayValue] = useState(formatDisplayDate(selectedDate))

  useEffect(() => {
    const nextDate = fromIsoDate(value)
    setDisplayValue(formatDisplayDate(nextDate))
    setMonth(nextDate)
  }, [value])

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <InputGroup>
        <InputGroupInput
          id={id}
          value={displayValue}
          placeholder="June 01, 2025"
          onChange={(e) => {
            const nextValue = e.target.value
            const parsedDate = new Date(nextValue)

            setDisplayValue(nextValue)

            if (isValidDate(parsedDate)) {
              onChange(toIsoDate(parsedDate))
              setMonth(parsedDate)
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault()
              setOpen(true)
            }
          }}
        />
        <InputGroupAddon align="inline-end">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <InputGroupButton
                variant="ghost"
                size="icon-xs"
                aria-label={`Select ${label.toLowerCase()}`}
              >
                <CalendarIcon />
                <span className="sr-only">Select {label.toLowerCase()}</span>
              </InputGroupButton>
            </PopoverTrigger>
            <PopoverContent
              className="w-auto overflow-hidden p-0"
              align="end"
              alignOffset={-8}
              sideOffset={10}
            >
              <Calendar
                mode="single"
                selected={selectedDate}
                month={month}
                onMonthChange={setMonth}
                onSelect={(nextDate) => {
                  if (nextDate) {
                    onChange(toIsoDate(nextDate))
                    setDisplayValue(formatDisplayDate(nextDate))
                    setMonth(nextDate)
                  }
                  setOpen(false)
                }}
              />
            </PopoverContent>
          </Popover>
        </InputGroupAddon>
      </InputGroup>
    </div>
  )
}

export function StrategyForm({ defaults, loading, onSubmit }: StrategyFormProps) {
  const [tickers, setTickers] = useState(defaults.tickers.join(", "))
  const [strategy, setStrategy] = useState<SimulationRequest["strategy"]>(
    defaults.strategy,
  )
  const [lookback, setLookback] = useState(String(defaults.lookback))
  const [initialCash, setInitialCash] = useState(String(defaults.initial_cash))
  const [startDate, setStartDate] = useState(defaults.start_date)
  const [endDate, setEndDate] = useState(defaults.end_date)
  const [useRegime, setUseRegime] = useState(defaults.use_regime)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const parsed = tickers
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean)
    if (parsed.length === 0) return
    onSubmit({
      tickers: parsed,
      strategy,
      lookback: Math.max(1, parseInt(lookback) || defaults.lookback),
      initial_cash: Math.max(1, parseFloat(initialCash) || defaults.initial_cash),
      start_date: startDate,
      end_date: endDate,
      use_regime: useRegime,
    })
  }

  const field = "flex flex-col gap-1.5"

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className={field}>
        <Label>TICKERS (comma-separated)</Label>
        <Input
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
          placeholder="AAPL, MSFT, GOOGL"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className={field}>
          <Label>STRATEGY</Label>
          <Select
            value={strategy}
            onValueChange={(v) => setStrategy(v as SimulationRequest["strategy"])}
          >
            <SelectTrigger className={`w-full`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="momentum">Momentum</SelectItem>
              <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
              <SelectItem value="ml_ensemble">ML Ensemble Long/Short</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className={field}>
          <Label>LOOKBACK (days)</Label>
          <Input
            type="number"
            min={1}
            value={lookback}
            onChange={(e) => setLookback(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <DatePickerField
          id="start-date"
          label="START DATE"
          value={startDate}
          onChange={setStartDate}
        />
        <DatePickerField
          id="end-date"
          label="END DATE"
          value={endDate}
          onChange={setEndDate}
        />
      </div>

      <div className={field}>
        <Label>INITIAL CAPITAL ($)</Label>
        <Input
          type="number"
          min={1}
          value={initialCash}
          onChange={(e) => setInitialCash(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-2">
        <Switch checked={useRegime} onCheckedChange={setUseRegime} id="regime" />
        <Label htmlFor="regime" className={`cursor-pointer`}>
          REGIME FILTER (200-day MA)
        </Label>
      </div>

      <Button type="submit" disabled={loading} className={`w-full `}>
        {loading ? "RUNNING..." : "▶  RUN SIMULATION"}
      </Button>
    </form>
  )
}
