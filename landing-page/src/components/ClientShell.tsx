"use client";

import { useState, useCallback, useEffect, type ReactNode } from "react";
import { Header } from "@/components/Header";
import { InteractiveHero } from "@/components/interactive-hero";
import { AppMockup } from "@/components/AppMockup";
import { Features } from "@/components/Features";
import { HowItWorks } from "@/components/HowItWorks";
import { Pricing } from "@/components/Pricing";
import { FAQ } from "@/components/FAQ";
import { CTA } from "@/components/CTA";
import { Footer } from "@/components/Footer";
import { SectionTracker } from "@/components/SectionTracker";
import type { ReplyItem } from "@/components/interactive-hero/types";
import { APP_URLS, SITE } from "@/app/constants";
import posthog from "posthog-js";

/**
 * ClientShell wraps all interactive sections.
 *
 * This component is the ONLY "use client" wrapper needed at the top level.
 * It holds the shared state (generated replies, mobile CTA) that flows
 * between the InteractiveHero funnel and the AppMockup display.
 *
 * Everything else can be a server component for better SSR/SEO.
 */
export function ClientShell() {
  const [generatedReplies, setGeneratedReplies] = useState<ReplyItem[] | null>(
    null
  );
  const [showMobileCTA, setShowMobileCTA] = useState(false);

  // Re-identify returning visitors from session storage
  useEffect(() => {
    const storedId = sessionStorage.getItem("posthog_distinct_id");
    if (storedId) {
      posthog.identify(storedId);
    }
  }, []);

  // Show sticky CTA on scroll past 50% of page height
  useEffect(() => {
    const onScroll = () => {
      if (showMobileCTA) return;
      const scrollPercent =
        window.scrollY / (document.body.scrollHeight - window.innerHeight);
      if (scrollPercent > 0.5) setShowMobileCTA(true);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [showMobileCTA]);

  const handleRepliesReady = useCallback((replies: ReplyItem[]) => {
    setGeneratedReplies(replies);
    setShowMobileCTA(true);
    setTimeout(() => {
      document
        .getElementById("app-mockup")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 400);
  }, []);

  const handleReset = useCallback(() => {
    setGeneratedReplies(null);
  }, []);

  return (
    <>
      <Header />
      <main>
        <InteractiveHero onRepliesReady={handleRepliesReady} />
        <AppMockup replies={generatedReplies ?? undefined} />
        <SectionTracker section="features" id="features">
          <Features />
        </SectionTracker>
        <SectionTracker section="how_it_works" id="how-it-works">
          <HowItWorks />
        </SectionTracker>
        <SectionTracker section="pricing" id="pricing">
          <Pricing />
        </SectionTracker>
        <SectionTracker section="faq" id="faq">
          <FAQ />
        </SectionTracker>
        <SectionTracker section="cta" id="cta">
          <CTA />
        </SectionTracker>
      </main>
      <Footer />

      {/* Sticky mobile CTA bar */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300 md:hidden ${
          showMobileCTA ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="flex items-center justify-between gap-3 border-t border-nothing-border bg-nothing-black/95 backdrop-blur-md px-4 py-3">
          <div className="flex flex-col">
            <span className="font-heading text-xs font-bold text-nothing-white leading-tight">
              {SITE.name} — {SITE.tagline}
            </span>
            <span className="text-[10px] font-mono text-nothing-text-tertiary">
              Get the perfect reply in seconds
            </span>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={APP_URLS.googlePlay}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() =>
                posthog.capture("app_download_clicked", {
                  source: "sticky_mobile_cta",
                  platform: "google_play",
                })
              }
              className="inline-flex items-center gap-1.5 rounded-full bg-neon-red px-4 py-2 text-xs font-bold text-nothing-white whitespace-nowrap"
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                />
              </svg>
              Google Play
            </a>
            <a
              href={APP_URLS.iosWaitlist}
              onClick={() =>
                posthog.capture("ios_waitlist_clicked", {
                  source: "mobile_sticky_cta",
                })
              }
              className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border px-4 py-2 text-xs font-bold text-nothing-white whitespace-nowrap"
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                />
              </svg>
              iOS Waitlist
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
