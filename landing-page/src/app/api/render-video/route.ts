/**
 * POST /api/render-video
 *
 * Renders a Remotion chat-short video directly.
 * Uses @remotion/bundler to bundle the composition .tsx files on-the-fly,
 * then @remotion/renderer to render the .mp4.
 *
 * The output is streamed back as a download.
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

// Matches the timing math in Composition.tsx (30 FPS)
function calcDuration(messages: number, winningLineLen: number): number {
  const analyzeStartFrame = 30 + messages * 45; // 1.5s per message
  const revealStartFrame = analyzeStartFrame + 60; // 2s analyzing
  const typingDuration = winningLineLen * 3; // 3 frames per char
  const outroStartFrame = revealStartFrame + typingDuration + 90; // 3s pause
  return outroStartFrame + 120; // 4s outro splash
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { personName, messages, winningLine, strategyLabel } = body;

    if (!winningLine || !personName) {
      return NextResponse.json(
        { error: "Missing required fields: personName, winningLine" },
        { status: 400 }
      );
    }

    const msgCount = (messages || []).length;

    // Import Remotion modules dynamically (heavy — avoid loading on every warm start)
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
      // Output to a temp dir so we don't pollute the source tree
      outDir: path.join(os.tmpdir(), "cookd-remotion-bundles"),
    });

    // ── Step 2: Select the composition by ID, overriding duration ──
    // Root.tsx has a static durationInFrames based on samplePreviewProps.
    // We override it here with the real calculated value for the actual data.
    const composition = await selectComposition({
      serveUrl,
      id: "CookdChatShort",
      inputProps,
    });
    composition.durationInFrames = calcDuration(msgCount, winningLine.length);

    // ── Step 3: Render the video ──
    const outputDir = path.join(os.tmpdir(), "cookd-videos");
    await fs.mkdir(outputDir, { recursive: true });
    const outputPath = path.join(outputDir, `${Date.now()}.mp4`);

    await renderMedia({
      composition,
      serveUrl,
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
      everyNthFrame: 1,
      numberOfGifLoops: null,
    });

    // ── Step 4: Stream the file back ──
    const fileBuffer = readFileSync(outputPath);
    const fileName = `cookd-${personName
      .toLowerCase()
      .replace(/\s+/g, "-")}.mp4`;

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": `attachment; filename="${fileName}"`,
        "Content-Length": fileBuffer.length.toString(),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Render failed";
    console.error("[Render Error]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
