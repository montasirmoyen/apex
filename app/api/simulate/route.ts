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
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      const python = spawn("python3", [scriptPath], { cwd: process.cwd() })

      python.stdin.write(JSON.stringify(body))
      python.stdin.end()

      let buffer = ""
      let stderrBuf = ""

      python.stdout.on("data", (chunk: Buffer) => {
        buffer += chunk.toString()
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""
        for (const line of lines) {
          if (line.trim()) {
            controller.enqueue(encoder.encode(line + "\n"))
          }
        }
      })

      python.stderr.on("data", (chunk: Buffer) => {
        stderrBuf += chunk.toString()
      })

      python.on("close", (code) => {
        // flush any remaining buffered output
        if (buffer.trim()) {
          controller.enqueue(encoder.encode(buffer + "\n"))
        }
        if (code !== 0) {
          const msg = stderrBuf.trim() || `Python process exited with code ${code}`
          controller.enqueue(
            encoder.encode(JSON.stringify({ type: "error", message: msg }) + "\n"),
          )
        }
        controller.close()
      })

      python.on("error", (err) => {
        controller.enqueue(
          encoder.encode(
            JSON.stringify({ type: "error", message: "Failed to start Python: " + err.message }) +
              "\n",
          ),
        )
        controller.close()
      })
    },
  })

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  })
}
