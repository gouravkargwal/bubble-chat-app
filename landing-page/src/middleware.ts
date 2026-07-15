import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isAdminRoute = createRouteMatcher(["/admin(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isAdminRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Match only admin routes — skip all Next.js internals, static files,
    // and the public landing page which doesn't need Clerk middleware.
    "/admin/:path*",
  ],
};
