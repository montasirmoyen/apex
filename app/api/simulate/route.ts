import { spawn } from "child_process"
import path from "path"
import { NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const scriptPath = path.join(process.cwd(), "backend", "quick_sim.py")

  return new Promise<NextResponse>((resolve) => {
    const python = spawn("python3", [scriptPath], { cwd: process.cwd() })

    let stdout = ""
    let stderr = ""

    python.stdin.write(JSON.stringify(body))
    python.stdin.end()

    python.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString()
    })
    python.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString()
    })

    python.on("close", (code) => {
      if (code !== 0) {
        const message = stderr.trim() || "Python process exited with code " + code
        resolve(NextResponse.json({ error: message }, { status: 500 }))
        return
      }
      try {
        const result = JSON.parse(stdout)
        if (result.error) {
          resolve(NextResponse.json({ error: result.error }, { status: 500 }))
        } else {
          resolve(NextResponse.json(result))
        }
      } catch {
        resolve(
          NextResponse.json({ error: "Could not parse Python output" }, { status: 500 }),
        )
      }
    })

    python.on("error", (err) => {
      resolve(
        NextResponse.json(
          { error: "Failed to start Python: " + err.message },
          { status: 500 },
        ),
      )
    })
  })
}
