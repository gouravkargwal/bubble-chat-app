/**
 * BFF proxy — /api/admin/* → backend /api/v1/admin/*
 *
 * Two layers of auth:
 *   1. Clerk session required (browser → Next.js)
 *   2. Admin API key header (Next.js → backend)
 *
 * This keeps admin endpoints unreachable from the public internet
 * even if someone discovers the backend URL.
 */

import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://api:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

async function proxy(req: NextRequest, method: string) {
  // ── Layer 1: Clerk session ──
  const session = await auth();
  if (!session.userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // ── Layer 2: Admin API key must be configured ──
  if (!ADMIN_API_KEY) {
    return NextResponse.json(
      { error: "Admin API key not configured on server." },
      { status: 503 }
    );
  }

  // ── Build backend URL ──
  // /api/admin/video-pipeline/candidates → /api/v1/admin/video-pipeline/candidates
  const pathname = req.nextUrl.pathname.replace("/api/admin", "/api/v1/admin");
  const search = req.nextUrl.search;
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
      // Don't follow redirects — let the caller handle them
      redirect: "manual",
    });

    // Build response preserving status and headers
    const resHeaders = new Headers(backendRes.headers);
    // Remove hop-by-hop headers
    resHeaders.delete("transfer-encoding");

    const resBody = backendRes.headers
      .get("content-type")
      ?.includes("application/json")
      ? await backendRes.json()
      : await backendRes.text();

    return NextResponse.json(resBody, {
      status: backendRes.status,
      headers: resHeaders,
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
