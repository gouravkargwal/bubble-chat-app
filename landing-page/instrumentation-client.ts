import posthog from "posthog-js";

(function initPostHog() {
  if (process.env.NODE_ENV !== "production") return;

  // Skip PostHog on admin pages — no analytics needed there
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/admin")) {
    return;
  }

  const token = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
  if (!token) {
    console.warn(
      "[PostHog] Skipping init: NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN is not set"
    );
    return;
  }

  posthog.init(token, {
    api_host: "/ph",
    ui_host: "https://us.posthog.com",
    defaults: "2026-01-30",
    capture_exceptions: true,
    capture_pageview: false,
    debug: false,
  });
})();
