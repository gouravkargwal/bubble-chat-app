"use client";

import React from "react";
import { motion } from "framer-motion";
import { StateBadge } from "./StateBadge";
import { CheckCircledIcon, MobileIcon } from "./icons";
import { slideUp, EASE_OUT } from "./types";

interface ReplyItem {
  id: string;
  style: string;
  text: string;
}

interface RevealProps {
  replies: ReplyItem[];
  isCached?: boolean;
  isRateLimited?: boolean;
  appUrl?: string;
  onReset?: () => void;
}

function UpsellBlock() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85, y: 30 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay: 0.7, duration: 0.6, ease: EASE_OUT }}
      className="relative w-full max-w-lg overflow-hidden rounded-2xl border-2 border-neon-red bg-gradient-to-br from-nothing-surface to-nothing-black p-8 text-center"
    >
      {/* Conic gradient border animation */}
      <motion.div
        className="absolute inset-0 rounded-2xl pointer-events-none"
        style={{
          background:
            "conic-gradient(from 0deg, transparent, rgba(255,0,60,0.1), transparent, rgba(255,0,60,0.1), transparent)",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute -top-20 -right-20 h-40 w-40 rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(255,0,60,0.3) 0%, transparent 70%)",
        }}
        animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative z-10">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-neon-red/30 bg-neon-red/10 px-3 py-1 text-[10px] font-mono text-neon-red tracking-wider">
          <span>&#x26A1;</span>
          LIMITED TIME
        </div>
        <h3 className="text-2xl font-extrabold text-nothing-white mb-2">
          Lifetime Access
        </h3>
        <p className="text-sm text-nothing-text-secondary mb-6 max-w-sm mx-auto">
          Unlimited replies, all conversation directions, custom hints,
          chemistry tracking, and more.
        </p>

        <div className="mb-6 flex items-baseline justify-center gap-1">
          <span className="text-5xl font-extrabold text-nothing-white">
            &#x20B9;999
          </span>
          <span className="text-sm font-mono text-nothing-text-tertiary line-through">
            &#x20B9;4,799
          </span>
        </div>

        <motion.a
          href="https://play.google.com/store/apps/details?id=com.cookd.mobile"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-neon-red px-10 py-3.5 text-sm font-bold text-nothing-white transition-all duration-300"
          whileHover={{
            scale: 1.04,
            boxShadow: "0 0 40px rgba(255,0,60,0.4)",
          }}
          whileTap={{ scale: 0.97 }}
        >
          <MobileIcon className="h-4 w-4" />
          Get the App
        </motion.a>

        <div className="mt-4 flex items-center justify-center gap-4 text-[10px] font-mono text-nothing-text-tertiary">
          <span>&#x2726; No subscription</span>
          <span>&#x2726; Lifetime updates</span>
          <span>&#x2726; Cancel anytime</span>
        </div>
      </div>
    </motion.div>
  );
}

function RateLimitedBlock({ appUrl }: { appUrl: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE_OUT }}
      className="flex flex-col items-center w-full"
    >
      <StateBadge step={5} />
      <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
        Free Demo Used! 🎯
      </h2>
      <p className="text-sm text-nothing-text-secondary mb-8 text-center max-w-md">
        You've used your free demo for today. Download the app to get unlimited
        AI-powered replies, custom coaching, and more.
      </p>

      <motion.a
        href={appUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-full bg-neon-red px-10 py-3.5 text-sm font-bold text-nothing-white transition-all duration-300"
        whileHover={{
          scale: 1.04,
          boxShadow: "0 0 40px rgba(255,0,60,0.4)",
        }}
        whileTap={{ scale: 0.97 }}
      >
        <MobileIcon className="h-4 w-4" />
        Get the App
      </motion.a>

      <div className="mt-6 flex items-center justify-center gap-4 text-[10px] font-mono text-nothing-text-tertiary">
        <span>&#x2726; Unlimited replies</span>
        <span>&#x2726; Custom coaching</span>
        <span>&#x2726; Chemistry tracking</span>
      </div>
    </motion.div>
  );
}

export function Reveal({
  replies,
  isCached = false,
  isRateLimited = false,
  appUrl = "https://play.google.com/store/apps/details?id=com.cookd.mobile",
  onReset,
}: RevealProps) {
  // Rate limited state — show download prompt
  if (isRateLimited || replies.length === 0) {
    return <RateLimitedBlock appUrl={appUrl} />;
  }

  return (
    <motion.div
      variants={slideUp}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center w-full"
    >
      <StateBadge step={5} />

      {isCached && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-text-tertiary/30 bg-nothing-surface/50 px-4 py-1.5 text-[10px] font-mono text-nothing-text-tertiary tracking-wider"
        >
          <span>&#x1F504;</span>
          You already tried this — here's your result!
        </motion.div>
      )}

      <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
        Your Replies Are Ready &#x1F3AF;
      </h2>
      <p className="text-sm text-nothing-text-secondary mb-8 text-center max-w-md">
        Full access. No blur. No limits.
      </p>

      {/* Unlocked replies */}
      <div className="w-full max-w-lg space-y-3 mb-10">
        {replies.map((reply, i) => (
          <motion.div
            key={reply.id}
            initial={{ opacity: 0, scale: 0.85, filter: "blur(12px)" }}
            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
            transition={{ delay: i * 0.15, duration: 0.7, ease: EASE_OUT }}
            className="rounded-xl border border-nothing-border bg-nothing-surface p-4"
          >
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-nothing-text-tertiary">
                {reply.style}
              </span>
              <motion.button
                onClick={() => navigator.clipboard.writeText(reply.text)}
                className="rounded-md border border-nothing-border px-2 py-0.5 text-[10px] font-mono text-nothing-text-secondary hover:bg-nothing-white/5 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <span className="flex items-center gap-1">
                  <CheckCircledIcon className="h-2.5 w-2.5" />
                  COPY
                </span>
              </motion.button>
            </div>
            <p className="text-sm text-nothing-white">{reply.text}</p>
          </motion.div>
        ))}
      </div>

      {/* Upsell */}
      <UpsellBlock />

      {onReset && (
        <motion.button
          onClick={onReset}
          className="mt-6 text-xs font-mono text-nothing-text-tertiary underline underline-offset-4 hover:text-nothing-text-secondary transition-colors"
          whileHover={{ scale: 1.02, letterSpacing: "0.05em" }}
          whileTap={{ scale: 0.98 }}
        >
          TRY AGAIN WITH A NEW SCREENSHOT
        </motion.button>
      )}
    </motion.div>
  );
}
