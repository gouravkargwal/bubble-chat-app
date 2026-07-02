"use client";

import React from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection } from "./Animations";

const STEPS = [
  {
    number: "01",
    title: "Connect Your Chat",
    description:
      "Share a screenshot or paste the conversation. Our AI instantly analyzes the tone, engagement level, and her personality signals.",
    detail: "Takes ~3 seconds",
    label: "INPUT",
  },
  {
    number: "02",
    title: "AI Analyzes & Scores",
    description:
      "Our engine runs pattern recognition against thousands of successful interactions. It scores each possible approach for win probability.",
    detail: "95% accuracy rate",
    label: "PROCESS",
  },
  {
    number: "03",
    title: "Get Your Winning Line",
    description:
      "Receive a tailored, high-impact response with an explanation of why it works. Use it as-is or make it your own.",
    detail: "Delivered in real-time",
    label: "OUTPUT",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative px-6 py-24 sm:py-32 overflow-hidden">
      {/* Background accent line */}
      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-nothing-border to-transparent hidden lg:block" />

      {/* Section header */}
      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16 sm:mb-20">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          WORKFLOW
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          Three Steps to{" "}
          <span className="text-neon-red">Conversation Mastery</span>
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
          From confusion to confidence in under 10 seconds.
        </p>
      </AnimatedSection>

      {/* Steps */}
      <div className="mx-auto max-w-4xl relative">
        {/* Connecting line (mobile) */}
        <div className="absolute left-[19px] top-0 bottom-0 w-px bg-nothing-border sm:left-[29px] lg:hidden" />

        <div className="space-y-12 sm:space-y-16 lg:space-y-24 relative">
          {STEPS.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: i % 2 === 0 ? -80 : 80 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{
                duration: 0.8,
                delay: i * 0.15,
                ease: [0.16, 1, 0.3, 1],
              }}
              className={`group relative flex flex-col lg:flex-row items-start gap-6 lg:gap-12 ${
                i % 2 === 1 ? "lg:flex-row-reverse" : ""
              }`}
            >
              {/* Number + connector */}
              <div className="relative z-10 flex-shrink-0">
                <motion.div
                  className="flex h-[38px] w-[38px] sm:h-[58px] sm:w-[58px] items-center justify-center rounded-full border border-nothing-border bg-nothing-black text-xs sm:text-sm font-extrabold text-nothing-white transition-all duration-300 group-hover:border-neon-red group-hover:text-neon-red"
                  whileHover={{ scale: 1.1, borderColor: "#FF003C" }}
                  transition={{ type: "spring", stiffness: 300, damping: 15 }}
                >
                  {step.number}
                </motion.div>
                {/* Connecting dot pulse */}
                <motion.div
                  className="absolute inset-0 rounded-full border border-neon-red/30"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.8 }}
                />
              </div>

              {/* Content */}
              <div
                className={`flex-1 lg:w-1/2 ${
                  i % 2 === 1 ? "lg:text-right" : ""
                }`}
              >
                <span className="inline-block font-mono text-[10px] tracking-[0.15em] text-nothing-text-tertiary mb-3">
                  [ {step.label} ]
                </span>
                <h3 className="text-xl sm:text-2xl font-bold text-nothing-white mb-3">
                  {step.title}
                </h3>
                <p className="text-sm sm:text-base leading-relaxed text-nothing-text-secondary max-w-md">
                  {step.description}
                </p>
                <motion.div
                  className="mt-4 flex items-center gap-2 text-xs font-mono text-nothing-text-tertiary tracking-wider"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 + i * 0.2 }}
                >
                  <motion.svg
                    className="h-3.5 w-3.5 text-nothing-success"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                    animate={{ rotate: [0, 360] }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4.5 12.75l6 6 9-13.5"
                    />
                  </motion.svg>
                  <span>{step.detail}</span>
                </motion.div>
              </div>

              {/* Spacer for alternating layout */}
              <div className="hidden lg:block lg:w-1/2" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
