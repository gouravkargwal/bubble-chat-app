/**
 * Public video streaming endpoint — serves rendered videos for in-browser preview.
 *
 * This bypasses the Clerk-authenticated BFF proxy because the <video> tag
 * needs direct, streamable access to the file. Security is maintained via:
 *   1. The admin API key (server-side only, never exposed to client)
 *   2. The admin page itself is still protected by middleware.ts
 *
 * Usage: <video src="/api/stream-video/{videoId}" controls />
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  if (!ADMIN_API_KEY) {
    return NextResponse.json(
      { error: "Admin API key not configured" },
      { status: 503 }
    );
  }

  const url = `${BACKEND_URL}/api/v1/admin/rendered-videos/${id}/download`;

  try {
    const backendRes = await fetch(url, {
      headers: { "X-Admin-Key": ADMIN_API_KEY },
    });

    if (!backendRes.ok) {
      const text = await backendRes.text().catch(() => "Backend error");
      return NextResponse.json({ error: text }, { status: backendRes.status });
    }

    // Stream the video response directly to the browser
    const contentType = backendRes.headers.get("content-type") || "video/mp4";

    return new NextResponse(backendRes.body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": "inline",
        "Accept-Ranges": "bytes",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unreachable";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
