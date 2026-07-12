"use client";

import { motion } from "framer-motion";
import { StatusDot } from "../Logo";
import { EASE_OUT } from "./types";

interface StateBadgeProps {
  step: number;
}

const STEP_LABELS = ["TRY IT", "VIBE", "PROCESS", "UNLOCK", "REVEAL"];

export function StateBadge({ step }: StateBadgeProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE_OUT }}
      className="mb-5 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider"
    >
      <StatusDot active={step < 5} />
      <span>
        STEP {step}/5 &bull; {STEP_LABELS[step - 1]}
      </span>
    </motion.div>
  );
}
