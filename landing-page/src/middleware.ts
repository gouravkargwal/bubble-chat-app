import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isAdminRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Match admin pages AND admin API routes so Clerk middleware runs
    // before the BFF proxy calls auth().
    "/admin/:path*",
    "/api/admin/:path*",
  ],
};
