"use client";

import React from "react";
import { motion } from "framer-motion";
import { StateBadge } from "./StateBadge";
import { ArrowRightIcon } from "./icons";
import { VIBE_OPTIONS, slideUp, EASE_OUT } from "./types";

interface VibeCheckProps {
  onSelect: (id: string) => void;
}

export function VibeCheck({ onSelect }: VibeCheckProps) {
  return (
    <motion.div
      variants={slideUp}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center w-full"
    >
      <StateBadge step={2} />
      <h2 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
        Pick a direction
      </h2>
      <p className="text-sm text-nothing-text-secondary mb-8 text-center max-w-md">
        Each direction tunes the AI to match your goal. Choose the one that fits
        the situation.
      </p>

      <div
        className="grid w-full max-w-lg gap-2.5"
        role="radiogroup"
        aria-label="Conversation direction"
      >
        {VIBE_OPTIONS.map((vibe, i) => (
          <motion.button
            key={vibe.id}
            onClick={() => onSelect(vibe.id)}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: 0.15 + i * 0.08,
              duration: 0.4,
              ease: EASE_OUT,
            }}
            className="group flex items-center gap-4 rounded-xl border border-nothing-border bg-nothing-surface/50 p-4 text-left transition-all duration-200 hover:border-neon-red/50 hover:bg-neon-red/[0.03]"
            whileHover={{ scale: 1.01, x: 4 }}
            whileTap={{ scale: 0.98 }}
            role="radio"
            aria-checked={false}
            aria-label={`Select ${vibe.label}: ${vibe.description}`}
          >
            <span className="flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-lg border border-nothing-border bg-nothing-black text-[10px] font-mono text-nothing-text-tertiary tracking-wider group-hover:border-neon-red/30 group-hover:text-neon-red transition-colors">
              {vibe.shortcut}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-nothing-white group-hover:text-neon-red transition-colors">
                {vibe.label}
              </p>
              <p className="mt-0.5 text-xs text-nothing-text-secondary leading-relaxed">
                {vibe.description}
              </p>
            </div>
            <ArrowRightIcon className="h-4 w-4 flex-shrink-0 text-nothing-text-tertiary group-hover:text-neon-red transition-colors" />
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
