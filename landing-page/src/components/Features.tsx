"use client";

import React from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import {
  AnimatedSection,
  StaggerContainer,
  StaggerItem,
  ScaleHover,
} from "./Animations";

const FEATURES = [
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
        />
      </svg>
    ),
    title: "Real-Time Chat Analysis",
    description:
      "Detect shifts in tone, engagement, and interest as they happen. Our AI reads between the lines so you never miss a signal.",
    label: "CORE_ENGINE",
  },
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
        />
      </svg>
    ),
    title: "AI-Generated Responses",
    description:
      "Get personalized, high-ROI replies tailored to her personality and the flow of the conversation. Each line is optimized for engagement.",
    label: "TARGET_LOCK",
  },
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.833.166l-1.333 1.333M19.5 10.5H18M7.5 18.167L3.383 21m0 0l2.284-10.18m0 0L3 7.5l3.768 2.5m0 0l.447-1.716"
        />
      </svg>
    ),
    title: "Personality Analysis",
    description:
      "Understand her interests, humor style, and emotional state. Our AI builds a profile so every message feels natural and intentional.",
    label: "PERSONA_SCAN",
  },
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
        />
      </svg>
    ),
    title: "Win Probability Scoring",
    description:
      "Every suggestion comes with a confidence score. Know exactly which messages have the highest chance of getting a reply.",
    label: "ANALYTICS",
  },
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
        />
      </svg>
    ),
    title: "Context Memory",
    description:
      "Never lose track of inside jokes, shared interests, or past conversations. Our AI remembers everything so you stay consistent.",
    label: "MEMORY_MODULE",
  },
  {
    icon: (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    ),
    title: "Privacy First",
    description:
      "Encrypted in transit and at rest. Screenshots auto-delete after analysis. Zero data retention — your conversations stay yours.",
    label: "SECURE",
  },
];

export function Features() {
  return (
    <section
      id="features"
      className="relative px-6 py-24 sm:py-32"
      aria-labelledby="features-heading"
    >
      {/* Section header */}
      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16 sm:mb-20">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          CAPABILITIES
        </div>
        <h2
          id="features-heading"
          className="font-heading text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white"
        >
          Engineered for <span className="text-neon-red">Better Conversations</span>
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
          Every feature is built on real conversation data and tested for
          maximum engagement.
        </p>
      </AnimatedSection>

      {/* Features grid */}
      <StaggerContainer className="mx-auto max-w-6xl" staggerDelay={0.08}>
        <div className="grid gap-px bg-nothing-border sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <StaggerItem key={i}>
              <ScaleHover scale={1.02}>
                <div className="group bg-nothing-black p-6 sm:p-8 transition-all duration-300 hover:bg-nothing-surface">
                  {/* Label */}
                  <span className="inline-block font-mono text-[10px] tracking-[0.15em] text-nothing-text-tertiary mb-6">
                    [ {feature.label} ]
                  </span>

                  {/* Icon */}
                  <motion.div
                    className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg border border-nothing-border text-nothing-white group-hover:text-neon-red transition-colors duration-200"
                    whileHover={{
                      rotate: [0, -10, 10, -5, 0],
                      transition: { duration: 0.4 },
                    }}
                    aria-hidden="true"
                  >
                    {feature.icon}
                  </motion.div>

                  {/* Content */}
                  <h3 className="font-heading text-lg font-bold text-nothing-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-nothing-text-secondary">
                    {feature.description}
                  </p>
                </div>
              </ScaleHover>
            </StaggerItem>
          ))}
        </div>
      </StaggerContainer>
    </section>
  );
}
