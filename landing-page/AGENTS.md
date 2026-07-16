<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

<!-- END:nextjs-agent-rules -->

# Cookd Landing Page — Agent Reference

## Overview

Next.js 15+ app router landing page for Cookd AI Dating Coach at [cookdai.site](https://cookdai.site).

## Key Architecture

```
app/
├── layout.tsx       # Root layout: fonts (Space Grotesk + DM Sans), JSON-LD (WebApp + FAQ + Breadcrumb),
│                    # PostHog analytics, Clerk auth provider, metadata
├── page.tsx         # Server component → ClientShell (all interactive state)
├── admin/page.tsx   # Admin dashboard: Remotion video pipeline (candidates, renders, publish)
├── blog/
│   ├── page.tsx     # Blog listing (reads BLOG_ARTICLES from metadata.ts)
│   ├── [slug]/page.tsx  # Individual blog post (static generation)
│   └── metadata.ts  # 6 articles with full body text + SEO metadata
├── contact/page.tsx # Contact form (mailto fallback) + FAQ accordion
├── ltd/success/ + /failure/  # LTD checkout result pages
├── privacy/ + terms/ + child-safety/ + delete-account/  # Legal pages
├── sitemap.ts       # Auto-generated sitemap with blog slugs
├── robots.ts        # Allow all, disallow /ltd/*
└── api/
    ├── admin/[...path]/route.ts  # BFF proxy to backend admin endpoints
    └── render-video/route.ts     # Remotion render trigger
```

## Components

| Component          | Purpose                                                                      |
| ------------------ | ---------------------------------------------------------------------------- |
| `ClientShell`      | Main client wrapper — lazy-loads InteractiveHero                             |
| `InteractiveHero`  | Lead magnet: dropzone → upload → processing → reveal                         |
| `Features`         | 6 feature cards with hover animations                                        |
| `Pricing`          | 3 plans (Crush/Match/LTD) + scarcity counter + LTD modal                     |
| `LtdCheckoutModal` | PayU checkout iframe                                                         |
| `CTA`              | Bottom CTA with referral callout                                             |
| `Header`/`Footer`  | Navigation                                                                   |
| `Testimonials`     | User testimonials carousel                                                   |
| `FAQ`              | FAQ accordion section                                                        |
| `admin/*`          | Video pipeline dashboard (CandidatesTab, RenderedTab, PostWizard, FilterBar) |

## SEO & Structured Data

- JSON-LD: WebApplication, BreadcrumbList, FAQPage (all in layout.tsx)
- OpenGraph + Twitter cards configured
- Sitemap auto-generates from static routes + blog slugs
- Robots.txt blocks `/ltd/*` from indexing

## Analytics

- PostHog via `posthog-js` (client-side) + `posthog-server` (lib)
- Events tracked: pricing_plan_cta_clicked, app_download_clicked, ltd_checkout_opened, contact_form_submitted, view_pricing_clicked
- SectionTracker + PostHogPageView for scroll + page views

## Environment

Key vars in `.env.local`:

- `NEXT_PUBLIC_API_BASE_URL` — backend API URL
- `NEXT_PUBLIC_POSTHOG_KEY` — PostHog project key
- `CLERK_SECRET_KEY` + `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` — Clerk for admin auth

## Build & Run

```bash
cd landing-page
npm run dev      # Local dev
npm run build    # Production build
```
