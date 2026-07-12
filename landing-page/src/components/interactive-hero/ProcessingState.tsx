"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
import { StateBadge } from "./StateBadge";
import { StatusDot } from "../Logo";
import { TERMINAL_LINES, slideUp } from "./types";

export function ProcessingState() {
  const [visibleLines, setVisibleLines] = useState(0);
  const [terminalComplete, setTerminalComplete] = useState(false);
  const startTimeRef = useRef(Date.now());

  // Deterministic delay for each line (golden ratio spread)
  // Slower pacing so the terminal feels genuine: 600–1200ms per line
  const lineDelays = useMemo(
    () =>
      TERMINAL_LINES.map(
        (_, i) => 600 + Math.floor(((i * 0.3819660112501051) % 1) * 600)
      ),
    []
  );

  useEffect(() => {
    if (visibleLines < TERMINAL_LINES.length) {
      const timer = setTimeout(
        () => setVisibleLines((prev) => prev + 1),
        lineDelays[visibleLines]
      );
      return () => clearTimeout(timer);
    } else {
      // Terminal animation complete — set flag so we show the "waiting" state
      const t = setTimeout(() => setTerminalComplete(true), 600);
      return () => clearTimeout(t);
    }
  }, [visibleLines, lineDelays]);

  // Show elapsed time once terminal is done
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!terminalComplete) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [terminalComplete]);

  return (
    <motion.div
      variants={slideUp}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center w-full"
    >
      <StateBadge step={3} />
      <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
        Analyzing Your Chat
      </h2>
      <p className="text-sm text-nothing-text-secondary mb-8 text-center max-w-md">
        {terminalComplete
          ? "Finalizing your personalized replies..."
          : "Our AI is studying the conversation flow and crafting the perfect responses."}
      </p>

      {/* Terminal */}
      <div className="relative w-full max-w-lg">
        {/* Spinning ring — subtle, doesn't distract */}
        <motion.div
          className="absolute -inset-1 rounded-2xl border pointer-events-none"
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
          style={{
            borderTopColor: terminalComplete
              ? "rgba(34,197,94,0.4)"
              : "rgba(255,0,60,0.4)",
            borderRightColor: "transparent",
            borderBottomColor: "transparent",
            borderLeftColor: "transparent",
          }}
        />
        <div className="relative rounded-xl border border-nothing-border bg-nothing-surface p-6 font-mono text-xs leading-relaxed overflow-hidden">
          <div className="relative z-10 mb-2 flex items-center gap-2 text-nothing-text-tertiary">
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <StatusDot active />
            </motion.span>
            <span>RIZZ_ENGINE // v2.0</span>
            {terminalComplete && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="ml-auto text-[10px] text-nothing-text-tertiary/60"
              >
                {elapsed > 0 && `${elapsed}s elapsed`}
              </motion.span>
            )}
          </div>
          {TERMINAL_LINES.slice(0, visibleLines).map((line, i) => {
            const isLast = i === visibleLines - 1;
            const isComplete = line === "[ COMPLETE ]";
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={`relative z-10 py-0.5 ${
                  isComplete
                    ? "text-nothing-success"
                    : isLast
                    ? "text-nothing-white"
                    : "text-nothing-text-secondary"
                }`}
              >
                <span className="text-nothing-text-tertiary/60">{"> "}</span>
                {line}
                {isLast && !isComplete && (
                  <motion.span
                    className="ml-1 inline-block h-4 w-2 bg-nothing-white"
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  />
                )}
                {isComplete && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500, damping: 15 }}
                    className="ml-2 inline-block"
                  >
                    &#x2714;
                  </motion.span>
                )}
              </motion.div>
            );
          })}

          {/* Post-complete: pulsing dots */}
          {terminalComplete && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="relative z-10 mt-3 flex items-center gap-2 text-nothing-text-tertiary"
            >
              <span className="text-nothing-success text-xs">
                &#x2714; ANALYSIS_COMPLETE
              </span>
              <span className="text-nothing-text-tertiary/40">&mdash;</span>
              <span className="flex items-center gap-1 text-[10px] tracking-wider">
                AWAITING_RESPONSE
                <span className="inline-flex gap-0.5">
                  <motion.span
                    className="inline-block h-1 w-1 rounded-full bg-nothing-text-tertiary"
                    animate={{ opacity: [1, 0.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
                  />
                  <motion.span
                    className="inline-block h-1 w-1 rounded-full bg-nothing-text-tertiary"
                    animate={{ opacity: [1, 0.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                  />
                  <motion.span
                    className="inline-block h-1 w-1 rounded-full bg-nothing-text-tertiary"
                    animate={{ opacity: [1, 0.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
                  />
                </span>
              </span>
            </motion.div>
          )}

          {/* Pre-complete: "PROCESSING" label */}
          {!terminalComplete && visibleLines < TERMINAL_LINES.length && (
            <div className="relative z-10 mt-2 flex items-center gap-1.5 text-nothing-text-tertiary">
              <motion.span
                className="inline-block h-2 w-2 rounded-full bg-neon-red"
                animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              PROCESSING
            </div>
          )}
        </div>
      </div>

      {/* Subtle "please wait" message when terminal is done */}
      {terminalComplete && (
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6 text-[10px] font-mono text-nothing-text-tertiary/60 text-center max-w-xs"
        >
          Your replies are being generated — this usually takes a few more
          seconds.
        </motion.p>
      )}
    </motion.div>
  );
}
