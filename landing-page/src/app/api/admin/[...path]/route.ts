/**
 * BFF proxy — /api/admin/* → backend /api/v1/admin/*
 *
 * Two layers of auth:
 *   1. Clerk session required (browser → Next.js)
 *   2. Admin API key header (Next.js → backend)
 *
 * This keeps admin endpoints unreachable from the public internet
 * even if someone discovers the backend URL.
 *
 * Handles:
 *   - JSON API responses (default)
 *   - Binary file downloads (when path ends in /download)
 */

import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

async function proxy(req: NextRequest, method: string) {
  // ── Layer 1: Clerk session ──
  try {
    const session = await auth();
    if (!session.userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  } catch (authErr) {
    console.error("[BFF] Clerk auth error:", authErr);
    return NextResponse.json(
      { error: "Authentication service error" },
      { status: 500 }
    );
  }

  // ── Layer 2: Admin API key must be configured ──
  if (!ADMIN_API_KEY) {
    console.error("[BFF] Missing ADMIN_API_KEY environment variable");
    return NextResponse.json(
      { error: "Admin API key not configured on server." },
      { status: 503 }
    );
  }

  // ── Build backend URL ──
  const pathname = req.nextUrl.pathname.replace("/api/admin", "/api/v1/admin");
  const search = req.nextUrl.search;
  const isDownload =
    req.nextUrl.pathname.includes("/download") ||
    (req.nextUrl.pathname.includes("/rendered-videos/") &&
      method === "GET" &&
      !search); // list endpoint has search
  const url = `${BACKEND_URL}${pathname}${search}`;

  // ── Forward request ──
  const headers = new Headers(req.headers);
  headers.set("X-Admin-Key", ADMIN_API_KEY);
  // Drop host header — let fetch set the right one
  headers.delete("host");

  // Stream body for POST/PUT
  const body = method === "GET" || method === "HEAD" ? undefined : req.body;

  try {
    const backendRes = await fetch(url, {
      method,
      headers,
      body,
      // ponytail: duplex required by Node 18+ fetch when sending a body
      ...(body ? { duplex: "half" } : {}),
      redirect: "manual",
    });

    // ── Binary response (file download) — pass through raw ──
    if (
      isDownload ||
      backendRes.headers.get("content-type")?.startsWith("video/") ||
      backendRes.headers.get("content-type") === "application/octet-stream"
    ) {
      // For download endpoints, return the raw blob
      const blob = await backendRes.blob();
      const contentType = backendRes.headers.get("content-type") || "video/mp4";
      const disposition =
        backendRes.headers.get("content-disposition") ||
        `attachment; filename="video.mp4"`;

      return new NextResponse(blob, {
        status: backendRes.status,
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": disposition,
          "Content-Length": blob.size.toString(),
        },
      });
    }

    // ── JSON response (default) ──
    let resBody: unknown;
    try {
      resBody = backendRes.headers
        .get("content-type")
        ?.includes("application/json")
        ? await backendRes.json()
        : await backendRes.text();
    } catch (parseErr) {
      const text = await backendRes.text().catch(() => "");
      console.error(
        `[BFF] Failed to parse backend response (${backendRes.status}):`,
        text.slice(0, 500),
        parseErr
      );
      return NextResponse.json(
        { error: "Invalid response from backend" },
        { status: 502 }
      );
    }

    return NextResponse.json(resBody, {
      status: backendRes.status,
    });
  } catch (err) {
    const detail =
      err instanceof TypeError && err.message === "fetch failed"
        ? `Backend unreachable at ${BACKEND_URL}`
        : err instanceof Error
        ? err.message
        : "Backend unreachable";
    console.error("[BFF] Fetch error:", method, url, err);
    return NextResponse.json({ error: detail }, { status: 502 });
  }
}

export async function GET(req: NextRequest) {
  return proxy(req, "GET");
}

export async function POST(req: NextRequest) {
  return proxy(req, "POST");
}

export async function PUT(req: NextRequest) {
  return proxy(req, "PUT");
}

export async function DELETE(req: NextRequest) {
  return proxy(req, "DELETE");
}
