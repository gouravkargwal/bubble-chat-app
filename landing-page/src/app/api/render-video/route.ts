/**
 * POST /api/render-video — start a render job (returns immediately with jobId)
 * GET  /api/render-video?id=<jobId> — poll for job status / download finished video
 *
 * Render runs in a background asyncio task so the HTTP request doesn't block
 * for 30-90s. The client polls GET until status="completed" or "error".
 *
 * Dependencies:
 *   npm install @remotion/bundler @remotion/renderer remotion
 *
 * Chrome must be available on the server for Remotion to render.
 * Install: npx puppeteer browsers install chrome
 */

import { NextRequest, NextResponse } from "next/server";
import path from "path";
import os from "os";
import fs from "fs/promises";
import { readFileSync, existsSync } from "fs";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

// ── In-process job store ────────────────────────────────────────────────
// Shared across all requests within the same process. On serverless or
// multi-process deployments this would need Redis — fine for a single
// Node.js process behind a proxy.

interface RenderJob {
  id: string;
  status: "pending" | "rendering" | "completed" | "error";
  outputPath: string;
  error?: string;
  createdAt: number;
  completedAt?: number;
  dbRecordId?: string | null;
}

const jobs = new Map<string, RenderJob>();

let jobCounter = 0;
function nextJobId(): string {
  jobCounter += 1;
  return `render-${Date.now()}-${jobCounter}`;
}

// ── Background runner ────────────────────────────────────────────────────

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

  try {
    job.status = "rendering";

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

    // Import Remotion modules dynamically (they're heavy)
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

    // Step 1: bundle
    const serveUrl = await bundle({
      entryPoint: path.join(compositionDir, "index.ts"),
      outDir: path.join(os.tmpdir(), "cookd-remotion-bundles"),
    });

    // Step 2: select composition
    const compositionId = isOpener ? "CookdProfileCard" : "CookdChatShort";
    const composition = await selectComposition({
      serveUrl,
      id: compositionId,
      inputProps,
    });
    composition.durationInFrames = isOpener
      ? calcProfileCardDuration(winningLine.length)
      : calcDuration(msgCount, winningLine.length);

    // Step 3: output path
    const permanentDir = "/rendered-videos";
    await fs.mkdir(permanentDir, { recursive: true });
    const timestamp = Date.now();
    const safeName = personName.toLowerCase().replace(/\s+/g, "-");
    const outputPath = path.join(permanentDir, `${timestamp}-${safeName}.mp4`);

    // Update job with the real output path
    job.outputPath = outputPath;

    // Step 4: render
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

    // Step 5: DB record
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
        const record = await recordRes.json();
        dbRecordId = record.id;
      }
    } catch {
      console.warn("[Render] Failed to create DB record");
    }

    job.status = "completed";
    job.completedAt = Date.now();
    job.dbRecordId = dbRecordId;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    console.error("[Render Error]", message);
    job.status = "error";
    job.error = message;
    job.completedAt = Date.now();
  }
}

// ── Duration helpers (lock-step with Composition.tsx) ────────────────────

function calcDuration(messages: number, winningLineLen: number): number {
  const chatStartFrame = 65;
  const analyzeStartFrame = chatStartFrame + messages * 28;
  const revealStartFrame = analyzeStartFrame + 18;
  const typingDuration = winningLineLen * 2;
  const outroStartFrame = revealStartFrame + typingDuration + 75;
  return outroStartFrame + 120;
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

    // Clean up stale jobs older than 1 hour
    const staleCutoff = Date.now() - 3_600_000;
    for (const [id, j] of jobs) {
      if (j.completedAt && j.completedAt < staleCutoff) jobs.delete(id);
    }

    const jobId = nextJobId();
    const job: RenderJob = {
      id: jobId,
      status: "pending",
      outputPath: "",
      createdAt: Date.now(),
    };
    jobs.set(jobId, job);

    // Fire & forget — runs in background
    runRender(jobId, body).catch((err) =>
      console.error("[Render] background task crashed:", err)
    );

    return NextResponse.json({ jobId, status: "pending" });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    console.error("[Render POST Error]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get("id");
  if (!jobId) {
    return NextResponse.json(
      { error: "Missing ?id= parameter" },
      { status: 400 }
    );
  }

  const job = jobs.get(jobId);
  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  // If completed and the file exists, stream it as a download
  if (
    job.status === "completed" &&
    job.outputPath &&
    existsSync(job.outputPath)
  ) {
    const fileBuffer = readFileSync(job.outputPath);
    const safeName = path.basename(job.outputPath).replace(/\.mp4$/, "");
    const fileName = `cookd-${safeName}.mp4`;

    // Clean up the job from the map — no more polling needed
    jobs.delete(jobId);

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": `attachment; filename="${fileName}"`,
        "Content-Length": fileBuffer.length.toString(),
        "X-Video-Id": job.dbRecordId || "",
      },
    });
  }

  // Otherwise return status
  return NextResponse.json({
    jobId: job.id,
    status: job.status,
    error: job.error,
    createdAt: job.createdAt,
    completedAt: job.completedAt,
    ...(job.status === "completed"
      ? { downloadUrl: `/api/render-video?id=${jobId}` }
      : {}),
  });
}
