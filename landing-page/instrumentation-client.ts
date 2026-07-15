import posthog from "posthog-js";

if (process.env.NODE_ENV === "production") {
  const token = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
  if (!token) {
    console.warn(
      "[PostHog] Skipping init: NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN is not set"
    );
  } else {
    posthog.init(token, {
      api_host: "/ph",
      ui_host: "https://us.posthog.com",
      defaults: "2026-01-30",
      capture_exceptions: true,
      capture_pageview: false,
      debug: false,
    });
  }
}
