import { spawn } from "child_process"
import fs from "fs"
import path from "path"
import { NextRequest, NextResponse } from "next/server"

function runPython(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), "backend", "live_market.py")
    const venvPythonPath = path.join(process.cwd(), "backend", ".venv", "bin", "python")
    const pythonExecutable = fs.existsSync(venvPythonPath) ? venvPythonPath : "python3"

    const proc = spawn(pythonExecutable, [scriptPath], { cwd: process.cwd() })

    let stdout = ""
    let stderr = ""

    proc.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString()
    })

    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString()
    })

    proc.on("error", (err) => reject(err))

    proc.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr.trim() || `Python process exited with code ${code}`))
        return
      }

      try {
        resolve(JSON.parse(stdout))
      } catch {
        reject(new Error("Invalid JSON returned by Python helper"))
      }
    })

    proc.stdin.write(JSON.stringify(payload))
    proc.stdin.end()
  })
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const q = request.nextUrl.searchParams.get("q")?.trim() ?? ""
  const limitParam = request.nextUrl.searchParams.get("limit")
  const limit = Number.parseInt(limitParam ?? "8", 10)

  if (!q) {
    return NextResponse.json({ results: [] })
  }

  try {
    const response = await runPython({ mode: "search", query: q, limit })
    const ok = response.ok === true
    if (!ok) {
      return NextResponse.json(
        { error: String(response.error ?? "Failed to search stocks") },
        { status: 400 },
      )
    }

    return NextResponse.json((response.data as Record<string, unknown>) ?? { results: [] }, {
      headers: { "Cache-Control": "no-store" },
    })
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to search stocks" },
      { status: 500 },
    )
  }
}
