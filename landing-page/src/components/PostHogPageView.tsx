"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import posthog from "posthog-js";

/**
 * Captures $pageview events on route change.
 * Must be mounted inside <Suspense> in the root layout because
 * useSearchParams() requires a Suspense boundary in Next.js 15+.
 *
 * Usage in root layout:
 *   <Suspense fallback={null}><PostHogPageView /></Suspense>
 */
export function PostHogPageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Skip pageview tracking on admin pages — PostHog is not initialized there
    if (pathname?.startsWith("/admin")) return;

    if (pathname) {
      const url = searchParams?.toString()
        ? `${pathname}?${searchParams.toString()}`
        : pathname;
      posthog.capture("$pageview", { $current_url: url });
    }
  }, [pathname, searchParams]);

  return null;
}
