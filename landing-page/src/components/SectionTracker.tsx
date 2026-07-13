"use client";

import { useEffect, useRef } from "react";
import posthog from "posthog-js";

interface SectionTrackerProps {
  /** The section name sent as the event property (e.g. "pricing", "features") */
  section: string;
  children: React.ReactNode;
  /** CSS classes to apply to the wrapper div */
  className?: string;
  /** Unique id for the section (used as the IntersectionObserver target) */
  id?: string;
}

/**
 * Tracks when a section becomes visible in the viewport.
 * Fires `section_viewed` once per section per page session.
 *
 * Usage:
 *   <SectionTracker section="pricing" id="pricing">
 *     <PricingSection />
 *   </SectionTracker>
 */
export function SectionTracker({
  section,
  children,
  className,
  id,
}: SectionTrackerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const tracked = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || tracked.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !tracked.current) {
          tracked.current = true;
          posthog.capture("section_viewed", { section });
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [section]);

  return (
    <div ref={ref} className={className} id={id}>
      {children}
    </div>
  );
}
