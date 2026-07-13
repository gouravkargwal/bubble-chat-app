<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the Cookd landing page. The following changes were made:

- **`instrumentation-client.ts`** (new): Initialises posthog-js for all client-side pages using Next.js 15.3+ instrumentation hooks. Includes exception autocapture and a reverse-proxy `api_host`.
- **`next.config.ts`**: Added `/ingest/*` rewrites so PostHog requests are proxied through the app's own domain, bypassing ad-blockers and reducing data loss.
- **`src/lib/posthog-server.ts`** (new): Singleton posthog-node client for server-side event capture. Configured with `flushAt: 1` and `flushInterval: 0` for short-lived server contexts.
- **`src/components/interactive-hero/InteractiveHero.tsx`**: Added `posthog.identify()` on email submit and `posthog.capture()` calls for every step of the AI-reply funnel.
- **`src/components/Pricing.tsx`**: Tracks LTD modal opens and plan CTA clicks.
- **`src/components/LtdCheckoutModal.tsx`**: Tracks payment initiation (with `posthog.identify()`) and payment errors (with `posthog.captureException()`).
- **`src/app/ltd/success/page.tsx`**: Tracks confirmed LTD payment successes via a `useEffect` on page mount.
- **`src/components/CTA.tsx`**: Tracks Google Play download clicks from the bottom CTA section.
- **`src/app/page.tsx`**: Tracks iOS waitlist clicks from the sticky mobile CTA bar.
- **`src/app/contact/page.tsx`**: Tracks contact form submissions.

| Event name | Description | File |
|---|---|---|
| `screenshot_uploaded` | User uploads a screenshot in the interactive hero, starting the AI reply funnel. | `src/components/interactive-hero/InteractiveHero.tsx` |
| `vibe_selected` | User selects a conversation direction (vibe) in the hero funnel. | `src/components/interactive-hero/InteractiveHero.tsx` |
| `lead_email_submitted` | User submits their email in the gate step to unlock AI-generated replies. | `src/components/interactive-hero/InteractiveHero.tsx` |
| `replies_revealed` | AI-generated replies are successfully returned and revealed to the user. | `src/components/interactive-hero/InteractiveHero.tsx` |
| `hero_rate_limited` | User hits the rate limit when trying to generate replies in the hero. | `src/components/interactive-hero/InteractiveHero.tsx` |
| `ltd_checkout_opened` | User opens the Lifetime Deal checkout modal from the pricing section. | `src/components/Pricing.tsx` |
| `pricing_plan_cta_clicked` | User clicks the CTA button (Download App) on a subscription pricing plan. | `src/components/Pricing.tsx` |
| `ltd_payment_initiated` | User submits the LTD checkout form and is redirected to PayU for payment. | `src/components/LtdCheckoutModal.tsx` |
| `ltd_payment_error` | An error occurs while creating the LTD payment order before redirect to PayU. | `src/components/LtdCheckoutModal.tsx` |
| `ltd_payment_succeeded` | User lands on the LTD success page confirming a completed lifetime deal payment. | `src/app/ltd/success/page.tsx` |
| `app_download_clicked` | User clicks a Google Play download button in the CTA section. | `src/components/CTA.tsx` |
| `ios_waitlist_clicked` | User clicks the iOS waitlist button in the sticky mobile CTA bar. | `src/app/page.tsx` |
| `contact_form_submitted` | User submits the contact form on the contact page. | `src/app/contact/page.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behaviour, based on the events we just instrumented:

- **Dashboard**: [Analytics basics (wizard)](https://us.posthog.com/project/510053/dashboard/1839581)
- **Hero conversion funnel** — screenshot → vibe → email → replies: [Jt1cpzeF](https://us.posthog.com/project/510053/insights/Jt1cpzeF)
- **LTD purchase funnel** — checkout opened → payment initiated → payment succeeded: [C8qgv5LK](https://us.posthog.com/project/510053/insights/C8qgv5LK)
- **Daily hero engagement** — screenshots, emails, replies over time: [zyXLrOKy](https://us.posthog.com/project/510053/insights/zyXLrOKy)
- **App download clicks by source**: [xGxFtV6n](https://us.posthog.com/project/510053/insights/xGxFtV6n)
- **Vibe selection breakdown** — which vibes users pick most: [TpVFbQ76](https://us.posthog.com/project/510053/insights/TpVFbQ76)

## Verify before merging

- [ ] Run a full production build (`npm run build`) and fix any lint or type errors introduced by the generated code.
- [ ] Run the test suite — call sites that were rewritten or instrumented may need updated mocks or fixtures.
- [ ] Add `NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN` and `NEXT_PUBLIC_POSTHOG_HOST` to `.env.example` and any monorepo bootstrap scripts so collaborators know what to set.
- [ ] Wire source-map upload (`posthog-cli sourcemap` or your bundler's upload step) into CI so production stack traces de-minify in PostHog error tracking.
- [ ] Confirm the returning-visitor path also calls `identify` — currently `posthog.identify()` is only called at the lead-email gate and LTD checkout; if users return to the site already known, their session won't be linked until they complete one of those flows again.

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-nextjs-app-router/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
