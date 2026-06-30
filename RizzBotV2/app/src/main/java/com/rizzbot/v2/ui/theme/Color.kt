package com.rizzbot.v2.ui.theme

import androidx.compose.ui.graphics.Color

// ── Nothing OS / Teenage Engineering-inspired palette ──
// Strict dark mode: pitch black background, pure white text.
// Exactly one accent color (vibrant neon red) used strictly for the primary 'Generate' action.
// No drop shadows. Hard, crisp 1dp borders. Monospaced labels. Bold geometric titles.

/** Pitch black background — no compromises. */
val NothingBlack = Color(0xFF000000)

/** Pure white for all primary text. */
val NothingWhite = Color(0xFFFFFFFF)

/** Vibrant neon red — the *only* accent color, reserved for the primary Generate CTA. */
val NeonRed = Color(0xFFFF003C)

/** Near-black surface for cards and elevated elements (subtle distinction from pitch black). */
val NothingSurface = Color(0xFF050505)

/** Subtle border color (10% white) for card outlines. */
val NothingBorder = Color(0x1AFFFFFF)

/** Muted secondary text (45% white) for labels and metadata. */
val NothingTextSecondary = Color(0x73FFFFFF)

/** Tertiary/muted metadata text (30% white). */
val NothingTextTertiary = Color(0x4DFFFFFF)

/** Success green — kept minimal, used only for passing badges. */
val NothingSuccess = Color(0xFF00FF66)

/** Error/delete red — distinct from neon accent. */
val NothingError = Color(0xFFFF3355)
