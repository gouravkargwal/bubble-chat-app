"use client";

import {
  useState,
  useCallback,
  useEffect,
  lazy,
  Suspense,
  type ReactNode,
} from "react";
import { Header } from "@/components/Header";
import { SectionTracker } from "@/components/SectionTracker";
import type { ReplyItem } from "@/components/interactive-hero/types";
import posthog from "posthog-js";

// Dynamic imports for heavy components — keeps the initial bundle small
const InteractiveHero = lazy(() =>
  import("@/components/interactive-hero").then((m) => ({
    default: m.InteractiveHero,
  }))
);
const AppMockup = lazy(() =>
  import("@/components/AppMockup").then((m) => ({ default: m.AppMockup }))
);
const Features = lazy(() =>
  import("@/components/Features").then((m) => ({ default: m.Features }))
);
const HowItWorks = lazy(() =>
  import("@/components/HowItWorks").then((m) => ({ default: m.HowItWorks }))
);
const Pricing = lazy(() =>
  import("@/components/Pricing").then((m) => ({ default: m.Pricing }))
);
const FAQ = lazy(() =>
  import("@/components/FAQ").then((m) => ({ default: m.FAQ }))
);
const CTA = lazy(() =>
  import("@/components/CTA").then((m) => ({ default: m.CTA }))
);
const Footer = lazy(() =>
  import("@/components/Footer").then((m) => ({ default: m.Footer }))
);

function SectionFallback({ height = "400px" }: { height?: string }) {
  return (
    <div
      className="flex items-center justify-center"
      style={{ minHeight: height }}
      aria-hidden="true"
    />
  );
}

/**
 * ClientShell wraps all interactive sections.
 *
 * This component is the ONLY "use client" wrapper needed at the top level.
 * It holds the shared state (generated replies, mobile CTA) that flows
 * between the InteractiveHero funnel and the AppMockup display.
 */
export function ClientShell() {
  const [generatedReplies, setGeneratedReplies] = useState<ReplyItem[] | null>(
    null
  );

  // Re-identify returning visitors from session storage
  useEffect(() => {
    const storedId = sessionStorage.getItem("posthog_distinct_id");
    if (storedId) {
      posthog.identify(storedId);
    }
  }, []);

  const handleRepliesReady = useCallback((replies: ReplyItem[]) => {
    setGeneratedReplies(replies);
  }, []);

  const handleReset = useCallback(() => {
    setGeneratedReplies(null);
  }, []);

  return (
    <>
      <Header />
      <main>
        <Suspense fallback={<SectionFallback height="100vh" />}>
          <InteractiveHero onRepliesReady={handleRepliesReady} />
        </Suspense>
        <Suspense fallback={<SectionFallback />}>
          <AppMockup replies={generatedReplies ?? undefined} />
        </Suspense>
        <SectionTracker section="features" id="features">
          <Suspense fallback={<SectionFallback />}>
            <Features />
          </Suspense>
        </SectionTracker>
        <SectionTracker section="how_it_works" id="how-it-works">
          <Suspense fallback={<SectionFallback />}>
            <HowItWorks />
          </Suspense>
        </SectionTracker>
        <SectionTracker section="pricing" id="pricing">
          <Suspense fallback={<SectionFallback />}>
            <Pricing />
          </Suspense>
        </SectionTracker>
        <SectionTracker section="faq" id="faq">
          <Suspense fallback={<SectionFallback />}>
            <FAQ />
          </Suspense>
        </SectionTracker>
        <SectionTracker section="cta" id="cta">
          <Suspense fallback={<SectionFallback />}>
            <CTA />
          </Suspense>
        </SectionTracker>
      </main>
      <Suspense fallback={null}>
        <Footer />
      </Suspense>
    </>
  );
}
