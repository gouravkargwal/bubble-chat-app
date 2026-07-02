"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection } from "./Animations";

type AppState = "bubble" | "loading" | "expanded";

const REPLIES = [
  {
    label: "Flirty",
    text: "There's a trail that ends at this cute cafe... but I'd need someone cute to go with \ud83d\ude0f",
    strategy: "CHARM",
    recommended: true,
    reasoning:
      "She engaged with playful energy \u2014 mirror it. The compliment is implied, not stated, making it land harder.",
  },
  {
    label: "Witty",
    text: "Anywhere the WiFi is weak and the views are strong. My phone needs a detox.",
    strategy: "PATTERN_INTERRUPT",
    recommended: false,
    reasoning: null,
  },
  {
    label: "Smooth",
    text: "There's a spot near Triund with unreal sunsets and filter coffee at the top.",
    strategy: "VISUAL_HOOK",
    recommended: false,
    reasoning: null,
  },
  {
    label: "Bold",
    text: "I know a trail. You bring the playlist. Let's find out if your music taste matches your hiking game.",
    strategy: "CHALLENGE",
    recommended: false,
    reasoning: null,
  },
];

// ── Dot matrix ring ──
function DotMatrixRing({ size = 56, pulse = false }: { size?: number; pulse?: boolean }) {
  const cx = size / 2;
  const cy = size / 2;
  const dotRadius = size * 0.022;
  const ringRadius = size * 0.5 - 2 - size * 0.07;
  const dotCount = 24;
  const dots = [];

  for (let i = 0; i < dotCount; i++) {
    const angle = (360 / dotCount) * i * (Math.PI / 180);
    const x = cx + ringRadius * Math.cos(angle);
    const y = cy + ringRadius * Math.sin(angle);
    dots.push(
      <motion.circle
        key={i}
        cx={x}
        cy={y}
        r={dotRadius}
        fill="rgba(255,255,255,0.5)"
        animate={pulse ? { opacity: [0.3, 1, 0.3] } : undefined}
        transition={
          pulse
            ? {
                duration: 1.2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: (i / dotCount) * 0.8,
              }
            : undefined
        }
      />,
    );
  }

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
      <circle cx={cx} cy={cy} r={ringRadius + dotRadius} fill="none" />
      {dots}
    </svg>
  );
}

// ── Cookd "C" Logo ──
function CLogo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 108 108" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="54" cy="54" r="28" fill="white" />
      <path
        d="M63.73,45.51 A12,12 0 1,0 63.73,62.49 L61.31,60.07 A8.6,8.6 0 1,1 61.31,47.93 Z"
        fill="black"
        fillRule="evenodd"
      />
    </svg>
  );
}

// ── Strategy badge ──
function StrategyBadge({ text }: { text: string }) {
  return (
    <div className="inline-flex rounded-full border border-nothing-border px-2 py-0.5">
      <span className="text-[9px] font-mono text-nothing-text-secondary tracking-wider">[ {text} ]</span>
    </div>
  );
}

// ── Shimmer skeleton card (matching LoadingPanel.kt) ──
function ShimmerSkeletonCard() {
  return (
    <div className="rounded-xl border border-nothing-border bg-nothing-surface overflow-hidden">
      <div className="p-3.5 space-y-3">
        <motion.div
          className="h-3 w-1/3 rounded bg-nothing-white/10"
          animate={{ opacity: [0.2, 0.6, 0.2] }}
          transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="h-3 w-full rounded bg-nothing-white/10"
          animate={{ opacity: [0.2, 0.6, 0.2] }}
          transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.1 }}
        />
        <motion.div
          className="h-3 w-2/3 rounded bg-nothing-white/10"
          animate={{ opacity: [0.2, 0.6, 0.2] }}
          transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
        />
        <div className="flex justify-between pt-2">
          <motion.div
            className="h-3 w-1/5 rounded bg-nothing-white/10"
            animate={{ opacity: [0.2, 0.6, 0.2] }}
            transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.15 }}
          />
          <motion.div
            className="h-5 w-1/5 rounded bg-nothing-white/10"
            animate={{ opacity: [0.2, 0.6, 0.2] }}
            transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.25 }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Pulsing dots (matching ProcessingOverlay in LoadingPanel.kt) ──
function LoadingDots() {
  return (
    <div className="flex items-center justify-center gap-2.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="h-2 w-2 rounded-full bg-nothing-white"
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            ease: "easeInOut",
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  );
}

// ── Suggestion Card (interactive) ──
function SuggestionCard({
  label,
  text,
  strategy,
  recommended,
  reasoning,
  index,
}: {
  label: string;
  text: string;
  strategy: string;
  recommended: boolean;
  reasoning: string | null;
  index: number;
}) {
  const [copied, setCopied] = React.useState(false);
  const [liked, setLiked] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    if (copied) {
      const t = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(t);
    }
  }, [copied]);

  const staggerDelay = 0.1 + index * 0.08;

  return (
    <motion.div
      className="rounded-xl border overflow-hidden"
      style={{
        borderColor: recommended ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.1)",
        borderWidth: recommended ? 1.5 : 1,
        background: "rgba(18,18,18,0.95)",
      }}
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: staggerDelay,
        duration: 0.4,
        ease: [0.16, 1, 0.3, 1],
      }}
      whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.25)" }}
    >
      <div className="p-3 sm:p-3.5">
        {/* Header */}
        <div className="flex items-center justify-between mb-1.5">
          <motion.span
            className="text-[10px] font-bold tracking-wider"
            style={{ color: recommended ? "#FF003C" : "#FFFFFF" }}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: staggerDelay + 0.1, duration: 0.3 }}
          >
            {recommended ? "WINGMAN'S CHOICE" : label.toUpperCase()}
          </motion.span>
          {recommended && (
            <motion.span
              className="text-[9px] font-bold text-nothing-success"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: staggerDelay + 0.2, duration: 0.3, type: "spring" }}
            >
              ★ BEST
            </motion.span>
          )}
        </div>

        {/* Strategy badge */}
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: staggerDelay + 0.15, duration: 0.3 }}
        >
          <StrategyBadge text={strategy} />
        </motion.div>

        {/* Reply text */}
        <motion.p
          className="mt-1.5 text-[12px] leading-relaxed text-nothing-white sm:text-[13px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: staggerDelay + 0.2, duration: 0.35 }}
        >
          {text}
        </motion.p>

        {/* Coach reasoning */}
        {recommended && reasoning && (
          <motion.p
            className="mt-1.5 text-[10px] italic leading-relaxed text-nothing-text-tertiary"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            transition={{ delay: staggerDelay + 0.3, duration: 0.4 }}
          >
            {reasoning}
          </motion.p>
        )}

        {/* Actions row */}
        <motion.div
          className="mt-2 flex items-center justify-between"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: staggerDelay + 0.3, duration: 0.25 }}
        >
          <motion.button
            onClick={() => setCopied(true)}
            className="flex items-center gap-1 transition-colors duration-200"
            style={{ color: copied ? "#00FF66" : "rgba(255,255,255,0.45)" }}
            whileTap={{ scale: 0.92 }}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            <span className="text-[10px] font-medium">{copied ? "Copied!" : "Copy"}</span>
          </motion.button>

          <div className="flex items-center gap-1">
            <motion.button
              onClick={() => setLiked(true)}
              className="p-1 transition-colors duration-200"
              style={{ color: liked === true ? "#00FF66" : liked === false ? "rgba(255,255,255,0.45)" : "rgba(255,255,255,0.45)" }}
              whileTap={{ scale: 0.85 }}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                />
              </svg>
            </motion.button>
            <motion.button
              onClick={() => setLiked(false)}
              className="p-1 transition-colors duration-200"
              style={{ color: liked === false ? "#FF003C" : liked === true ? "rgba(255,255,255,0.45)" : "rgba(255,255,255,0.45)" }}
              whileTap={{ scale: 0.85 }}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
                />
              </svg>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

// ── Main Interactive AppMockup ──
export function AppMockup() {
  const [state, setState] = React.useState<AppState>("bubble");
  const [progress, setProgress] = React.useState(0);

  // Auto-advance state machine
  React.useEffect(() => {
    if (state === "bubble") {
      const t = setTimeout(() => {
        setState("loading");
        setProgress(0);
      }, 2500);
      return () => clearTimeout(t);
    }

    if (state === "loading") {
      // Advance loading progress every 600ms: 0→1→2→3 (done)
      if (progress < 3) {
        const t = setTimeout(() => setProgress((p) => p + 1), 800);
        return () => clearTimeout(t);
      } else {
        const t = setTimeout(() => setState("expanded"), 400);
        return () => clearTimeout(t);
      }
    }
  }, [state, progress]);

  // Feature data
  const features = [
    {
      num: "01",
      title: "Tap the Bubble",
      desc: "The signature Cookd bubble floats over your chat. One tap and it captures the conversation to craft AI-powered replies.",
    },
    {
      num: "02",
      title: "Review Your Options",
      desc: "Four distinct vibes — Flirty, Witty, Smooth, Bold — each with a strategy label and optional coach reasoning.",
    },
    {
      num: "03",
      title: "Copy & Send",
      desc: "Tap a card to copy it to your clipboard. Like or dislike to train your style. Hit Regenerate for fresh options.",
    },
  ];

  return (
    <section className="relative px-6 py-24 sm:py-32 overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <div className="relative mx-auto max-w-6xl">
        {/* Section header */}
        <AnimatedSection className="text-center mb-16">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
            <StatusDot active />
            {state === "bubble"
              ? "TAP THE BUBBLE"
              : state === "loading"
                ? "ANALYZING..."
                : "READY TO COPY"}
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
            See It in <span className="text-neon-red">Action</span>
          </h2>
          <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
            {state === "bubble"
              ? "A floating bubble sits on your chat screen. Tap it to generate replies."
              : state === "loading"
                ? "Cookd analyzes the conversation and crafts your options..."
                : "Four distinct vibes. One perfect reply."}
          </p>
        </AnimatedSection>

        {/* Phone + Overlay */}
        <div className="flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-16">
          {/* Phone mockup */}
          <AnimatedSection direction="left" className="flex-shrink-0">
            <div className="relative w-[300px] sm:w-[340px]">
              {/* Phone frame */}
              <div className="relative rounded-[2.5rem] border border-nothing-border bg-nothing-black p-3 shadow-[0_0_60px_rgba(255,0,60,0.06)]">
                {/* Notch */}
                <div className="mx-auto mb-2 h-5 w-24 rounded-b-xl bg-nothing-black" />

                {/* Screen */}
                <div className="rounded-[1.25rem] bg-[#0a0a0a] overflow-hidden min-h-[580px] relative">
                  {/* ── Chat screen ── */}
                  <div className="p-3" style={{ paddingBottom: state === "expanded" ? "340px" : "40px" }}>
                    {/* Chat header */}
                    <div className="text-center pb-2 mb-2 border-b border-nothing-border/50">
                      <p className="text-[11px] font-bold text-nothing-white tracking-wide">PRIYA</p>
                      <p className="text-[8px] font-mono text-nothing-text-tertiary tracking-wider">ONLINE</p>
                    </div>

                    {/* Messages */}
                    <div className="space-y-2">
                      <motion.div
                        className="flex justify-start"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                      >
                        <div className="max-w-[85%] rounded-xl rounded-bl-sm bg-nothing-surface border border-nothing-border px-2.5 py-1.5 text-[10px] leading-relaxed text-nothing-text-secondary">
                          Hey! I saw you&apos;re into hiking too. What&apos;s your favourite trail?
                        </div>
                      </motion.div>
                      <motion.div
                        className="flex justify-end"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                      >
                        <div className="max-w-[85%] rounded-xl rounded-br-sm bg-neon-red/20 border border-neon-red/30 px-2.5 py-1.5 text-[10px] leading-relaxed text-nothing-white">
                          The one that leads to good coffee afterwards ☕
                        </div>
                      </motion.div>
                      <motion.div
                        className="flex justify-start"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.8, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                      >
                        <div className="max-w-[85%] rounded-xl rounded-bl-sm bg-nothing-surface border border-nothing-border px-2.5 py-1.5 text-[10px] leading-relaxed text-nothing-text-secondary">
                          Haha priorities! Where do you usually go?
                        </div>
                      </motion.div>
                    </div>
                  </div>

                  {/* ── Bubble overlay (shown when state is bubble or loading) ── */}
                  <AnimatePresence>
                    {(state === "bubble" || state === "loading") && (
                      <motion.div
                        key="bubble"
                        className="absolute top-28 right-3 z-20"
                        initial={{ opacity: 0, scale: 0.88, x: 20 }}
                        animate={{ opacity: 1, scale: 1, x: 0 }}
                        exit={{ opacity: 0, scale: 0.92, x: 20 }}
                        transition={{
                          opacity: { duration: 0.34 },
                          scale: { type: "spring", damping: 18, stiffness: 200 },
                          x: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
                        }}
                        onClick={() => {
                          if (state === "bubble") {
                            setState("loading");
                            setProgress(0);
                          }
                        }}
                      >
                        {/* Floating animation */}
                        <motion.div
                          animate={state === "bubble" ? { y: [0, -6, 0] } : {}}
                          transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: "easeInOut",
                          }}
                          className="relative cursor-pointer"
                        >
                          {/* Click ripple */}
                          {state === "bubble" && (
                            <motion.div
                              className="absolute inset-0 rounded-full"
                              animate={{
                                boxShadow: [
                                  "0 0 0 0px rgba(255,255,255,0)",
                                  "0 0 0 8px rgba(255,255,255,0.08)",
                                  "0 0 0 16px rgba(255,255,255,0)",
                                ],
                              }}
                              transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                            />
                          )}

                          {/* Pulse when loading */}
                          <motion.div
                            className="relative h-14 w-14"
                            animate={
                              state === "loading"
                                ? {
                                    scale: [1, 1.08, 1],
                                  }
                                : {}
                            }
                            transition={
                              state === "loading"
                                ? { duration: 0.8, repeat: Infinity, ease: "easeInOut" }
                                : {}
                            }
                          >
                            {/* Glow when loading */}
                            <motion.div
                              className="absolute inset-0 rounded-full"
                              animate={
                                state === "loading"
                                  ? {
                                      boxShadow: [
                                        "0 0 4px rgba(255,255,255,0.2)",
                                        "0 0 12px rgba(255,255,255,0.4)",
                                        "0 0 4px rgba(255,255,255,0.2)",
                                      ],
                                    }
                                  : {}
                              }
                              transition={
                                state === "loading"
                                  ? { duration: 0.8, repeat: Infinity, ease: "easeInOut" }
                                  : {}
                              }
                            />
                            <div className="absolute inset-0 rounded-full bg-nothing-black/80 border-2 border-nothing-white" />
                            <DotMatrixRing size={56} pulse={state === "loading"} />
                            <div className="absolute inset-0 flex items-center justify-center">
                              <CLogo size={28} />
                            </div>
                          </motion.div>

                          {/* "Tap me" hint */}
                          {state === "bubble" && (
                            <motion.div
                              className="absolute -top-8 right-0 whitespace-nowrap"
                              initial={{ opacity: 0, y: 4 }}
                              animate={{ opacity: [0, 1, 1, 0], y: [4, 0, 0, -4] }}
                              transition={{
                                duration: 3,
                                repeat: Infinity,
                                ease: "easeInOut",
                                times: [0, 0.15, 0.85, 1],
                              }}
                            >
                              <span className="text-[8px] font-mono text-nothing-text-secondary tracking-wider bg-nothing-surface/80 px-2 py-0.5 rounded-full border border-nothing-border">
                                Tap me →
                              </span>
                            </motion.div>
                          )}
                        </motion.div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* ── Loading overlay (shown when state is loading) ── */}
                  <AnimatePresence>
                    {state === "loading" && (
                      <motion.div
                        key="loading"
                        className="absolute inset-0 z-10 rounded-[1.25rem] overflow-hidden"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.24 }}
                      >
                        {/* Scrim */}
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" />

                        {/* Loading content */}
                        <div className="relative z-10 flex flex-col items-center justify-center h-full px-4">
                          {/* Status text */}
                          <div className="text-center mb-8">
                            <motion.p
                              className="text-[15px] font-bold text-nothing-white"
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: 0.1, duration: 0.3 }}
                            >
                              Cooking up replies              <motion.span
                animate={{ opacity: [1, 0.2, 1] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              >
                                ...
                              </motion.span>
                            </motion.p>
                            <LoadingDots />
                          </div>

                          {/* Skeleton cards */}
                          <div className="w-full space-y-2 px-2">
                            {[0, 1, 2].map((i) => (
                              <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 + i * 0.1, duration: 0.3 }}
                              >
                                <ShimmerSkeletonCard />
                              </motion.div>
                            ))}
                          </div>

                          {/* Progress text */}
                          <motion.p
                            className="mt-6 text-[10px] font-mono text-nothing-text-tertiary tracking-wider"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.5, duration: 0.3 }}
                          >
                            {progress === 0 && "Analyzing her vibe..."}
                            {progress === 1 && "Cloning your style..."}
                            {progress === 2 && "Crafting replies..."}
                            {progress >= 3 && "Almost done"}
                          </motion.p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* ── Expanded suggestion panel (shown when state is expanded) ── */}
                  <AnimatePresence>
                    {state === "expanded" && (
                      <motion.div
                        key="expanded"
                        className="absolute bottom-0 left-0 right-0 z-10 rounded-t-xl border border-nothing-border shadow-[0_-4px_20px_rgba(0,0,0,0.5)]"
                        style={{ background: "rgba(12,12,12,0.97)" }}
                        initial={{ y: "100%" }}
                        animate={{ y: 0 }}
                        exit={{ y: "100%" }}
                        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                      >
                        {/* Panel handle */}
                        <div className="mx-auto my-2 h-1 w-8 rounded-full bg-nothing-border" />

                        <div className="px-3 pb-3 max-h-[340px] overflow-y-auto">
                          {/* Cards */}
                          <div className="space-y-2">
                            {REPLIES.map((reply, i) => (
                              <SuggestionCard
                                key={i}
                                label={reply.label}
                                text={reply.text}
                                strategy={reply.strategy}
                                recommended={reply.recommended}
                                reasoning={reply.reasoning}
                                index={i}
                            />
                            ))}
                          </div>

                          {/* Regenerate button */}
                          <motion.div
                            className="mt-2 mb-1"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6, duration: 0.3 }}
                          >
                            <motion.button
                              onClick={() => {
                                setState("loading");
                                setProgress(0);
                              }}
                              className="flex w-full items-center justify-center gap-2 rounded-full bg-nothing-white py-2.5 text-[11px] font-bold text-nothing-black transition-all duration-200 hover:bg-nothing-white/90"
                              whileTap={{ scale: 0.97 }}
                            >
                              <motion.svg
                                className="h-3.5 w-3.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2.5}
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                />
                              </motion.svg>
                              Regenerate
                            </motion.button>
                          </motion.div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>
          </AnimatedSection>

          {/* Feature highlights */}
          <AnimatedSection direction="right" className="max-w-sm">
            <div className="space-y-5">
              {features.map((item, i) => {
                const isActive =
                  (state === "bubble" && i === 0) ||
                  (state === "loading" && i === 1) ||
                  (state === "expanded" && i === 2);

                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 30 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.15, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    animate={{
                      borderColor: isActive
                        ? "rgba(255,255,255,0.25)"
                        : "rgba(255,255,255,0.06)",
                    }}
                    className="group flex gap-4 p-4 rounded-xl border transition-all duration-500"
                  >
                    <div
                      className={`flex-shrink-0 w-10 h-10 rounded-lg border flex items-center justify-center transition-all duration-500 ${
                        isActive
                          ? "bg-neon-red/10 border-neon-red/40"
                          : "bg-nothing-surface border-nothing-border"
                      }`}
                    >
                      <span
                        className={`text-xs font-mono font-bold transition-colors duration-500 ${
                          isActive ? "text-neon-red" : "text-nothing-text-secondary"
                        }`}
                      >
                        {item.num}
                      </span>
                    </div>
                    <div>
                      <h4
                        className={`text-sm font-bold mb-1 transition-colors duration-500 ${
                          isActive ? "text-nothing-white" : "text-nothing-text-secondary"
                        }`}
                      >
                        {item.title}
                      </h4>
                      <p className="text-xs text-nothing-text-tertiary leading-relaxed">{item.desc}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </AnimatedSection>
        </div>
      </div>
    </section>
  );
}
