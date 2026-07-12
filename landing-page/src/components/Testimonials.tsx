"use client";

import React from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection, StaggerContainer, StaggerItem } from "./Animations";

const EARLY_REVIEWS = [
  {
    quote:
      "Your app actually helped me draft a reply that felt like ME, not some pickup line. That's rare.",
    author: "Friend 1",
    handle: "@friend1",
    source: "Personal Review",
  },
  {
    quote:
      "The photo audit roasted me but honestly it was spot on. Changed my main pic and actually got more matches.",
    author: "Friend 2",
    handle: "@friend2",
    source: "Personal Review",
  },
  {
    quote:
      "Bro the voice DNA thing is wild. It literally caught that I use 'haha' too much. Rude but true.",
    author: "Friend 3",
    handle: "@friend3",
    source: "Personal Review",
  },
  {
    quote:
      "I tested it on a convo I'd been overthinking for hours. It gave me 3 solid options in seconds. Game changer.",
    author: "Friend 4",
    handle: "@friend4",
    source: "Personal Review",
  },
];

export function Testimonials() {
  return (
    <section
      id="testimonials"
      className="relative px-6 py-24 sm:py-32 overflow-hidden"
    >
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          EARLY ACCESS
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          We&rsquo;re Just Getting Started.
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base max-w-lg mx-auto font-mono tracking-wide">
          {">"} currently in beta with{" "}
          <span className="text-nothing-white font-bold">10</span> initial
          downloads &mdash; here&rsquo;s what early testers had to say.
        </p>
      </AnimatedSection>

      <StaggerContainer className="mx-auto max-w-5xl" staggerDelay={0.08}>
        <div className="grid gap-4 sm:grid-cols-2">
          {EARLY_REVIEWS.map((r) => (
            <StaggerItem key={r.author} distance={40}>
              <div className="rounded-xl border border-nothing-border bg-nothing-surface/40 backdrop-blur-sm p-6 hover:border-nothing-text-tertiary/30 transition-colors duration-300">
                {/* Source badge */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-mono text-nothing-text-tertiary tracking-wider">
                    {r.source}
                  </span>
                  <span className="text-[10px] font-mono text-neon-red/60 tracking-wider">
                    VERIFIED
                  </span>
                </div>

                {/* Quote */}
                <p className="text-sm leading-relaxed text-nothing-text-secondary mb-6">
                  &ldquo;{r.quote}&rdquo;
                </p>

                {/* Author */}
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-neon-red/20 flex items-center justify-center text-xs font-bold text-neon-red">
                    {r.author.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-nothing-white">
                      {r.author}
                    </p>
                    <p className="text-xs text-nothing-text-tertiary">
                      {r.handle}
                    </p>
                  </div>
                </div>
              </div>
            </StaggerItem>
          ))}
        </div>
      </StaggerContainer>
    </section>
  );
}
