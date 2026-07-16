/**
 * POST /api/render-video — start a render job (returns immediately with jobId)
 * GET  /api/render-video/stream?id=<jobId> — SSE status stream
 * GET  /api/render-video?id=<jobId> — download completed video
 */

import { NextRequest, NextResponse } from "next/server";
import path from "path";
import os from "os";
import fs from "fs/promises";
import { readFileSync, existsSync } from "fs";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

// ── In-process job store ────────────────────────────────────────────────

interface PendingJob {
  id: string;
  status: "pending" | "rendering" | "completed" | "error";
  outputPath: string;
  error?: string;
  createdAt: number;
  completedAt?: number;
  dbRecordId?: string | null;
  /** SSE subscriber callbacks — called when status changes. */
  subscribers: Set<(event: string, data: unknown) => void>;
}

const jobs = new Map<string, PendingJob>();
let jobCounter = 0;

function nextJobId(): string {
  jobCounter += 1;
  return `render-${Date.now()}-${jobCounter}`;
}

// ── Background render ───────────────────────────────────────────────────

async function runRender(
  jobId: string,
  body: {
    personName: string;
    messages: string[];
    winningLine: string;
    strategyLabel?: string;
    hookStyle?: string;
    viralScore?: number;
    interactionId?: string | null;
    isOpener?: boolean;
    keyDetail?: string;
  }
): Promise<void> {
  const job = jobs.get(jobId);
  if (!job) return;

  const emit = (event: string, data: unknown) => {
    for (const cb of job.subscribers) cb(event, data);
  };

  try {
    job.status = "rendering";
    emit("status", { status: "rendering" });

    const {
      personName,
      messages,
      winningLine,
      strategyLabel,
      hookStyle,
      viralScore,
      interactionId,
      isOpener,
      keyDetail,
    } = body;
    const msgCount = (messages || []).length;

    const { bundle } = await import("@remotion/bundler");
    const { renderMedia, selectComposition } = await import(
      "@remotion/renderer"
    );

    const compositionDir = path.join(process.cwd(), "src/app/admin/remotion");
    const inputProps = {
      personName,
      messages: messages || [],
      winningLine,
      strategyLabel: strategyLabel || "COOKD_AI",
      voiceoverAudio: "",
      isOpener: !!isOpener,
      keyDetail: keyDetail || "",
    };

    emit("status", { status: "bundling" });
    const serveUrl = await bundle({
      entryPoint: path.join(compositionDir, "index.ts"),
      outDir: path.join(os.tmpdir(), "cookd-remotion-bundles"),
    });

    emit("status", { status: "rendering_video" });
    const compositionId = isOpener ? "CookdProfileCard" : "CookdChatShort";
    const composition = await selectComposition({
      serveUrl,
      id: compositionId,
      inputProps,
    });
    composition.durationInFrames = isOpener
      ? calcProfileCardDuration(winningLine.length)
      : calcDuration(msgCount, winningLine.length);

    const permanentDir = "/rendered-videos";
    await fs.mkdir(permanentDir, { recursive: true });
    const timestamp = Date.now();
    const safeName = personName.toLowerCase().replace(/\s+/g, "-");
    const outputPath = path.join(permanentDir, `${timestamp}-${safeName}.mp4`);
    job.outputPath = outputPath;

    await renderMedia({
      composition,
      serveUrl,
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
      everyNthFrame: 1,
      numberOfGifLoops: null,
      videoBitrate: "8M",
    });

    const stat = await fs.stat(outputPath);
    let dbRecordId: string | null = null;
    try {
      const recordRes = await fetch(
        `${BACKEND_URL}/api/v1/admin/rendered-videos`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Admin-Key": ADMIN_API_KEY || "",
          },
          body: JSON.stringify({
            personName,
            winningLine,
            strategyLabel: strategyLabel || "COOKD_AI",
            hookStyle: hookStyle || "strategy",
            viralScore: viralScore || 0,
            interactionId: interactionId || null,
            filePath: outputPath,
            fileSizeBytes: stat.size,
            status: "completed",
          }),
        }
      );
      if (recordRes.ok) {
        dbRecordId = (await recordRes.json()).id;
      }
    } catch {
      console.warn("[Render] Failed to create DB record");
    }

    job.status = "completed";
    job.completedAt = Date.now();
    job.dbRecordId = dbRecordId;
    emit("completed", {
      downloadUrl: `/api/render-video?id=${jobId}`,
      dbRecordId,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    console.error("[Render Error]", message);
    job.status = "error";
    job.error = message;
    job.completedAt = Date.now();
    emit("error", { message });
  } finally {
    job.subscribers.clear();
  }
}

function calcDuration(messages: number, winningLineLen: number): number {
  return 65 + messages * 28 + 18 + winningLineLen * 2 + 75 + 120;
}
function calcProfileCardDuration(winningLineLen: number): number {
  return 120 + winningLineLen * 2 + 20 + 60 + 90;
}

// ── Routes ──────────────────────────────────────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { personName, winningLine } = body;
    if (!winningLine || !personName) {
      return NextResponse.json(
        { error: "Missing required fields: personName, winningLine" },
        { status: 400 }
      );
    }

    // Clean stale jobs
    const staleCutoff = Date.now() - 3_600_000;
    for (const [id, j] of jobs) {
      if (j.completedAt && j.completedAt < staleCutoff) jobs.delete(id);
    }

    const jobId = nextJobId();
    jobs.set(jobId, {
      id: jobId,
      status: "pending",
      outputPath: "",
      createdAt: Date.now(),
      subscribers: new Set(),
    });

    runRender(jobId, body).catch((err) =>
      console.error("[Render] background crash:", err)
    );

    return NextResponse.json({ jobId, status: "pending" });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  // ── SSE stream (use ?stream instead of sub-path for Next.js App Router) ─
  if (searchParams.has("stream")) {
    const jobId = searchParams.get("id");
    if (!jobId) {
      return NextResponse.json(
        { error: "Missing ?id= param" },
        { status: 400 }
      );
    }
    const job = jobs.get(jobId);
    if (!job) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    // Already done — return immediately as JSON
    if (job.status === "completed") {
      return NextResponse.json({
        event: "completed",
        downloadUrl: `/api/render-video?id=${jobId}`,
        dbRecordId: job.dbRecordId,
      });
    }
    if (job.status === "error") {
      return NextResponse.json({ event: "error", message: job.error });
    }

    // Subscribe to live updates
    const encoder = new TextEncoder();
    let closed = false;
    const stream = new ReadableStream({
      start(controller) {
        const send = (event: string, data: unknown) => {
          if (closed) return;
          controller.enqueue(
            encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
          );
          if (event === "completed" || event === "error") {
            closed = true;
            controller.close();
          }
        };

        send("status", { status: job.status });
        job.subscribers.add(send);

        const timeout = setTimeout(() => {
          job.subscribers.delete(send);
          send("error", { message: "Render timed out" });
        }, 300_000);

        const cleanup = () => {
          clearTimeout(timeout);
          job.subscribers.delete(send);
        };
        // Store cleanup on controller so cancel() can call it
        (controller as unknown as { _cleanup: () => void })._cleanup = cleanup;
      },
      cancel() {
        (this as unknown as { _cleanup?: () => void })._cleanup?.();
      },
    });

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  // ── Download completed video ────────────────────────────────────────────
  const jobId = searchParams.get("id");
  if (!jobId) {
    return NextResponse.json({ error: "Missing ?id= param" }, { status: 400 });
  }
  const job = jobs.get(jobId);
  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }
  if (
    job.status !== "completed" ||
    !job.outputPath ||
    !existsSync(job.outputPath)
  ) {
    return NextResponse.json({
      status: job.status,
      error: job.status === "error" ? job.error : undefined,
    });
  }

  const fileBuffer = readFileSync(job.outputPath);
  const safeName = path.basename(job.outputPath).replace(/\.mp4$/, "");
  jobs.delete(jobId);

  return new NextResponse(fileBuffer, {
    headers: {
      "Content-Type": "video/mp4",
      "Content-Disposition": `attachment; filename="cookd-${safeName}.mp4"`,
      "Content-Length": fileBuffer.length.toString(),
      "X-Video-Id": job.dbRecordId || "",
    },
  });
}
