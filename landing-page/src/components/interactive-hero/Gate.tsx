"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { StateBadge } from "./StateBadge";
import { ArrowRightIcon, LockIcon } from "./icons";
import { slideUp, EASE_OUT } from "./types";

interface GateProps {
  onSubmit: (email: string) => Promise<void>;
  error: string | null;
}

/* ── Style labels matching Reveal card format ── */
const PREVIEW_CARDS = [
  { id: "p1", label: "Playful Tease" },
  { id: "p2", label: "Warm & Genuine" },
  { id: "p3", label: "Keep It Playful" },
];

/* ── Blurred preview card (matches the Reveal card design but blurred) ── */
function BlurredCard({
  label,
  index,
}: {
  label: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.08, duration: 0.5, ease: EASE_OUT }}
      className="relative rounded-xl border border-nothing-border bg-nothing-surface p-4 overflow-hidden select-none"
    >
      {/* Style label — visible to show the format */}
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-widest text-nothing-text-tertiary">
          {label}
        </span>
      </div>

      {/* Blurred content */}
      <div className="relative">
        <p className="text-sm text-nothing-white blur-sm leading-relaxed select-none">
          Haha you&rsquo;re literally impossible to resist, you know that? 😏
          Okay but real talk — you just made my whole day.
        </p>
      </div>

      {/* Lock overlay */}
      <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-nothing-black/20 backdrop-blur-[0.5px]">
        <motion.div
          className="flex flex-col items-center gap-1"
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        >
          <LockIcon className="h-5 w-5 text-nothing-text-tertiary" />
          <span className="text-[9px] font-mono text-nothing-text-tertiary tracking-widest">
            LOCKED
          </span>
        </motion.div>
      </div>
    </motion.div>
  );
}

export function Gate({ onSubmit, error: apiError }: GateProps) {
  const [email, setEmail] = useState("");
  const [validationError, setValidationError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setValidationError("Enter a valid email address");
      return;
    }
    setValidationError("");
    onSubmit(trimmed);
  };

  const displayError = validationError || apiError;

  return (
    <motion.div
      variants={slideUp}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center w-full"
    >
      <StateBadge step={4} />

      <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
        Preview Your Replies
      </h2>
      <p className="text-sm text-nothing-text-secondary mb-6 text-center max-w-md">
        Enter your email and our AI will craft personalized replies for your conversation.
      </p>

      {/* ── Blurred preview cards ── */}
      <div className="w-full max-w-lg space-y-3 mb-6">
        {PREVIEW_CARDS.map((card, i) => (
          <BlurredCard key={card.id} label={card.label} index={i} />
        ))}
      </div>

      {/* ── "Unlock" prompt ── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.4, ease: EASE_OUT }}
        className="mb-6 w-full max-w-lg text-center"
      >
        <div className="inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface/50 px-4 py-1.5 text-[10px] font-mono text-nothing-text-tertiary tracking-wider">
          <LockIcon className="h-3 w-3" />
          ENTER EMAIL TO UNLOCK FULL REPLIES
        </div>
      </motion.div>

      {/* ── Email form ── */}
      <motion.form
        onSubmit={handleSubmit}
        className="w-full max-w-lg relative"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5, ease: EASE_OUT }}
      >
        <div className="flex items-center gap-2 rounded-xl border border-nothing-border bg-nothing-surface p-1.5 transition-all duration-200 focus-within:border-neon-red focus-within:ring-1 focus-within:ring-neon-red/30">
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setValidationError("");
            }}
            placeholder="your@email.com"
            className="flex-1 bg-transparent px-3 py-2.5 text-sm text-nothing-white outline-none placeholder:text-nothing-text-tertiary font-mono"
          />
          <motion.button
            type="submit"
            className="inline-flex items-center gap-1.5 rounded-lg bg-neon-red px-5 py-2.5 text-xs font-bold text-nothing-white transition-all duration-200 hover:shadow-[0_0_20px_rgba(255,0,60,0.25)]"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Unlock Replies
            <ArrowRightIcon className="h-3.5 w-3.5" />
          </motion.button>
        </div>
        {displayError && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-2 text-xs font-mono text-neon-red"
          >
            {">"} ERROR: {displayError}
          </motion.p>
        )}
        <p className="mt-3 text-center text-[10px] font-mono text-nothing-text-tertiary tracking-wider">
          No spam. Unsubscribe anytime. &#x1F54A;&#xFE0F;
        </p>
      </motion.form>
    </motion.div>
  );
}
