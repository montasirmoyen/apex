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
