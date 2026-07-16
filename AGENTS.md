<!-- code-review-graph MCP tools -->

## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool                        | Use when                                               |
| --------------------------- | ------------------------------------------------------ |
| `detect_changes`            | Reviewing code changes — gives risk-scored analysis    |
| `get_review_context`        | Need source snippets for review — token-efficient      |
| `get_impact_radius`         | Understanding blast radius of a change                 |
| `get_affected_flows`        | Finding which execution paths are impacted             |
| `query_graph`               | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes`     | Finding functions/classes by name or keyword           |
| `get_architecture_overview` | Understanding high-level codebase structure            |
| `refactor_tool`             | Planning renames, finding dead code                    |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

---

# Cookd — AI Dating Coach

**Product:** Android app that analyzes dating app screenshots and generates witty, personalized reply options using a multi-agent Gemini pipeline.

**Domain:** [cookdai.site](https://cookdai.site)
**Google Play:** `com.cookd.mobile`
**Tech Stack:** FastAPI + Gemini 3.1 Flash-Lite + PostgreSQL (pgvector) + LangGraph + Next.js landing page

---

## Architecture Overview

```mermaid
flowchart LR
    Android[Android App] --> API[FastAPI Backend]
    API --> Auth[Firebase Auth / JWT]
    API --> Quota[Quota Manager]
    API --> VisionV2[Vision V2 Endpoint]

    subgraph AgentPipeline[Multi-Agent Gemini Pipeline]
        VisionNode[Vision Node<br/>Screen Analysis] --> GeneratorNode[Generator Node<br/>Reply Generation]
        GeneratorNode --> AuditorNode[Auditor Node<br/>Quality Gate]
        AuditorNode -- pass --> Ship[Return 4 Replies]
        AuditorNode -- fail + ≤1 rewrites --> GeneratorNode
        AuditorNode -- fail + ≥2 rewrites --> Ship
    end

    VisionV2 --> AgentPipeline
    AgentPipeline --> DB[(PostgreSQL<br/>+ pgvector)]
    AgentPipeline --> OCI[OCI Object Storage<br/>Temp Screenshots]

    subgraph Telemetry[Data Pipeline]
        Track[Track Copy/Rating] --> DB
        Telemetry[Telemetry Action] --> DB
    end

    Android --> Telemetry
```

---

## Backend API Endpoints

All under `/api/v1/` prefix.

### Core Vision (the main product loop)

| Endpoint                      | Method | Description                                                             |
| ----------------------------- | ------ | ----------------------------------------------------------------------- |
| `/vision/generate`            | POST   | Analyze screenshots + generate 4 reply options via multi-agent pipeline |
| `/conversations`              | GET    | List active conversations for user (paginated)                          |
| `/conversations/{id}`         | DELETE | Delete a conversation                                                   |
| `/conversations/{id}/resolve` | POST   | Resolve hybrid-stitch pending images                                    |

### History & Tracking

| Endpoint            | Method | Description                                         |
| ------------------- | ------ | --------------------------------------------------- |
| `/history`          | GET    | User's interaction history with vibe breakdown      |
| `/track/copy`       | POST   | Track which reply user copied + store embedding     |
| `/track/rating`     | POST   | Track user rating of a reply                        |
| `/telemetry/action` | POST   | Record regenerated / copied index for data pipeline |

### Auth & Users

| Endpoint             | Method  | Description                                          |
| -------------------- | ------- | ---------------------------------------------------- |
| `/auth/me`           | GET     | Current user profile                                 |
| `/auth/firebase`     | POST    | Firebase token exchange                              |
| `/users/delete`      | DELETE  | Delete account + all data                            |
| `/users/preferences` | GET/PUT | User preferences (prompt variant, marketing consent) |

### Billing & Referral

| Endpoint                     | Method | Description                           |
| ---------------------------- | ------ | ------------------------------------- |
| `/billing/status`            | GET    | Current tier + plan info              |
| `/billing/ltd/create-order`  | POST   | Create PayU order for Lifetime Deal   |
| `/billing/ltd/banner-config` | GET    | LTD scarcity config (spots remaining) |
| `/billing/ltd/history`       | GET    | LTD purchase history                  |
| `/billing/ltd/verify`        | POST   | Verify PayU payment                   |
| `/billing/ltd/redeem`        | POST   | Redeem LTD code                       |
| `/webhooks/revenuecat`       | POST   | RevenueCat subscription webhook       |
| `/webhooks/payu`             | POST   | PayU payment callback                 |
| `/referral/me`               | GET    | User's referral code + stats          |
| `/referral/apply`            | POST   | Apply a referral code                 |

### Public (no auth)

| Endpoint                       | Method | Description                                                      |
| ------------------------------ | ------ | ---------------------------------------------------------------- |
| `/public/lead-magnet/generate` | POST   | Free demo: screenshot → AI replies (rate-limited, email capture) |

### Admin (behind X-Admin-Key)

| Endpoint                                    | Method     | Description                                |
| ------------------------------------------- | ---------- | ------------------------------------------ |
| `/admin/rendered-videos`                    | GET        | List rendered Remotion videos with filters |
| `/admin/rendered-videos/{id}`               | GET/DELETE | Get or delete a rendered video             |
| `/admin/rendered-videos/{id}/download`      | GET        | Download rendered video file               |
| `/admin/candidates`                         | GET        | List video candidates with scoring         |
| `/admin/candidates/render`                  | POST       | Trigger Remotion render                    |
| `/admin/publish/trending-audio`             | GET        | Trending YouTube audio tracks              |
| `/admin/publish/generate-caption`           | POST       | Generate caption via Llama 3               |
| `/admin/publish/send`                       | POST       | Overlay audio + post to Instagram/YouTube  |
| `/admin/publish/audio-preview/{youtube_id}` | GET        | Stream audio preview URL                   |

---

## Multi-Agent Pipeline (LangGraph)

The core product uses a 3-node LangGraph agent with an auditor rewrite loop:

```
vision_node → (valid?) → generator_node → auditor_node → (pass? → END)
                                ↑                            |
                                └── (fail, rewrite ≤ 1) ────┘
```

### 1. Vision Node

- **Model:** Gemini 3.1 Flash-Lite (or `gemini_vision_model` override)
- **Input:** 1-5 base64-encoded screenshots
- **Output:** Structured analysis: OCR text, visual hooks, photo persona, durable facts, archetype, dialect
- **Validation:** Bouncer checks if screenshots contain actual dating app chat UI

### 2. Generator Node

- **Model:** Gemini 3.1 Flash-Lite (or `gemini_generator_model` override) — or Groq's Llama 3.3 70B via `generator_provider=groq`
- **Prompt Mode:** "screenplay" (Netflix India Screenwriter) or "coach" (legacy Dating Coach)
- **Input:** Vision analysis + conversation context + direction + optional custom hint
- **Output:** 4 reply options, each with: `text`, `strategy` label, `is_recommended` flag
- **Direction Options:** OPENER, QUICK_REPLY, KEEP_PLAYFUL, CHANGE_TOPIC, TEASE, REVIVE_CHAT, GET_NUMBER, ASK_OUT, DE_ESCLATE — feature-gated by tier

### 3. Auditor Node

- **Model:** Gemini 3.1 Flash-Lite (or `gemini_auditor_model` override)
- **Temperature:** 0 (deterministic)
- **Checks:** Context fit, tone safety, direction compliance, cringe detection, diversity, dialect authenticity
- **Rewrites:** Max 1 rewrite cycle (2 total generations). Ships after that regardless.

---

## Tier System (Credits-Based)

| Tier      | Price   | Credits           | Period   | Directions | Screenshots | Hints      | Photo Audit | Blueprint |
| --------- | ------- | ----------------- | -------- | ---------- | ----------- | ---------- | ----------- | --------- |
| **Free**  | ₹0      | 10 signup + 1/day | daily    | 4 basic    | 2           | No         | No          | No        |
| **Crush** | ₹99/wk  | 50                | 7 days   | 7          | 5           | 300 chars  | 6 photos    | No        |
| **Match** | ₹249/mo | 150               | 30 days  | All 9      | 5           | 300 chars  | 6 photos    | Yes       |
| **Rizz**  | ₹499/mo | 300               | 30 days  | All 9      | 5           | 300 chars  | 6 photos    | Yes       |
| **LTD**   | ₹999    | 300/30d refill    | lifetime | Match tier | —           | 1000 chars | —           | —         |

**Credit costs:** `chat_generation=1`, `profile_audit=8`, `profile_blueprint=12`

---

## Database Schema

Key tables (PostgreSQL + pgvector):

- **`users`** — Auth, tier, referral codes, plan tracking
- **`user_quotas`** — Credits system (keyed by Google provider ID)
- **`conversations`** — Chat threads with person name, stage, tone trend
- **`interactions`** — Per-generation records with replies, copied index, embeddings
- **`conversation_memories`** — RAG fact store with embeddings + importance scoring
- **`generation_logs`** — Full telemetry pipeline (vision dump, auditor critiques, human feedback)
- **`rendered_videos`** — Remotion video render queue
- **`published_videos`** — Social media publish log
- **`ltd_redemption_codes`** — Lifetime deal codes
- **`purchases`** — Subscription history
- **`referrals`** — Referral tracking
- **`lead_magnet_leads`** — Lead capture from public API
- **`user_voice_dna`** — Voice/style learning (disabled by default)

---

## RAG Memory System

3-tier memory buffer for conversation context:

| Tier       | Name              | Content                                                        | Max Size        |
| ---------- | ----------------- | -------------------------------------------------------------- | --------------- |
| **Tier 1** | Raw Exchanges     | FIFO sliding window of last N messages                         | 6 messages      |
| **Tier 2** | Narrative Summary | Compressed arc of recent interactions                          | Dynamic         |
| **Tier 3** | Core Lore (RAG)   | Vector search over `conversation_memories` table with pgvector | Tokens-budgeted |

**RAG pipeline:**

1. Text → Gemini Embeddings (`text-embedding-005`, 768d)
2. Multi-query expansion (3 variants)
3. Hybrid search: vector cosine + sparse lexical expansion
4. MMR reranking for diversity (NumPy-vectorized)
5. Token-budgeted fact selection (LLM importance scoring per fact)
6. Graph triples extraction (entity-relationship for knowledge graph)

---

## Infrastructure

| Component          | Technology                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------ |
| **API Server**     | FastAPI + Uvicorn                                                                                |
| **Database**       | PostgreSQL 16 + pgvector                                                                         |
| **LLM**            | Gemini 3.1 Flash-Lite (primary), Groq Llama 3.3 70B (A/B), OpenRouter Qwen 3.5 9B (experimental) |
| **Auth**           | Firebase Auth + custom JWT fallback                                                              |
| **Payments**       | RevenueCat (subscriptions) + PayU (LTD, India gateway)                                           |
| **Storage**        | OCI Object Storage (temp screenshots, auto-delete after 1 day)                                   |
| **Observability**  | OpenObserver (OTLP logs + metrics + traces), 10% sampling                                        |
| **Monitoring**     | Grafana + Loki + Promtail (Docker Compose)                                                       |
| **Video Pipeline** | Remotion (React → MP4) → FFmpeg audio overlay → Instagram/YouTube auto-publish                   |
| **Dating Audio**   | Trending audio from YouTube via yt-dlp for social posts                                          |
| **Deployment**     | Docker Compose (dev + prod profiles)                                                             |

---

## Key Prompt Architecture

### The "Screenplay Hack"

Instead of a corporate "Dating Coach" persona with 4,500+ tokens of negative rules, the system uses a **Netflix India Screenwriter** roleplay (~1,200 tokens). This reduced token costs by 70% and improved output authenticity.

### Generator Prompt Structure

1. **Phase 1: Strategy** — Read conversation, identify hook point, choose operational strategy
2. **Phase 2: Write** — Generate 4 distinct replies with specific hooks, 6-12 words each
3. **Phase 3: Self-Check** — Verify each reply has a spike, is short, anchored, no AI scaffolds

### Auditor Prompt

Deterministic (temp=0) quality gate checking: context fit, tone safety, direction compliance, cringe, diversity, dialect authenticity.

---

## Data Pipeline (Future ML Training)

Defined in [`features.md`](features.md:1) — captures every generation with:

- Full vision context (OCR, hooks, persona, facts)
- Auditor critique (when rewrites happen)
- Human telemetry (which reply was copied, regenerate events)

Enables SFT (Supervised Fine-Tuning) and DPO (Direct Preference Optimization) dataset creation for future small model distillation (Llama 8B / Qwen 2.5).

---

## Product Hunt Launch Prep

### Key differentiators to highlight:

1. **Multi-agent rewrite loop** — Not just a single LLM call. Vision → Generator → Auditor with quality gate.
2. **Screenplay Hack** — Novel prompt engineering technique (Netflix India Screenwriter persona)
3. **RAG memory** — 3-tier memory buffer with pgvector, MMR reranking, graph extraction
4. **Data pipeline** — Built for model distillation from day one
5. **Remotion video pipeline** — Auto-generate before/after dating advice videos
6. **Lead magnet** — Public API that converts visitors without requiring app install

### Marketing angles:

- "The AI wingman that actually works"
- "Built on a 3-node LangGraph pipeline with an auditor rewrite loop"
- "Gemini-powered dating coach that 3x'd my reply rate"
- "From ₹0 to paying users in India — bootstrapped AI startup story"
