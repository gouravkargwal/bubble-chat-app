# Cookd Landing Page — cookdai.site

Marketing landing page for Cookd AI Conversation Assistant. Built with Next.js 16 (App Router), Tailwind CSS 4, Framer Motion, and PostHog analytics.

## Stack

- **Framework:** Next.js 16.2.9 (App Router, Turbopack)
- **Styling:** Tailwind CSS 4, custom design tokens
- **Animation:** Framer Motion
- **Analytics:** PostHog (self-hosted, reverse-proxied via `/ingest/*`)
- **Fonts:** Space Grotesk (headings), DM Sans (body)

## Getting Started

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local   # or use .env.production for prod builds

# Start dev server
npm run dev
# → http://localhost:3000
```

## Environment Variables

| Variable                            | Required | Description                                          |
| ----------------------------------- | -------- | ---------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`          | Yes      | Backend API base URL (e.g., `http://localhost:8000`) |
| `NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN` | Yes      | PostHog project token (`phc_...`)                    |
| `NEXT_PUBLIC_POSTHOG_HOST`          | Yes      | PostHog server URL (`https://us.i.posthog.com`)      |

## Domain Configuration

All domain-specific values are in [`src/app/constants.ts`](src/app/constants.ts). Edit **two constants** at the top:

```ts
const APP_DOMAIN = "cookdai.site"; // website, ogImage, iosWaitlist
const EMAIL_DOMAIN = "cookdai.site"; // support@, hello@, legal@
```

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout + PostHog page view tracking
│   ├── page.tsx            # Home page (hero → features → pricing → faq → cta)
│   ├── constants.ts        # All domain config (single source of truth)
│   ├── contact/page.tsx    # Contact form
│   ├── ltd/success/page.tsx # LTD payment success + verification failure
│   ├── privacy/page.tsx    # Privacy policy
│   └── terms/page.tsx      # Terms of service
├── components/
│   ├── PostHogPageView.tsx # Route-based page view capture
│   ├── SectionTracker.tsx  # IntersectionObserver section visibility
│   ├── Header.tsx          # Navigation with CTA tracking
│   ├── CTA.tsx             # Bottom call-to-action section
│   ├── FAQ.tsx             # FAQ with interaction tracking
│   ├── Footer.tsx          # Footer with link tracking
│   └── interactive-hero/   # Lead magnet funnel (dropzone → vibe → gate → reveal)
└── instrumentation-client.ts  # PostHog client init (production only)
```

## PostHog Events

| Event                             | Trigger                                                            |
| --------------------------------- | ------------------------------------------------------------------ |
| `$pageview`                       | Every route change                                                 |
| `section_viewed`                  | User scrolls to Features / Pricing / FAQ / CTA                     |
| `screenshot_uploaded`             | User uploads screenshot in hero                                    |
| `vibe_selected`                   | User picks a conversation direction                                |
| `lead_email_submitted`            | User submits email in gate                                         |
| `replies_revealed`                | AI replies generated successfully                                  |
| `app_download_clicked`            | Any Google Play CTA (header, mobile menu, CTA section, sticky bar) |
| `ltd_checkout_opened`             | LTD checkout modal opens                                           |
| `ltd_payment_initiated`           | User submits LTD payment form                                      |
| `ltd_payment_succeeded`           | Payment confirmed (with `txnid`, `amount`)                         |
| `ltd_payment_verification_failed` | PayU redirect with error                                           |
| `view_pricing_clicked`            | "View Pricing" secondary CTA                                       |
| `faq_opened` / `faq_closed`       | FAQ toggle                                                         |
| `footer_link_clicked`             | Any footer link                                                    |

Events are production-only (disabled in dev via `NODE_ENV` guard).

## Build

```bash
npm run build    # Production build
npm run start    # Start production server
```

## Domain

**Production:** https://cookdai.site
