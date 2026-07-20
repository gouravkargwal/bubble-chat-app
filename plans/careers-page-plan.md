# Careers Page — Implementation Plan

## Overview

Add a `/careers` page to the Cookd landing page for hiring a **Media Marketing Manager Intern** (₹5,000 stipend, task-based Google Form application). The page is linked **only from the footer** in a new "Company" section — no header nav link.

## Strategy Alignment

As discussed, this doubles as:
1. **Genuine hiring** for a Media Manager role
2. **SEO + dwell-time boost** — task-based form forces applicants to download the app, find a bug/UX friction point, and create a TikTok hook, generating high-quality engagement signals

## Files to Create/Modify

### 1. [`landing-page/src/app/constants.ts`](landing-page/src/app/constants.ts) — Add Google Form URL

Add a `GOOGLE_FORM_URL` constant for the application form:
```ts
export const CAREERS = {
  mediaManagerForm: "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform",
} as const;
```

### 2. [`landing-page/src/app/careers/page.tsx`](landing-page/src/app/careers/page.tsx) — New Careers page (Create)

**Route:** `/careers`

**Structure (matching existing page patterns from contact + terms):**
- `"use client"` — same as contact/terms
- Import `Header`, `Footer`, `StatusDot`, `AnimatedSection`, `motion`
- Use `head` with proper `<title>` and `<meta description>`

**Sections:**

1. **Hero Section** — same animated gradient/glow background pattern as contact page
   - Job title: "Media Marketing Manager Intern"
   - Stipend: ₹5,000/month
   - Tagline: "Task-based application — show us what you've got"
   - StatusDot + "Now Hiring" badge

2. **About the Role** — brief JD
   - Own Cookd's social media presence (TikTok, Instagram, Twitter/X)
   - Create viral hooks, trend-jack, and grow organic reach
   - Collaborate with product on brand voice
   - Target: Gen Z/Millennial dating app users

3. **Task-Based Application** (the high-dwell-time strategy)
   - **The Task:** Download Cookd from Google Play, use it to generate a "rizz" response for a dating app conversation, and create a **15-second TikTok/Reel hook** featuring the result. Show us how you'd make this go viral.
   - Submit via Google Form below

4. **Embedded Google Form** — iframe or large CTA button linking to the form
   - Since Google Forms doesn't always embed well in iframes (CORS), use a clean CTA button: "Apply Now — Fill the Google Form"

5. **Footer** — already rendered via `<Footer />`

### 3. [`landing-page/src/components/Footer.tsx`](landing-page/src/components/Footer.tsx) — Update footer links

Add a **"Company"** section to `FOOTER_LINKS` with a **"Careers"** link:
```ts
const FOOTER_LINKS = {
  Product: [ ... ],
  Company: [
    { label: "Careers", href: "/careers" },
  ],
  Legal: [ ... ],
  Connect: [ ... ],
};
```

**No changes to Header.tsx** — per requirement, careers link is footer-only.

## Design Tokens Used

All from existing design system ([`globals.css`](landing-page/src/app/globals.css)):
- Colors: `brand-black`, `brand-white`, `brand-primary` (rose #E11D48), `brand-muted`, `brand-border`
- Typography: `font-heading` (Space Grotesk), `font-sans` (DM Sans), `font-mono`
- Animations: `framer-motion` with `EASE_OUT = [0.16, 1, 0.3, 1]`
- Grid pattern background from contact page (radial + dotted grid)

## Execution Order

1. Add `GOOGLE_FORM_URL` to [`constants.ts`](landing-page/src/app/constants.ts)
2. Create [`careers/page.tsx`](landing-page/src/app/careers/page.tsx)
3. Update [`Footer.tsx`](landing-page/src/components/Footer.tsx) — add "Company" section with "Careers"

## Page Flow Diagram

```mermaid
flowchart LR
    A[Footer: Company > Careers] --> B[/careers page]
    B --> C[Hero: Job Title + Stipend]
    C --> D[About the Role]
    D --> E[Task Instructions]
    E --> F[Google Form CTA]
    F --> G[External Google Form]
```

## Future Considerations

- When you have the actual Google Form ID, replace the placeholder in [`constants.ts`](landing-page/src/app/constants.ts#L1)
- Can add server-side submit tracking via PostHog if the form is embedded (though cross-origin tracking is limited with Google Forms)
- If Google Form embed works, consider adding PostHog `capture` on the "Apply Now" button click
