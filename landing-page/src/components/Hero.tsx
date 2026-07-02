"use client";

import React from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import { ParallaxLayer, ScaleHover } from "./Animations";

export function Hero() {
  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 40 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.7,
        ease: [0.16, 1, 0.3, 1] as const,
      },
    },
  };

  const headlineWords = ["Never", "Lose", "The", "Conversation", "Again."];

  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-24 pb-16 overflow-hidden">
      {/* Subtle grid background with parallax */}
      <ParallaxLayer
        speed={0.15}
        className="absolute inset-0 pointer-events-none"
      >
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
      </ParallaxLayer>

      {/* Animated ambient glow */}
      <motion.div
        className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(255,0,60,0.08) 0%, transparent 70%)",
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Top-right status bar decoration */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="absolute top-28 right-8 hidden lg:flex items-center gap-2 text-xs text-nothing-text-tertiary font-mono tracking-wider"
      >
        <StatusDot active />
        <span>SYSTEM_ONLINE // v2.0</span>
      </motion.div>

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-4xl text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-8 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface/80 backdrop-blur-sm px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider"
        >
          <StatusDot active />
          AI-POWERED DATING COACH
        </motion.div>

        {/* Main headline — word-by-word reveal */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-extrabold leading-[0.95] tracking-tight"
        >
          {headlineWords.map((word, i) => (
            <motion.span
              key={i}
              variants={{
                hidden: { opacity: 0, y: 60, scale: 0.95 },
                visible: {
                  opacity: 1,
                  y: 0,
                  scale: 1,
                  transition: {
                    duration: 0.8,
                    ease: [0.16, 1, 0.3, 1] as const,
                  },
                },
              }}
              className={`inline-block mr-[0.3em] ${
                i === 3 ? "text-neon-red" : "text-nothing-white"
              }`}
            >
              {word}
            </motion.span>
          ))}
        </motion.div>

        {/* Subtext */}
        <motion.p
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="mx-auto mt-6 max-w-2xl text-base sm:text-lg leading-relaxed text-nothing-text-secondary"
        >
          Cookd analyzes your real-time chats and crafts personalized,
          high-impact opening lines and responses based on her personality. Stop
          guessing — start winning.
        </motion.p>

        {/* CTA — Primary action: redirect to Google Play */}
        <motion.div
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <ScaleHover scale={1.05}>
            <a
              href="https://play.google.com/store/apps/details?id=com.cookd.mobile"
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex items-center gap-2 rounded-full bg-neon-red px-8 py-3.5 text-sm font-bold text-nothing-white transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,0,60,0.25)]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5" />
              </svg>
              <span>Get on Google Play</span>
              <motion.svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
                animate={{ x: [0, 3, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </motion.svg>
            </a>
          </ScaleHover>
          <ScaleHover scale={1.05}>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface/80 backdrop-blur-sm px-8 py-3.5 text-sm font-bold text-nothing-white transition-all duration-200 hover:bg-nothing-white/5"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              See How It Works
            </a>
          </ScaleHover>
        </motion.div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-nothing-black to-transparent pointer-events-none" />
    </section>
  );
}
