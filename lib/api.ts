import type { SimulationRequest, SimulationResult } from "@/types/simulation"

export async function runSimulation(
  request: SimulationRequest,
): Promise<SimulationResult> {
  const res = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error((data as { error?: string }).error ?? "Simulation failed")
  }

  return data as SimulationResult
}


// run a simulation and stream progress logs to the caller
// calls `onLog` for each progress message and resolves with the final result
export async function runSimulationStream(
  request: SimulationRequest & { speed_up?: boolean },
  onLog: (message: string) => void,
): Promise<SimulationResult> {
  const res = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.body) {
    throw new Error("No response body — streaming not supported")
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() ?? ""

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(trimmed)
      } catch {
        continue
      }
      if (parsed.type === "log") {
        onLog(parsed.message as string)
      } else if (parsed.type === "result") {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { type, ...result } = parsed
        return result as unknown as SimulationResult
      } else if (parsed.type === "error") {
        throw new Error(parsed.message as string)
      }
    }
  }

  // handle any trailing content
  if (buffer.trim()) {
    try {
      const parsed = JSON.parse(buffer.trim()) as Record<string, unknown>
      if (parsed.type === "result") {
        const { type, ...result } = parsed
        return result as unknown as SimulationResult
      }
      if (parsed.type === "error") throw new Error(parsed.message as string)
    } catch {
      // not JSON, ignore
    }
  }

  throw new Error("Stream ended without a result")
}
