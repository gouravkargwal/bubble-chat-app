import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isAdminRoute = createRouteMatcher(["/admin(.*)", "/api/admin(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isAdminRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Protect admin pages (/admin/*) and admin API routes (/api/admin/*).
    // The BFF proxy at /api/admin/[...path]/route.ts calls Clerk's auth()
    // which requires clerkMiddleware to have run for the request first.
    "/admin/:path*",
    "/api/admin/:path*",
  ],
};
