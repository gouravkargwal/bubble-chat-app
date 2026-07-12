"use client";

import type { Variants } from "framer-motion";

// ── Shared types ──
export interface ReplyItem {
  id: string;
  style: string;
  text: string;
}

// ── State Machine ──
export type ComponentState =
  | "idle"
  | "vibe_check"
  | "processing"
  | "gate"
  | "reveal";

// ── Data Models ──
export interface VibeOption {
  id: string;
  label: string;
  description: string;
  shortcut: string;
}

// ── Shared Easing ──
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// ── Shared Variants ──
export const slideUp: Variants = {
  initial: { opacity: 0, y: 24 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: EASE_OUT },
  },
  exit: {
    opacity: 0,
    y: -16,
    transition: { duration: 0.3, ease: EASE_OUT },
  },
};

// ── Constants ──
// Picked from the 7 real backend directions (models.py):
// OPENER, QUICK_REPLY, TEASE, GET_NUMBER, ASK_OUT, REVIVE_CHAT, CHANGE_TOPIC
// Focused on three core directions: Opener, Tease & Keep Playful
export const VIBE_OPTIONS: VibeOption[] = [
  {
    id: "OPENER",
    label: "First Message",
    description: "Craft the perfect opener to break the ice.",
    shortcut: "CTRL+1",
  },
  {
    id: "TEASE",
    label: "Tease",
    description: "Playful push-pull that builds attraction.",
    shortcut: "CTRL+2",
  },
  {
    id: "KEEP_PLAYFUL",
    label: "Keep It Playful",
    description: "Light, flirty energy that keeps the spark alive.",
    shortcut: "CTRL+3",
  },
];

export const TERMINAL_LINES = [
  "[ INITIALIZING_VISION_ENGINE... ]",
  "[ ANALYZING_CONTEXT... ]",
  "[ DECODING_CHAT_PATTERNS... ]",
  "[ SELECTING_RESPONSE_VECTOR... ]",
  "[ GENERATING_REPLIES... ]",
  "[ COMPLETE ]",
];

// ── API ──
// NOTE: Use API_URLS.leadMagnet from @/app/constants instead.
// This file kept for type definitions only.
export const API_BASE = "";
