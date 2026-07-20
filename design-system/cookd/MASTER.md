# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Cookd
**Last Updated:** 2026-07-20
**Category:** Dating App — AI Conversation Assistant

---

## Design Philosophy

**Nothing OS / Teenage Engineering-inspired.** Strict dark mode with pitch black backgrounds, pure white text, and exactly one accent color (vibrant neon red) used strictly for the primary action. No drop shadows — hard, crisp 1dp borders replace them. Monospaced labels for metadata. Bold geometric titles. Static and precise, not bouncy.

---

## Color Palette

### Dark Mode (default)

| Role | Hex | CSS Variable | Android Token | Usage |
|------|-----|-------------|---------------|-------|
| **Background** | `#000000` | `--color-brand-black` | `NothingBlack` | App / page background |
| **Surface** | `#0a0a0a` | `--color-brand-surface` | `NothingSurface` `#050505` | Cards, elevated elements |
| **Primary Text** | `#ffffff` | `--color-brand-white` | `NothingWhite` | All primary text |
| **Primary Action** | `#e11d48` | `--color-brand-primary` | `NeonRed` `#FF003C` | Generate CTA, links, accents |
| **Secondary CTA** | `#2563eb` | `--color-brand-accent` | — | Blue CTAs on landing page only |
| **Border** | `rgba(255,255,255,0.1)` | `--color-brand-border` | `NothingBorder` `0x1AFFFFFF` | Card outlines, dividers |
| **Muted Text** | `rgba(255,255,255,0.45)` | `--color-brand-muted` | `NothingTextSecondary` `0x73FFFFFF` | Labels, secondary info |
| **Subtle Text** | `rgba(255,255,255,0.3)` | `--color-brand-subtle` | `NothingTextTertiary` `0x4DFFFFFF` | Tertiary metadata |
| **Success** | `#00ff66` | `--color-brand-success` | `NothingSuccess` `0xFF00FF66` | Passing badges, success states |
| **Error** | `#ff3355` | `--color-brand-error` | `NothingError` `0xFFFF3355` | Error states, destructive actions |

### Light Mode

Applied via `@media (prefers-color-scheme: light)` — only on the landing page (web). The Android app is dark mode only.

| Role | Hex | Notes |
|------|-----|-------|
| Background | `#ffffff` | Inverted from dark |
| Surface | `#fff1f2` | Rose-tinted light surface |
| Primary Text | `#111111` | Near-black |
| Primary Action | `#be123c` | Darker rose for light bg contrast |
| Secondary CTA | `#1d4ed8` | Darker blue |
| Border | `rgba(0,0,0,0.1)` | Dark border variant |
| Muted Text | `rgba(0,0,0,0.65)` | WCAG AA compliant |
| Subtle Text | `rgba(0,0,0,0.4)` | |
| Success | `#059669` | Darker green |
| Error | `#dc2626` | Darker red |

### Legacy Alias Tokens (backward-compatible)

These exist in the landing page CSS for migration compatibility:

| Alias | Maps To |
|-------|---------|
| `--color-nothing-black` | `--color-brand-black` |
| `--color-nothing-white` | `--color-brand-white` |
| `--color-neon-red` | `--color-brand-primary` |
| `--color-nothing-surface` | `--color-brand-surface` |
| `--color-nothing-border` | `--color-brand-border` |
| `--color-nothing-text-secondary` | `--color-brand-muted` |
| `--color-nothing-text-tertiary` | `--color-brand-subtle` |
| `--color-nothing-success` | `--color-brand-success` |
| `--color-nothing-error` | `--color-brand-error` |

---

## Typography

### Web (Landing Page)

| Role | Font | CSS Variable | Weights Used |
|------|------|-------------|--------------|
| **Heading** | Space Grotesk | `--font-heading` | 400, 500, 600, 700 |
| **Body** | DM Sans | `--font-sans` | 400, 500, 700 |
| **Mono** | SF Mono / JetBrains Mono / Fira Code | `--font-mono` | — |

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
```

### Android App

| Role | Font | Notes |
|------|------|-------|
| **All text** | Plus Jakarta Sans | 5 weights: Regular, Medium, SemiBold, Bold, ExtraBold |
| **Hero / Display** | ExtraBold, negative letter-spacing `-0.75px` to `-1px` | Tight, geometric |
| **Labels** | Medium weight, wide tracking `0.5–0.8sp` | Monospaced feel |

---

## Spacing Variables

### Web (Tailwind)

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-screen` | `24px` | Standard horizontal padding |
| `--spacing-section` | `48px` | Gap between major sections |
| `--spacing-card` | `16px` | Padding inside cards |

### Android App

| Token | Value | Usage |
|-------|-------|-------|
| `screenPadding` | `24dp` | Standard horizontal padding |
| `sectionSpacing` | `28dp` | Between major sections |
| `cardPadding` | `16dp` | Inside cards |
| `elementGap` | `12dp` | Between elements in a row |
| `textGap` | `4dp` | Between stacked text |
| `minTouchTarget` | `48dp` | Minimum touch target size |
| `borderThickness` | `1dp` | Default border width |

### Legacy Spacing (pre-migration — do not use for new work)

| Token | Value |
|-------|-------|
| `--space-xs` | `4px` / `0.25rem` |
| `--space-sm` | `8px` / `0.5rem` |
| `--space-md` | `16px` / `1rem` |
| `--space-lg` | `24px` / `1.5rem` |
| `--space-xl` | `32px` / `2rem` |
| `--space-2xl` | `48px` / `3rem` |
| `--space-3xl` | `64px` / `4rem` |

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| Card | `12px` / `12dp` | Cards, panels |
| Pill | `9999px` / `999dp` | Buttons, badges |
| Small | `4px` | Minor elements |
| Android card | `10dp` | Secondary card shape |

**Rule:** No rounded corners above `12dp` / `12px`. Sharp, hard lines. Pill radius is the only exception.

---

## Shadows

**Do NOT use shadows.** The Nothing OS-inspired design uses hard borders (`1px` / `1dp`) instead of drop shadows. All existing shadow tokens are legacy from a previous design direction:

| Token | ~~Value~~ | Status |
|-------|-----------|--------|
| `--shadow-sm` | ~~0 1px 2px rgba(0,0,0,0.05)~~ | **Deprecated** — use borders |
| `--shadow-md` | ~~0 4px 6px rgba(0,0,0,0.1)~~ | **Deprecated** — use borders |
| `--shadow-lg` | ~~0 10px 15px rgba(0,0,0,0.1)~~ | **Deprecated** — use borders |
| `--shadow-xl` | ~~0 20px 25px rgba(0,0,0,0.15)~~ | **Deprecated** — use borders |

---

## Component Specs

### Buttons

```css
/* Primary CTA (Generate / Subscribe) */
.btn-primary {
  background: #e11d48;  /* --color-brand-primary / NeonRed */
  color: #ffffff;
  padding: 12px 24px;
  border-radius: 9999px;  /* pill */
  font-weight: 700;  /* bold */
  border: none;
  cursor: pointer;
  transition: all 200ms ease;
}

.btn-primary:hover {
  opacity: 0.9;
  box-shadow: 0 0 30px rgba(225, 29, 72, 0.25);  /* subtle neon glow on web only */
}

/* Secondary / Outline Button */
.btn-secondary {
  background: transparent;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 12px 24px;
  border-radius: 9999px;
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Android: White filled button with black text */
/* Button(colors = ButtonDefaults.buttonColors(containerColor = NothingWhite)) */
/* Text("Label", color = NothingBlack) */
```

### Cards

```css
.card {
  background: #0a0a0a;  /* --color-brand-surface */
  border: 1px solid rgba(255, 255, 255, 0.1);  /* hard border, no shadow */
  border-radius: 12px;
  padding: 24px;
  transition: all 200ms ease;
}

.card:hover {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.2);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: #0a0a0a;
  border-radius: 8px;
  font-size: 16px;
  color: #ffffff;
  outline: none;
  transition: border-color 200ms ease;
}

.input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.input:focus {
  border-color: #e11d48;
}
```

### Modals / Overlay Panels

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.7);  /* scrim */
}

.modal {
  background: #0a0a0a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 32px;
  max-width: 500px;
  width: 90%;
}
```

---

## Animations

| Token | Value | Usage |
|-------|-------|-------|
| `--ease-out-expo` | `cubic-bezier(0.19, 1, 0.22, 1)` | Standard easing |
| Duration | `200–300ms` | All transitions |
| Neon pulse | 3s infinite | CTA glow animation |
| Fade in | 0.6s ease-out-expo | Entrance animations |

**Key animation classes (web):**
- `animate-neon-pulse` — Subtle glow oscillation on CTAs
- `animate-fade-in` — Entrance with translateY(12px) → 0
- `animate-blink` — Opacity blink for status indicators
- `animate-cursor` — Terminal cursor blink
- `animate-gradient-x` — 6s gradient sweep for backgrounds

---

## Style Guidelines

**Style:** Nothing OS / Teenage Engineering minimalism — dark brutalist

**Keywords:** Pitch black, pure white, neon red accent, hard borders, monospaced labels, bold geometric titles, dot-matrix rings, static, precise, industrial

**Key Effects:**
- Large sections with 48px+ gaps
- Hard 1px borders replace shadows everywhere
- Exactly one accent color (neon red) reserved for primary action
- Dot-matrix / Glyph interface elements (Android bubble)
- Neon glow on primary CTAs (web only)
- Monospaced metadata labels

### Page Pattern (Landing Page)

**Pattern Name:** App Store Style Landing

- **Conversion Strategy:** Show real app screenshots. Ratings. QR code for mobile. Platform-specific CTAs.
- **CTA Placement:** Download buttons (Google Play) prominent throughout
- **Section Order:** 1. Hero with phone mockup, 2. Screenshots carousel, 3. Features grid, 4. How it works, 5. Pricing, 6. FAQ, 7. Footer

---

## Cross-Platform Discrepancies (Needs Alignment)

These are differences between the Android app and landing page that should be reconciled in a future update:

| Token | Landing Page (Web) | Android App | Recommended Canonical |
|-------|-------------------|-------------|-----------------------|
| **Primary accent** | `#e11d48` (rose) | `#FF003C` (neon red) | `#e11d48` (rose) — or decide on one |
| **Surface** | `#0a0a0a` | `#050505` | `#0a0a0a` (visually near-identical; minimal impact) |
| **Heading font** | Space Grotesk | Plus Jakarta Sans | Platform-native — accept difference |
| **Body font** | DM Sans | Plus Jakarta Sans | Platform-native — accept difference |
| **Mono stack** | SF Mono / JetBrains Mono / Fira Code | System monospace | Platform-native |
| **Light mode** | Supported via `prefers-color-scheme` | Dark mode only | Accept difference |
| **Card radius** | `12px` | `10dp` (secondary), `12dp` (primary) | Align to `12px`/`12dp` |

---

## Anti-Patterns (Do NOT Use)

- ❌ **Multiple accent colors** — Exactly one accent (neon red). Blue is secondary CTA on web only.
- ❌ **Drop shadows** — Use hard borders instead
- ❌ **Generic profiles / stock photography** — Show real app screenshots
- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing `cursor:pointer`** — All clickable elements must have it
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y
- ❌ **Rounded corners above 12dp** — Except pill buttons
- ❌ **Idle animations / pulsing** — Nothing OS is static and precise (except loading states)

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] Colors match the dark mode palette (pitch black bg, white text, neon red accent)
- [ ] No drop shadows — hard borders used instead
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum (web only)
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
- [ ] Primary CTA uses neon red accent exclusively
- [ ] Border radius does not exceed 12dp (except pills)
