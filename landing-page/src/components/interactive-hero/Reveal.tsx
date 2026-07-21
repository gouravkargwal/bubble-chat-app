"use client";

import React from "react";
import { motion } from "framer-motion";
import { StateBadge } from "./StateBadge";
import { CheckCircledIcon, MobileIcon } from "./icons";
import { slideUp, EASE_OUT } from "./types";
import { APP_URLS } from "@/app/constants";

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

function DownloadAppCTA() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.5, ease: EASE_OUT }}
      className="w-full max-w-lg text-center"
    >
      <p className="text-xs text-nothing-text-secondary mb-4 max-w-sm mx-auto leading-relaxed">
        Get unlimited conversations, all conversation directions, custom hints,
        and coach reasoning in the app.
      </p>

      <motion.a
        href={APP_URLS.googlePlay}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-full bg-neon-red px-8 py-3 text-xs font-bold text-nothing-white transition-all duration-200 hover:bg-red-600"
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.97 }}
      >
        <MobileIcon className="h-3.5 w-3.5" />
        Get the App
      </motion.a>
    </motion.div>
  );
}

function CopyButton({ text, onCopy }: { text: string; onCopy?: () => void }) {
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    if (copied) {
      const t = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(t);
    }
  }, [copied]);

  return (
    <motion.button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        onCopy?.();
      }}
      className={`rounded-md border px-2 py-0.5 text-[10px] font-mono transition-colors ${
        copied
          ? "border-neon-red text-neon-red"
          : "border-nothing-border text-nothing-text-secondary hover:bg-nothing-white/5"
      }`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <span className="flex items-center gap-1">
        {copied ? (
          <svg
            className="h-2.5 w-2.5 text-neon-red"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4.5 12.75l6 6 9-13.5"
            />
          </svg>
        ) : (
          <CheckCircledIcon className="h-2.5 w-2.5" />
        )}
        {copied ? "COPIED!" : "COPY"}
      </span>
    </motion.button>
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
      <h2 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
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
      </div>
    </motion.div>
  );
}

export function Reveal({
  replies,
  isCached = false,
  isRateLimited = false,
  appUrl = APP_URLS.googlePlay,
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

      <h2 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white mb-3 text-center">
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
              <CopyButton text={reply.text} />
            </div>
            <p className="text-sm text-nothing-white">{reply.text}</p>
          </motion.div>
        ))}
      </div>

      {/* Download CTA */}
      <DownloadAppCTA />
    </motion.div>
  );
}
