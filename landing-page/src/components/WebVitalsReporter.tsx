"use client";

import { useReportWebVitals } from "next/web-vitals";
import posthog from "posthog-js";

/**
 * Reports Core Web Vitals to PostHog for historical monitoring.
 *
 * This gives you a dashboard of real-user LCP, FID/INP, CLS, FCP, TTFB
 * so you can track improvements over time after deploys.
 *
 * Metrics reference:
 *   LCP  (Largest Contentful Paint)  — ≤2.5s  (good)
 *   FID  (First Input Delay)          — ≤100ms (good)
 *   INP  (Interaction to Next Paint)  — ≤200ms (good)
 *   CLS  (Cumulative Layout Shift)    — ≤0.1   (good)
 *   FCP  (First Contentful Paint)     — ≤1.8s  (good)
 *   TTFB (Time to First Byte)         — ≤800ms (good)
 */
export function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    // Send to PostHog
    posthog.capture("web_vital", {
      metric: metric.name,
      value: metric.value,
      rating: metric.rating, // 'good' | 'needs-improvement' | 'poor'
      delta: metric.delta,
      id: metric.id,
      // Navigation type: 'navigate' | 'reload' | 'back-forward' | 'prerender'
      navigationType: metric.navigationType,
    });

    // Also log to console in development for quick feedback
    if (process.env.NODE_ENV === "development") {
      console.log(
        `[Web Vitals] ${metric.name}: ${metric.value} (${metric.rating})`
      );
    }
  });

  return null;
}
