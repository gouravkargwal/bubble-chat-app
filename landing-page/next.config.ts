import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Remotion packages use native platform binaries — don't bundle them,
  // load from node_modules at runtime instead.
  serverExternalPackages: [
    "@remotion/renderer",
    "@remotion/bundler",
    "remotion",
    "esbuild",
  ],
  async rewrites() {
    return [
      {
        source: "/ingest/static/:path*",
        destination: "https://us-assets.i.posthog.com/static/:path*",
      },
      {
        source: "/ingest/array/:path*",
        destination: "https://us-assets.i.posthog.com/array/:path*",
      },
      {
        source: "/ingest/:path*",
        destination: "https://us.i.posthog.com/:path*",
      },
    ];
  },
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
