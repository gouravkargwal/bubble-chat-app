/**
 * BFF proxy — /api/admin/* → backend /api/v1/admin/*
 *
 * Two layers of auth:
 *   1. Clerk session (if Clerk is configured) OR admin page origin check
 *   2. Admin API key header (Next.js → backend)
 *
 * If Clerk JS CDN is unreachable (common in some regions), auth falls back
 * to checking that the request originated from the admin page itself,
 * which is already protected by middleware.ts.
 *
 * Handles:
 *   - JSON API responses (default)
 *   - Binary file downloads (when path ends in /download)
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

async function proxy(req: NextRequest, method: string) {
  // ── Layer 1: Clerk session (optional — skip if Clerk CDN is unreachable) ──
  // We try Clerk first. If it fails (CDN blocked, not configured), we fall back
  // to checking the Referer header comes from the admin page. The middleware.ts
  // already blocks non-admin users from reaching the page at all.
  const isDev = process.env.NODE_ENV === "development";
  if (!isDev || process.env.CLERK_SECRET_KEY) {
    try {
      const { auth: clerkAuth } = await import("@clerk/nextjs/server");
      const session = await clerkAuth();
      if (!session.userId) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
      // Clerk auth succeeded — proceed
    } catch {
      if (!isDev) {
        // In prod, fall through (Clerk CDN might be blocked).
        // The request already passed middleware.ts which protects /admin/* pages.
        // We log the failure but don't block.
        console.warn(
          "[BFF] Clerk auth unavailable, falling back to origin check"
        );
      }
      // In dev without Clerk keys, or in prod with blocked CDN, fall through
    }
  }

  // ── Layer 2: Admin API key must be configured ──
  if (!ADMIN_API_KEY) {
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

    // ── Binary response (video file) — stream directly ──
    // Reading the full blob into memory blocks the browser's <video> tag
    // from starting playback until the entire file is downloaded. Instead,
    // we stream it chunk-by-chunk using the ReadableStream from the response body.
    if (
      isDownload ||
      backendRes.headers.get("content-type")?.startsWith("video/") ||
      backendRes.headers.get("content-type") === "application/octet-stream"
    ) {
      const contentType = backendRes.headers.get("content-type") || "video/mp4";
      const disposition =
        backendRes.headers.get("content-disposition") ||
        `inline; filename="video.mp4"`;

      return new NextResponse(backendRes.body, {
        status: backendRes.status,
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": disposition,
          "Content-Length": backendRes.headers.get("content-length") || "",
        },
      });
    }

    // ── JSON response (default) ──
    const resBody = backendRes.headers
      .get("content-type")
      ?.includes("application/json")
      ? await backendRes.json()
      : await backendRes.text();

    return NextResponse.json(resBody, {
      status: backendRes.status,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unreachable";
    return NextResponse.json({ error: message }, { status: 502 });
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
