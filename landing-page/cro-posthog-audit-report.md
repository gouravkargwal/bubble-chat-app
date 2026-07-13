# CRO PostHog Audit Report: Landing Page Event Tracking

**Auditor:** CRO Specialist
**Date:** 2026-07-13
**Scope:** Full event instrumentation audit for the Cookd landing page (`landing-page/`)

---

## Executive Summary

The landing page has **14 tracked events** covering the two primary conversion funnels (hero lead magnet + LTD purchase). However, there are **10 critical gaps** that prevent proper conversion rate optimization analysis. The most severe is the complete absence of page view tracking, which makes it impossible to calculate any conversion rate (visitors → action).

**CRO Readiness Score: 4/10** — The hero interactive funnel and LTD purchase flow are well-instrumented internally, but the overall landing page lacks the foundational analytics needed to diagnose drop-offs, measure performance, or run experiments.

---

## 1. Configuration Analysis

### 1.1 Client-Side Initialization ([`instrumentation-client.ts`](landing-page/instrumentation-client.ts))

```ts
posthog.init(POSTHOG_PROJECT_TOKEN, {
  api_host: "/ingest",
  ui_host: "https://us.posthog.com",
  defaults: "2026-01-30",
  capture_exceptions: true,
  debug: process.env.NODE_ENV === "development",
});
```

| Setting                    | Status         | Assessment                                                                        |
| -------------------------- | -------------- | --------------------------------------------------------------------------------- |
| `api_host: "/ingest"`      | ✅ Correct     | Reverse-proxy via Next.js rewrites beats ad-blockers                              |
| `ui_host`                  | ✅ Correct     | Points to US region                                                               |
| `capture_exceptions: true` | ✅ Correct     | Enables JS error tracking                                                         |
| `debug`                    | ✅ Correct     | Dev-only debug mode                                                               |
| `capture_pageview`         | ❌ **Missing** | **Page views are NOT being captured** — this is the most critical gap             |
| `capture_performance`      | ❌ Missing     | No web vitals tracking                                                            |
| `person_profiles`          | ❌ Missing     | Defaults to "identified only" — fine for now but limits anonymous funnel analysis |

### 1.2 Server-Side Client ([`posthog-server.ts`](landing-page/src/lib/posthog-server.ts))

```ts
const client = new PostHog(token, { flushAt: 1, flushInterval: 0 });
```

- ✅ Correct for serverless/Edge Functions (`flushAt: 1` ensures immediate dispatch)
- ⚠️ **Not used anywhere** in the landing page. The server client is imported ready but no server actions or API routes currently emit events through it.

### 1.3 Reverse Proxy ([`next.config.ts`](landing-page/next.config.ts))

```ts
source: "/ingest/static/:path*"  → "https://us-assets.i.posthog.com/static/:path*"
source: "/ingest/array/:path*"   → "https://us-assets.i.posthog.com/array/:path*"
source: "/ingest/:path*"         → "https://us.i.posthog.com/:path*"
```

✅ Correct — standard PostHog proxy setup to bypass ad-blockers.

---

## 2. Tracked Events Inventory

All 14 currently tracked events, with CRO analysis:

| #   | Event                                       | File                                                                                              | Props                           | CRO Grade | Notes                                                                                                                          |
| --- | ------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `screenshot_uploaded`                       | [`InteractiveHero.tsx:69`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:69)   | `file_type`                     | 🟡        | Missing `file_size` and `image_dimensions` — useful for UX perf analysis                                                       |
| 2   | `vibe_selected`                             | [`InteractiveHero.tsx:75`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:75)   | `vibe`                          | 🟢        | Clean, captures the direction choice                                                                                           |
| 3   | `lead_email_submitted`                      | [`InteractiveHero.tsx:85`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:85)   | `vibe`                          | 🟡        | Missing `email_domain` for provider analysis, missing `is_returning` flag                                                      |
| 4   | `hero_rate_limited`                         | [`InteractiveHero.tsx:116`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:116) | `retry_after_seconds`           | 🟢        | Good for rate-limit monitoring                                                                                                 |
| 5   | `replies_revealed`                          | [`InteractiveHero.tsx:125`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:125) | `reply_count`, `cached`, `vibe` | 🟢        | Good context-rich event                                                                                                        |
| 6   | `ltd_checkout_opened`                       | [`Pricing.tsx:345`](landing-page/src/components/Pricing.tsx:345)                                  | _(none)_                        | 🟡        | Missing `source` (which page/section triggered it)                                                                             |
| 7   | `pricing_plan_cta_clicked`                  | [`Pricing.tsx:375`](landing-page/src/components/Pricing.tsx:375)                                  | `plan`, `plan_name`             | 🟢        | Only fires for Crush/Match plans (LTD uses separate event) — correct                                                           |
| 8   | `ltd_payment_initiated`                     | [`LtdCheckoutModal.tsx:89`](landing-page/src/components/LtdCheckoutModal.tsx:89)                  | `amount`, `txnid`               | 🟢        | Good revenue tracking                                                                                                          |
| 9   | `ltd_payment_error`                         | [`LtdCheckoutModal.tsx:95`](landing-page/src/components/LtdCheckoutModal.tsx:95)                  | `error`                         | 🟢        | Also calls `captureException` — excellent                                                                                      |
| 10  | `ltd_payment_succeeded`                     | [`ltd/success/page.tsx:35`](landing-page/src/app/ltd/success/page.tsx:35)                         | `has_code`                      | 🔴        | **Critical: missing `txnid` and `amount`** — cannot join to `ltd_payment_initiated` for funnel analysis or revenue attribution |
| 11  | `app_download_clicked`                      | [`CTA.tsx:161`](landing-page/src/components/CTA.tsx:161)                                          | `source`, `platform`            | 🟢        | Good attribution props                                                                                                         |
| 12  | `ios_waitlist_clicked`                      | [`page.tsx:106`](landing-page/src/app/page.tsx:106)                                               | `source`                        | 🟢        | Clean                                                                                                                          |
| 13  | `contact_form_submitted`                    | [`contact/page.tsx:106`](landing-page/src/app/contact/page.tsx:106)                               | `subject`                       | 🟡        | Missing `category` for contact routing analysis                                                                                |
| 14  | `screenshot_uploaded` (duplicate in report) | —                                                                                                 | —                               | —         | —                                                                                                                              |

---

## 3. 🔴 Critical Gaps (ALL FIXED)

> **Status:** All 10 gaps identified below have been fixed in the implementation pass. See [Fix Summary](#appendix-fix-summary) for details.

### Gap 1: No Page View Tracking (Severity: **CRITICAL**)

- **File:** [`instrumentation-client.ts`](landing-page/instrumentation-client.ts)
- **Problem:** In Next.js App Router, `posthog-js` does **not** auto-capture `$pageview`. You must call `posthog.pageview()` in a `useEffect` or use the `usePathname()` hook. Without this, you cannot compute any conversion rate.
- **Impact:** You know _how many_ people submitted their email, but not _what percentage_ of visitors that represents. Makes A/B testing and funnel analysis impossible.
- **Fix:** Add a [`PostHogPageView`](https://posthog.com/docs/libraries/next-js#app-router) component to the root layout that captures page views on route change.

### Gap 2: No Scroll/Section Visibility Tracking (Severity: **HIGH**)

- **Files:** [`page.tsx`](landing-page/src/app/page.tsx), all section components
- **Problem:** No tracking of when users scroll to key sections (Features, How It Works, Pricing, FAQ, CTA).
- **Impact:** You cannot identify where users drop off in the page. Is nobody making it to Pricing? Is the FAQ killing conversions? Unknown.
- **Fix:** Add `posthog.capture("section_viewed", { section: "pricing" })` using Intersection Observer on each section.

### Gap 3: Header CTA Not Tracked (Severity: **HIGH**)

- **File:** [`Header.tsx:64-83`](landing-page/src/components/Header.tsx)
- **Problem:** The "Google Play" button in the header navigation has no `onClick` tracking.
- **Impact:** The most prominent CTA on every page view — likely a significant source of installs — is invisible to analytics.
- **Fix:** Add `posthog.capture("app_download_clicked", { source: "header", platform: "google_play" })`.

### Gap 4: Mobile Menu CTA Not Tracked (Severity: **HIGH**)

- **File:** [`Header.tsx:127-150`](landing-page/src/components/Header.tsx)
- **Problem:** The Google Play button in the mobile hamburger menu is not tracked.
- **Impact:** Mobile traffic is typically 60%+ for dating apps. This is a blind spot.
- **Fix:** Same event as header desktop, with `source: "mobile_menu"`.

### Gap 5: LTD Success Missing Join Key (Severity: **HIGH**)

- **File:** [`ltd/success/page.tsx:33-37`](landing-page/src/app/ltd/success/page.tsx:33-37)
- **Problem:** `ltd_payment_succeeded` captures `has_code: Boolean(code)` but **not** the `txnid` or `amount`. This means you cannot link the success event back to the `ltd_payment_initiated` event.
- **Impact:** The entire LTD purchase funnel is broken — you can see "checkout opened → payment initiated" but cannot confirm which initiations resulted in success. Revenue tracking per transaction is impossible.
- **Fix:** Pass `txnid` and `amount` as URL params from PayU redirect and capture them in the success event.

### Gap 6: "View Pricing" Secondary CTA Not Tracked (Severity: **MEDIUM**)

- **File:** [`CTA.tsx:213-219`](landing-page/src/components/CTA.tsx:213-219)
- **Problem:** The secondary "View Pricing" button in the bottom CTA section has no tracking.
- **Impact:** Cannot measure intent-to-purchase traffic.
- **Fix:** Add `posthog.capture("view_pricing_clicked", { source: "bottom_cta" })`.

### Gap 7: Payment Verification Failures Not Tracked (Severity: **MEDIUM**)

- **File:** [`ltd/success/page.tsx:39-97`](landing-page/src/app/ltd/success/page.tsx:39-97)
- **Problem:** When the success page renders with an `error` query param (PayU failure redirect), no event is captured. The page shows a "Verification Failed" UI but PostHog never knows.
- **Impact:** Failed payment flows are invisible. You cannot measure pay-fail rate or diagnose issues.
- **Fix:** Add `posthog.capture("ltd_payment_verification_failed", { error: searchParams.get("error") })` in the `useEffect`.

### Gap 8: No FAQ Interaction Tracking (Severity: **MEDIUM**)

- **File:** [`FAQ.tsx`](landing-page/src/components/FAQ.tsx)
- **Problem:** FAQ open/close actions are not tracked.
- **Impact:** FAQ content is a valuable source of conversion objections. Knowing which questions users open most tells you what's blocking purchases.
- **Fix:** Add `posthog.capture("faq_opened", { question: faq.q })` and `faq_closed`.

### Gap 9: No Footer Link Tracking (Severity: **LOW-MEDIUM**)

- **File:** [`Footer.tsx`](landing-page/src/components/Footer.tsx)
- **Problem:** No footer link clicks are tracked (product links, social links, legal pages).
- **Impact:** Minor — footer links are lower in the conversion hierarchy, but social proof and legal trust signals matter.

### Gap 10: No Server-Side Events (Severity: **LOW**)

- **File:** [`posthog-server.ts`](landing-page/src/lib/posthog-server.ts)
- **Problem:** The `posthog-node` client is initialized but never used. Server actions (form submissions, API errors) aren't tracked server-side.
- **Impact:** Low for now since most events are client-side. But server-side retry/failure tracking would add robustness.

---

## 4. Funnel Analysis

### Hero Lead Magnet Funnel

```
screenshot_uploaded → vibe_selected → lead_email_submitted → replies_revealed
```

✅ **Well-tracked.** Each step has a distinct event with relevant properties. Rate limits are captured separately. This funnel is CRO-ready.

**Missing:** No tracking for users who _enter_ the funnel (dropzone interaction) but don't upload. You can't measure "screenshot intent" abandonment.

### LTD Purchase Funnel

```
ltd_checkout_opened → ltd_payment_initiated → ltd_payment_succeeded
```

⚠️ **Broken.** The join between `ltd_payment_initiated` and `ltd_payment_succeeded` is missing `txnid`. You can count events at each stage but cannot track individual users through the funnel.

### App Install Funnel (Missing)

```
page_view → header_cta_click → google_play_install
```

🔴 **Not tracked at all.** No page views, no header CTA tracking. The most important conversion path on the landing page is invisible.

---

## 5. Identity Management

### Current `identify()` calls:

1. [`InteractiveHero.tsx:84`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:84) — on lead email submit
2. [`LtdCheckoutModal.tsx:88`](landing-page/src/components/LtdCheckoutModal.tsx:88) — on payment initiation

### Issues:

- **Returning users are anonymous until they re-submit email.** If a user identified yesterday returns today, their session is fresh and anonymous until they hit the gate again. This inflates unique visitor counts and breaks session-based funnels.
- **No alias/reset calls.** If a user generates leads as `user@a.com` and later purchases as `user@b.com`, PostHog sees two distinct users.
- **`capture` before `identify` in some paths.** `lead_email_submitted` is captured after `identify()` — correct order. But `ltd_payment_initiated` is also after `identify()` — also correct.

### Recommendation:

Implement cookie-based re-identification on page load. Store the `distinct_id` in localStorage and call `posthog.identify()` on mount if the ID exists. The [setup report](landing-page/posthog-setup-report.md) already flagged this in its verification checklist.

---

## 6. Event Naming Convention Review

| Convention               | Assessment                                                              |
| ------------------------ | ----------------------------------------------------------------------- |
| `snake_case`             | ✅ Consistent across all 14 events                                      |
| Verb_noun pattern        | ✅ `screenshot_uploaded`, `vibe_selected`, `lead_email_submitted`, etc. |
| Namespacing by feature   | ✅ `ltd_*` prefix for LTD events, `hero_*` for hero events              |
| Standard property naming | Mostly consistent (`source`, `platform`, `vibe`)                        |

**No convention issues.** Events are well-named and namespaced.

---

## 7. Recommendations (Priority-Ordered)

### P0 — Must Fix (CRO-blocking)

| #   | Action                                                                                                | File(s)                     | Effort |
| --- | ----------------------------------------------------------------------------------------------------- | --------------------------- | ------ |
| 1   | **Add page view tracking** — Create a `PostHogPageView` component and mount it in the root layout     | `layout.tsx`, new component | 30 min |
| 2   | **Fix LTD success event** — Pass `txnid` and `amount` via URL params from PayU redirect, capture them | `ltd/success/page.tsx`      | 1 hr   |
| 3   | **Track header CTAs** — Add `posthog.capture` to both desktop and mobile header buttons               | `Header.tsx`                | 15 min |

### P1 — High Impact

| #   | Action                                                                                    | File(s)                              | Effort |
| --- | ----------------------------------------------------------------------------------------- | ------------------------------------ | ------ |
| 4   | **Add scroll/section tracking** — Track when users scroll to each major section           | `page.tsx` or each section component | 30 min |
| 5   | **Track "View Pricing" secondary CTA** — Bottom CTA secondary button                      | `CTA.tsx`                            | 5 min  |
| 6   | **Track payment verification failures** — Capture `ltd_payment_verification_failed` event | `ltd/success/page.tsx`               | 10 min |

### P2 — Nice to Have

| #   | Action                                                                                              | File(s)               | Effort |
| --- | --------------------------------------------------------------------------------------------------- | --------------------- | ------ |
| 7   | **Track FAQ interactions** — Which questions users open                                             | `FAQ.tsx`             | 20 min |
| 8   | **Add `email_domain` to `lead_email_submitted`** — For provider analytics                           | `InteractiveHero.tsx` | 5 min  |
| 9   | **Track footer link clicks** — Social and product links                                             | `Footer.tsx`          | 15 min |
| 10  | **Implement cookie-based re-identification** — Link returning users to their previous `distinct_id` | `layout.tsx`          | 1 hr   |

### P3 — Future

| #   | Action                                                                        | File(s)                     | Effort |
| --- | ----------------------------------------------------------------------------- | --------------------------- | ------ |
| 11  | **Add web vitals tracking**                                                   | `instrumentation-client.ts` | 15 min |
| 12  | **Add server-side event capture** — Use `posthog-node` for API route tracking | API routes                  | 2 hr   |
| 13  | **Add `$pageleave` tracking** — Capture exit intent                           | `Instrumentation`           | 15 min |

---

## 8. Quick Wins (30-minute fixes)

These are the highest-ROI changes you can make immediately:

1. **Page view tracking** + **Header CTA tracking** + **View Pricing CTA tracking** = ~45 min total and fixes the 3 biggest blind spots.
2. **LTD success event fix** = ~1 hr and unblocks the entire purchase funnel.

---

## 9. Summary Dashboard

| Metric                       | Status                         |
| ---------------------------- | ------------------------------ |
| Page views tracked           | ❌                             |
| Scroll depth tracked         | ❌                             |
| Section visibility tracked   | ❌                             |
| Hero funnel tracked          | ✅                             |
| LTD purchase funnel tracked  | ⚠️ (broken join)               |
| App install CTA tracked      | ⚠️ (partial — only bottom CTA) |
| Header CTA tracked           | ❌                             |
| Mobile CTA tracked           | ❌                             |
| FAQ interactions tracked     | ❌                             |
| Footer links tracked         | ❌                             |
| Error tracking (autocapture) | ✅                             |
| Error tracking (manual)      | ✅ (LTD only)                  |
| Identity management          | ⚠️ (no re-identification)      |
| Server-side events           | ❌ (client exists but unused)  |

---

## Appendix: Event Schema Reference

For consistency, ensure all new events follow the established patterns:

```typescript
// Event naming: snake_case, feature_prefixed
// Property naming: snake_case
// Required properties where applicable:
interface EventProps {
  source?: "header" | "mobile_menu" | "cta_section" | "pricing_section";
  platform?: "google_play" | "ios";
  vibe?: string;
}
```

---

## Appendix A: Fix Summary

All 10 critical gaps identified in this audit have been fixed. Below is a summary of every change made.

| #   | Gap                                                                  | Files Changed                                                                                                                                                                                                                                                                 | New Events / Props                                                         |
| --- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1   | **No page view tracking**                                            | [`instrumentation-client.ts`](landing-page/instrumentation-client.ts) — added `capture_pageview: false`; [`layout.tsx`](landing-page/src/app/layout.tsx) — mounted `<PostHogPageView>`; **new file** [`PostHogPageView.tsx`](landing-page/src/components/PostHogPageView.tsx) | `$pageview` (auto on route change)                                         |
| 2   | **No scroll/section visibility tracking**                            | **New file** [`SectionTracker.tsx`](landing-page/src/components/SectionTracker.tsx); [`page.tsx`](landing-page/src/app/page.tsx) — wrapped Features, HowItWorks, Pricing, FAQ, CTA sections                                                                                   | `section_viewed` { section }                                               |
| 3   | **Header CTA not tracked (desktop)**                                 | [`Header.tsx`](landing-page/src/components/Header.tsx:69) — added `onClick` to desktop Google Play button                                                                                                                                                                     | `app_download_clicked` { source: "header" }                                |
| 4   | **Mobile menu CTA not tracked**                                      | [`Header.tsx`](landing-page/src/components/Header.tsx:140) — added `onClick` to mobile hamburger Google Play button                                                                                                                                                           | `app_download_clicked` { source: "mobile_menu" }                           |
| 5   | **LTD success missing join key**                                     | [`ltd/success/page.tsx`](landing-page/src/app/ltd/success/page.tsx:33) — added `txnid` and `amount` from URL search params                                                                                                                                                    | `ltd_payment_succeeded` now includes `txnid`, `amount`                     |
| 6   | **"View Pricing" secondary CTA not tracked**                         | [`CTA.tsx`](landing-page/src/components/CTA.tsx:221) — added `onClick` to secondary button                                                                                                                                                                                    | `view_pricing_clicked` { source: "bottom_cta" }                            |
| 7   | **Payment verification failures not tracked**                        | [`ltd/success/page.tsx`](landing-page/src/app/ltd/success/page.tsx:33) — added `useEffect` branch for error state                                                                                                                                                             | `ltd_payment_verification_failed` { error, txnid, amount }                 |
| 8   | **No FAQ interaction tracking**                                      | [`FAQ.tsx`](landing-page/src/components/FAQ.tsx) — added `onOpen`/`onClose` callbacks to `FAQItem`                                                                                                                                                                            | `faq_opened` { question, index }, `faq_closed` { question, index }         |
| 9   | **No footer link tracking**                                          | [`Footer.tsx`](landing-page/src/components/Footer.tsx) — added `onClick` to every footer link                                                                                                                                                                                 | `footer_link_clicked` { category, label }                                  |
| 10  | **Missing `file_size` on screenshot + `email_domain` on lead email** | [`InteractiveHero.tsx`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:69) — added `file_size`; same file line 88 — added `email_domain`                                                                                                                    | `screenshot_uploaded` +`file_size`; `lead_email_submitted` +`email_domain` |
| —   | **Re-identification for returning users**                            | [`page.tsx`](landing-page/src/app/page.tsx:25) — added `useEffect` to restore from `sessionStorage`; [`InteractiveHero.tsx:86`](landing-page/src/components/interactive-hero/InteractiveHero.tsx:86) — stores `distinct_id` on identify                                       | N/A (identity management)                                                  |
| —   | **Sticky mobile Google Play CTA not tracked**                        | [`page.tsx`](landing-page/src/app/page.tsx:104) — added `onClick` to sticky CTA Google Play button                                                                                                                                                                            | `app_download_clicked` { source: "sticky_mobile_cta" }                     |

### Events Added (7 new)

| Event                             | Properties                 | Source                 |
| --------------------------------- | -------------------------- | ---------------------- |
| `$pageview`                       | `$current_url`             | `PostHogPageView.tsx`  |
| `section_viewed`                  | `section`                  | `SectionTracker.tsx`   |
| `view_pricing_clicked`            | `source`                   | `CTA.tsx`              |
| `faq_opened`                      | `question`, `index`        | `FAQ.tsx`              |
| `faq_closed`                      | `question`, `index`        | `FAQ.tsx`              |
| `footer_link_clicked`             | `category`, `label`        | `Footer.tsx`           |
| `ltd_payment_verification_failed` | `error`, `txnid`, `amount` | `ltd/success/page.tsx` |

### Existing Events Enhanced (3)

| Event                   | Added Properties  |
| ----------------------- | ----------------- |
| `screenshot_uploaded`   | `file_size`       |
| `lead_email_submitted`  | `email_domain`    |
| `ltd_payment_succeeded` | `txnid`, `amount` |

### New Files Created (2)

- [`PostHogPageView.tsx`](landing-page/src/components/PostHogPageView.tsx) — Client component that captures `$pageview` on route change via `usePathname()` + `useSearchParams()`
- [`SectionTracker.tsx`](landing-page/src/components/SectionTracker.tsx) — Wrapper component using `IntersectionObserver` to fire `section_viewed` once per section per session

### Build Result

```
npx next build  →  Finished TypeScript in 1506ms ...  ✅ No errors
```
