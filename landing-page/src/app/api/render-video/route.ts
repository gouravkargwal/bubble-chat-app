/**
 * POST /api/render-video
 *
 * Renders a Remotion chat-short video directly.
 * Uses @remotion/bundler to bundle the composition .tsx files on-the-fly,
 * then @remotion/renderer to render the .mp4.
 *
 * The rendered file is saved permanently to ./rendered-videos/ and
 * a DB record is created via the backend CRUD API.
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
import { readFileSync } from "fs";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

// Matches the timing math in Composition.tsx (30 FPS). Keep these constants
// in lock-step with the composition or the video will clip / pad dead frames.
function calcDuration(messages: number, winningLineLen: number): number {
  const chatStartFrame = 65;
  const analyzeStartFrame = chatStartFrame + messages * 28; // MSG_PACE
  const revealStartFrame = analyzeStartFrame + 18; // ANALYZE_FRAMES
  const typingDuration = winningLineLen * 2; // typingSpeed
  const outroStartFrame = revealStartFrame + typingDuration + 75;
  return outroStartFrame + 120; // ~4s outro hold
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      personName,
      messages,
      winningLine,
      strategyLabel,
      hookStyle,
      viralScore,
      interactionId,
    } = body;

    if (!winningLine || !personName) {
      return NextResponse.json(
        { error: "Missing required fields: personName, winningLine" },
        { status: 400 }
      );
    }

    const msgCount = (messages || []).length;

    // Import Remotion modules dynamically
    const { bundle } = await import("@remotion/bundler");
    const { renderMedia, selectComposition } = await import(
      "@remotion/renderer"
    );

    // Path to the Remotion composition source files
    const compositionDir = path.join(process.cwd(), "src/app/admin/remotion");

    const inputProps = {
      personName,
      messages: messages || [],
      winningLine,
      strategyLabel: strategyLabel || "COOKD_AI",
      voiceoverAudio: "",
    };

    // ── Step 1: Bundle the composition .tsx files into a static site ──
    const serveUrl = await bundle({
      entryPoint: path.join(compositionDir, "index.ts"),
      outDir: path.join(os.tmpdir(), "cookd-remotion-bundles"),
    });

    // ── Step 2: Select the composition by ID, overriding duration ──
    const composition = await selectComposition({
      serveUrl,
      id: "CookdChatShort",
      inputProps,
    });
    composition.durationInFrames = calcDuration(msgCount, winningLine.length);

    // ── Step 3: Define permanent output path (shared Docker volume) ──
    // Both landing-page and api containers mount rendered_videos_data at /rendered-videos
    const permanentDir = "/rendered-videos";
    await fs.mkdir(permanentDir, { recursive: true });
    const timestamp = Date.now();
    const safeName = personName.toLowerCase().replace(/\s+/g, "-");
    const outputPath = path.join(permanentDir, `${timestamp}-${safeName}.mp4`);

    // ── Step 4: Render the video ──
    await renderMedia({
      composition,
      serveUrl,
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
      everyNthFrame: 1,
      numberOfGifLoops: null,
      // 8 Mbps bitrate for crisp text rendering on social platforms
      // Remotion default (~2 Mbps) causes blocky text on sharp font edges
      videoBitrate: "8M",
    });

    // ── Step 5: Get file stats ──
    const stat = await fs.stat(outputPath);

    // ── Step 6: Create DB record via backend CRUD API ──
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
    } catch (dbErr) {
      // Non-fatal: video is saved on disk even if DB record fails
      console.warn("[Render] Failed to create DB record:", dbErr);
    }

    // ── Step 7: Stream the file back as download ──
    const fileBuffer = readFileSync(outputPath);
    const fileName = `cookd-${safeName}.mp4`;

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": `attachment; filename="${fileName}"`,
        "Content-Length": fileBuffer.length.toString(),
        "X-Video-Id": dbRecordId || "",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    console.error("[Render Error]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
