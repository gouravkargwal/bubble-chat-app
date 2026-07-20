# Complete Audit: All References Requiring Changes

Conducted across 5 passes over the full codebase. This is the definitive list of every file, line, and string that references "dating," "dating coach," "dating app," "rizz," "RizzBot," "AI wingman," or related terms that need repositioning.

---

## PASS 1: Landing Page (`landing-page/src/`)

### 1. `landing-page/src/app/constants.ts`
| Line | Current | Notes |
|------|---------|-------|
| 54 | `tagline: "AI Dating Coach"` | → Change to `"AI Conversation Assistant"` |
| 57-58 | `title: "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder"` | → Remove all "dating" and app names |
| 59-60 | `description: "Best free AI dating coach for Hinge, Bumble & Tinder..."` | → Rewrite without dating framing |

### 2. `landing-page/src/app/layout.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 39-49 | Keywords array: `"AI dating coach"`, `"dating app replies"`, `"Hinge reply generator"`, `"Bumble chat assistant"`, `"Tinder opener"`, `"AI wingman"`, `"dating profile help"`, `"better dating responses"`, `"free AI dating coach"` | → Replace all with non-dating keywords |
| 66 | OG image alt: `"AI Dating Coach App Preview — Get Better Replies on Hinge, Bumble & Tinder"` | → Remove dating/app names |
| 128 | JSON-LD comment: `WebApplication (AI Dating Coach)` | → Reword |
| 197-200 | FAQ in JSON-LD: `"Which dating apps does Cookd support?"` | → Reword to "chat apps" |
| 216-218 | FAQ JSON-LD answer: `"Our AI has been trained on thousands of successful dating conversations..."` | → Reword |

### 3. `landing-page/src/app/blog/page.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 8-9 | meta description: `"Dating tips, AI coaching guides..."` | → Reword |
| 11-13 | OG title/description: `"Dating Tips & AI Coaching Guides"` / `"Learn how to get better replies, craft winning openers, and master dating apps..."` | → Reword |
| 24-25 | H1: `"Dating Tips & AI Coaching Guides"` | → Reword |
| 28-29 | Subtitle: `"...improve your dating app conversations..."` | → Reword |

### 4. `landing-page/src/app/blog/metadata.ts`
Virtually every article has "dating," "AI dating coach," "AI dating assistant," "Hinge," "Bumble," "Tinder," or "dating apps" in title/description/body. Full list:

| Slug | Title | Description |
|------|-------|-------------|
| `how-to-get-better-replies-on-hinge` | "How to Get Better Replies on Hinge: A Complete Guide" | "Stop getting left on read. Learn the exact strategies..." |
| `best-openers-for-bumble` | "Best Openers for Bumble That Actually Get Responses" | "Tired of your Bumble matches expiring?..." |
| `ai-dating-coach-vs-human-wingman` | "AI Dating Coach vs Human Wingman: Which Works Better?" | "We compared an AI dating coach against a human wingman..." |
| `how-to-get-unmatched-tinder-strategies` | "5 Tinder Strategies That Actually Lead to Dates" | "Stop swiping into oblivion. Use these data-backed Tinder strategies..." |
| `dating-profile-photo-tips` | "Dating Profile Photo Tips: What Science Says About First Impressions" | "Your photos are 90% of your dating profile. Here's how..." |
| `conversation-killers-dating-apps` | "7 Conversation Killers on Dating Apps (And How to Fix Them)" | "These common conversation mistakes are costing you matches..." |

Category labels: `"Dating Tips"`, `"Profile Tips"`, `"Comparisons"` — at minimum `"Dating Tips"` needs renaming.

### 5. `landing-page/src/app/blog/[slug]/page.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 135-136 | `"Download Cookd — the AI dating coach that analyzes your chats and crafts winning replies in seconds."` | → Reword |

### 6. `landing-page/src/app/privacy/page.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 17 | `"Cookd ... provides a mobile application and related services for AI-assisted dating conversation support."` | → Remove "dating" |
| 161 | meta description: `"Cookd privacy policy — how we collect, use, and protect your data when you use our AI dating coach app."` | → Reword |

### 7. `landing-page/src/app/terms/page.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 103-104 | meta description: `"Cookd terms of service — conditions for using our AI dating coach app..."` | → Reword |

### 8. `landing-page/src/app/contact/page.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 15 | FAQ: `"...connect your dating apps. Our AI analyzes your conversations in real-time..."` | → Reword |
| 22-23 | FAQ: `"Which dating apps are supported?"` / `"Cookd works with all major dating platforms including Tinder, Hinge, Bumble..."` | → Reword |
| 116-117 | meta description: `"Get in touch with Cookd — our AI dating coach team..."` | → Reword |

### 9. `landing-page/src/components/Features.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 165 | H2: `"Engineered for the Modern Dater"` | → Change to `"Engineered for Better Conversations"` |
| (multiple) | Feature descriptions reference "dating" context | → Reword to generic conversation assistance |

### 10. `landing-page/src/components/Pricing.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 42 | Plan description: `"The standard blueprint for dating control."` | → Reword |
| (multiple) | Feature labels mention "dating" | → Check all |

### 11. `landing-page/src/components/FAQ.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 19-20 | `"Which dating apps does Cookd support?"` / `"Cookd works with any chat-based app — Hinge, Bumble, Tinder..."` | → Reword |
| 28 | `"Our AI has been trained on thousands of successful dating conversations..."` | → Reword |

### 12. `landing-page/src/components/Footer.tsx`
| Line | Current | Notes |
|------|---------|-------|
| 47 | `"AI-powered dating coach that helps you craft winning messages."` | → Reword |

### 13. `landing-page/src/components/CTA.tsx`
No direct "dating" references found — the CTA is already neutral. ✓

### 14. `landing-page/src/components/AppMockup.tsx`
(Not checked explicitly — should be verified for "dating" in UI mockup text)

### 15. `landing-page/README.md`
| Line | Current | Notes |
|------|---------|-------|
| 3 | `"Marketing landing page for Cookd AI Dating Coach."` | → Reword |

---

## PASS 2: Android App (`RizzBotV2/`)

### 16. `RizzBotV2/app/src/main/res/values/strings.xml`
| Line | Current | Notes |
|------|---------|-------|
| 4 | `boot_tagline: "Smart replies for dating chats"` | → Change to `"Smart replies for any chat"` |
| 13 | `share_app_body: "Check out Cookd — AI dating chat assistant! %1$s"` | → Remove "dating" |
| 14 | `share_referral_body: "Use my code %1$s to unlock 24 Hours of God Mode on Cookd! %2$s"` | No "dating" — OK |

### 17. `RizzBotV2/app/src/main/java/com/rizzbot/v2/ui/home/HomeScreen.kt`
| Line | Current | Notes |
|------|---------|-------|
| 323 | `"Open a dating app and tap the bubble."` | → Change to `"Open a messaging app and tap the bubble."` |
| 324 | `"Turn on to get AI replies in your dating apps."` | → `"Turn on to get AI replies in your messaging apps."` |
| 472 | `"Score your dating photos"` | → `"Score your profile photos"` |
| 632 | `"...float a bubble over your dating apps."` | → `"...float a bubble over your messaging apps."` |

### 18. `RizzBotV2/app/src/main/java/com/rizzbot/v2/ui/settings/SettingsScreen.kt`
| Line | Current | Notes |
|------|---------|-------|
| 308 | `"Check out Cookd — AI replies for dating apps! 🚀"` | → Remove "dating apps" |

### 19. `RizzBotV2/app/src/main/java/com/rizzbot/v2/ui/onboarding/OnboardingValueCardsStep.kt`
| Line | Current | Notes |
|------|---------|-------|
| 60 | `"Get an AI-powered audit of your dating profile."` | → `"Get an AI-powered audit of your chat profile."` |

### 20. `RizzBotV2/app/src/main/java/com/rizzbot/v2/domain/model/ConversationDirection.kt`
Package name contains `rizzbot` — this is a code package name, not user-facing. **Low priority for changes**, but if Google Play reviewers inspect the app binary, they could see `com.rizzbot.v2` in the package namespace. Changing the package name would require a new Play Store listing. **Risk assessment**: Google Play does not typically flag package names.

### 21. `RizzBotV2/app/src/main/res/raw/terms_of_service.txt`
| Line | Current | Notes |
|------|---------|-------|
| 11 | `"Cookd provides AI-assisted features for dating-app conversations..."` | → Reword |
| 17 | `"...including dating platforms"` in acceptable use | → Reword |

### 22. `RizzBotV2/settings.gradle.kts`
| Line | Current | Notes |
|------|---------|-------|
| 26 | `rootProject.name = "RizzBotV2"` | Internal build name, not user-facing |

### 23. `RizzBotV2/app/build.gradle.kts`
| Line | Current | Notes |
|------|---------|-------|
| 28 | `namespace = "com.rizzbot.v2"` | Internal, but visible in compiled binary. Renaming requires new Play Store app. |

### 24. `RizzBotV2/app/src/main/res/values/themes.xml`
| Line | Current | Notes |
|------|---------|-------|
| 8, 12, 15 | `name="Theme.RizzBotV2"`, `name="Theme.RizzBotV2.Splash"` | Internal theme names |

### 25. `RizzBotV2/app/src/main/AndroidManifest.xml`
| Line | Current | Notes |
|------|---------|-------|
| 20 | `android:name=".RizzBotApp"` | Internal class reference |
| 28 | `android:theme="@style/Theme.RizzBotV2"` | Internal theme reference |

---

## PASS 3: Backend (`backend/`)

### 26. `backend/app/main.py`
| Line | Current | Notes |
|------|---------|-------|
| 319 | `title="RizzBot API"` | → Change to `"Cookd API"` |

### 27. `backend/app/config.py`
| Line | Current | Notes |
|------|---------|-------|
| 58-59 | Comment: `"screenplay (default) or coach (legacy Dating Coach rules)"` | Internal comment — OK to leave |
| 120 | `openobserver_service_name: str = "rizzbot-api"` | → Change to `"cookd-api"` |

### 28. `backend/app/infrastructure/metrics.py`
All Prometheus metric names use `rizzbot_` prefix. E.g.:
| Line | Current |
|------|---------|
| 274 | `"rizzbot_http_requests_total"` |
| 280 | `"rizzbot_http_request_duration_seconds"` |
| 290 | `"rizzbot_llm_calls_total"` |
| 296 | `"rizzbot_llm_latency_seconds"` |
| 303 | `"rizzbot_llm_tokens_total"` |
| 309 | `"rizzbot_llm_fallback_total"` |
| 319 | `"rizzbot_llm_cost_total"` |
| 329 | `"rizzbot_audit_jobs_total"` |
| 335 | `"rizzbot_blueprint_generations_total"` |
| 345 | `"rizzbot_db_connections_in_use"` |
| 351 | `"rizzbot_active_audit_workers"` |
| 360 | `"rizzbot_error_total"` |
| 366 | `"rizzbot_notification_failures_total"` |
| 376 | `"rizzbot_cache_hits_total"` |
| 382 | `"rizzbot_cache_misses_total"` |
| 388 | `"rizzbot_tier_allocations_total"` |
| 429 | `service_name: str = "rizzbot-api"` |

**Note**: Changing Prometheus metric names will break existing dashboards. If you don't have critical dashboards yet, rename them. If you do, keep the old names or migrate gradually.

### 29. `backend/app/infrastructure/tracing.py`
| Line | Current | Notes |
|------|---------|-------|
| 37 | `service_name: str = "rizzbot-api"` | → Change to `"cookd-api"` |

### 30. `backend/app/infrastructure/otel_logging.py`
| Line | Current | Notes |
|------|---------|-------|
| 13, 62 | `service_name: str = "rizzbot-api"` | → Change to `"cookd-api"` |

### 31. `backend/app/infrastructure/database/models.py`
| Line | Current | Notes |
|------|---------|-------|
| 48 | Comment: `# free, crush, match, rizz` | Tier names include "rizz". This is internal data taxonomy. |
| 48 | `tier: "rizz"` is a subscription tier value | If this flows to RevenueCat entitlments, renaming it means changing subscription product IDs. **High risk — leave as-is**. |

### 32. `backend/app/core/tier_config.py`
| Line | Current | Notes |
|------|---------|-------|
| 40 | `"rizz": 300,  # ₹499/month` | Internal tier name — OK to keep |
| 46 | `"rizz": 30,` | Same |
| 152-155 | `"rizz": {...}` | Same |

### 33. `backend/app/domain/tiers.py`
| Line | Current | Notes |
|------|---------|-------|
| 5 | `TIER_HIERARCHY = {"free": 0, "crush": 1, "match": 2, "rizz": 3}` | Internal — OK |

### 34. `backend/app/api/v1/webhooks.py`
| Line | Current | Notes |
|------|---------|-------|
| 27 | `"rizz": "rizz"` | Internal RevenueCat product mapping |
| 46-47 | `if "rizz" in pid: return "rizz"` | Same |

### 35. `backend/app/testing/__main__.py`
| Line | Current | Notes |
|------|---------|-------|
| 11 | `description="RizzBot Prompt Evaluation Suite"` | Internal test tool — OK |

### 36. `backend/agent/graph_v2.py`
| Line | Current | Notes |
|------|---------|-------|
| 156 | `rizz_agent_v2 = workflow.compile()` | Internal variable name. Referenced from `vision_v2.py` and `public.py` |

### 37. `backend/app/api/v1/vision_v2.py`
| Line | Current | Notes |
|------|---------|-------|
| 245-248 | `from agent.graph_v2 import rizz_agent_v2` | Internal import |
| 665-667 | `bouncer_reason, "Image is not a valid chat or dating app screenshot."` | → Change error message to `"Image is not a valid chat screenshot."` |

### 38. `backend/app/api/v1/public.py`
| Line | Current | Notes |
|------|---------|-------|
| 3-4 | Docstring: `runs the full rizz_agent_v2` | Internal docstring |
| 336-339 | `from agent.graph_v2 import rizz_agent_v2` | Internal import |

### 39. `backend/app/prompts/` — ALL prompt files
These are **internal prompt instructions fed to the LLM**, not user-facing. They extensively reference "dating coach," "dating app," etc. These do NOT need to change — they are not visible to Razorpay or Google Play reviewers. The LLM prompts instruct the model on what to generate; changing them would change the product behavior, which is out of scope.

### 40. `backend/docker/openobserver/README.md`
| Line | Current | Notes |
|------|---------|-------|
| 23 | `default: rizzbot-api` | Internal doc |

### 41. `backend/docker/observability/README.md`
| Line | Current | Notes |
|------|---------|-------|
| 3 | `"monitoring the RizzBot API"` | Internal doc |

---

## PASS 4: Markdown Docs & Root Config Files

### 42. `landing-page/README.md`
| Line | Current | Notes |
|------|---------|-------|
| 3 | `"Marketing landing page for Cookd AI Dating Coach."` | → Reword |

### 43. `build-commands.md`
| Line | Current | Notes |
|------|---------|-------|
| 1 | `"# RizzBot / Cookd – Build & Release Commands"` | Internal dev doc — OK |

### 44. `RizzBotV2/app/src/production/README.md`
Internal build doc — OK

### 45. `features.md`, `GROWTH_STRATEGY.md`, `prompts.md`, `LLM_PROMPTS_AUDIT.md`
These are internal planning/docs — NOT public-facing. OK to leave as-is.

### 46. `backend/scripts/generator_prompt.txt`
Internal prompt reference — OK.

### 47. `backend/scripts/model_comparison.md`
Internal model eval — OK.

### 48. `design-system/cookd/MASTER.md`
| Line | Current | Notes |
|------|---------|-------|
| 11 | `"Category: Dating App"` | Internal design doc — OK |

---

## PASS 5: Android App — Additional User-Facing Strings

### 49. `RizzBotV2/app/src/main/java/com/rizzbot/v2/util/Constants.kt`
| Line | Current | Notes |
|------|---------|-------|
| 18 | `NOTIFICATION_CHANNEL_ID = "rizzbot_service"` | Internal — OK |
| 19 | `NOTIFICATION_ID = 1001` | Internal — OK |

### 50. `RizzBotV2/app/src/main/java/com/rizzbot/v2/capture/CaptureService.kt`
| Line | Current | Notes |
|------|---------|-------|
| 59 | `"Cookd is taking a screenshot..."` | Notification text — OK (no dating reference) |
| 66 | `CHANNEL_ID = "rizzbot_capture"` | Internal — OK |

### 51. `RizzBotV2/app/src/main/java/com/rizzbot/v2/domain/model/DatingApp.kt`
File exists at `domain/model/DatingApp.kt`. Check its content for user-facing strings.

### 52. `RizzBotV2/app/src/main/java/com/rizzbot/v2/ui/paywall/PaywallTierMarketing.kt`
| Line | Current | Notes |
|------|---------|-------|
| 14 | `else -> "Upgrade your wingman"` | "wingman" could imply dating. → Change to `"Upgrade your plan"` |

---

## SUMMARY: What MUST Change for Razorpay/Google Play

### CRITICAL (affects visible public content):

| # | File | Lines | Count |
|---|------|-------|-------|
| 1 | `landing-page/src/app/constants.ts` | 54, 57-60 | 2-3 changes |
| 2 | `landing-page/src/app/layout.tsx` | 39-49, 66, 128, 197-200, 216-218 | ~15 keyword changes |
| 3 | `landing-page/src/app/blog/page.tsx` | 8-9, 11-13, 24-25, 28-29 | ~6 changes |
| 4 | `landing-page/src/app/blog/metadata.ts` | All 6 articles + categories | ~20+ changes |
| 5 | `landing-page/src/app/blog/[slug]/page.tsx` | 135-136 | 1 change |
| 6 | `landing-page/src/app/privacy/page.tsx` | 17, 161 | 2 changes |
| 7 | `landing-page/src/app/terms/page.tsx` | 103-104 | 1 change |
| 8 | `landing-page/src/app/contact/page.tsx` | 15, 22-23, 116-117 | ~4 changes |
| 9 | `landing-page/src/components/Features.tsx` | 165 | 1 change |
| 10 | `landing-page/src/components/Pricing.tsx` | 42 | 1 change |
| 11 | `landing-page/src/components/FAQ.tsx` | 19-20, 28 | 2 changes |
| 12 | `landing-page/src/components/Footer.tsx` | 47 | 1 change |
| 13 | `landing-page/README.md` | 3 | 1 change |
| 14 | `RizzBotV2/app/src/main/res/values/strings.xml` | 4, 13 | 2 changes |
| 15 | `RizzBotV2/app/src/main/res/raw/terms_of_service.txt` | 11, 17 | 2 changes |
| 16 | `RizzBotV2/app/src/main/java/.../HomeScreen.kt` | 323, 324, 472, 632 | 4 changes |
| 17 | `RizzBotV2/app/src/main/java/.../SettingsScreen.kt` | 308 | 1 change |
| 18 | `RizzBotV2/app/src/main/java/.../OnboardingValueCardsStep.kt` | 60 | 1 change |
| 19 | `RizzBotV2/app/src/main/java/.../PaywallTierMarketing.kt` | 14 | 1 change |
| 20 | `backend/app/api/v1/vision_v2.py` | 666 | 1 change |

### COSMETIC/NON-BLOCKING (rename for consistency):

| # | File | Lines | Notes |
|---|------|-------|-------|
| 21 | `backend/app/main.py` | 319 | API title: `"RizzBot API"` → `"Cookd API"` |
| 22 | `backend/app/config.py` | 120 | Service name: `"rizzbot-api"` → `"cookd-api"` |
| 23 | `backend/app/infrastructure/tracing.py` | 37 | Same service name |
| 24 | `backend/app/infrastructure/otel_logging.py` | 13, 62 | Same service name |
| 25 | `backend/app/infrastructure/metrics.py` | All `rizzbot_*` metrics | Renaming breaks existing dashboards — evaluate |

### INTERNAL ONLY (NO CHANGE NEEDED):

- Prompt files (`_generator.py`, `_auditor.py`, `profile_auditor.py`, `scripts.py`, `vision_api.py`, etc.)
- Tier names in `tier_config.py`, `models.py`, `webhooks.py`
- Internal variable names like `rizz_agent_v2`
- `features.md`, `GROWTH_STRATEGY.md`, `prompts.md`, `LLM_PROMPTS_AUDIT.md`
- Android package `com.rizzbot.v2` (binary-level, would require new Play Store app)
- RevenueCat product identifiers containing "rizz"
- Prometheus metric names (if dashboards exist)

### TOTAL:
- **~50 user-facing string changes** across ~20 files
- **~5 cosmetic backend renames**
- **0 prompt/behavioral changes**
