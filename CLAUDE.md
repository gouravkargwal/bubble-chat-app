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

# Cookd — Complete Agent Reference

## Project Structure

```
cookd/
├── backend/                          # FastAPI + LangGraph backend
│   ├── app/
│   │   ├── api/v1/                   # All REST endpoints
│   │   │   ├── vision_v2.py          # Core generation endpoint (964 lines)
│   │   │   ├── auth.py               # Firebase + JWT auth
│   │   │   ├── billing.py            # RevenueCat + PayU LTD
│   │   │   ├── conversations.py      # CRUD for chat threads
│   │   │   ├── history.py            # User interaction history
│   │   │   ├── track.py              # Copy/rating tracking with embeddings
│   │   │   ├── telemetry.py          # Data pipeline telemetry
│   │   │   ├── referral.py           # Referral system
│   │   │   ├── users.py              # User preferences & deletion
│   │   │   ├── public.py             # Lead magnet (no auth)
│   │   │   ├── webhooks.py           # RevenueCat + PayU webhooks
│   │   │   ├── video_crud.py         # Remotion video CRUD
│   │   │   ├── video_export.py       # Video file export
│   │   │   ├── publish.py            # Post Wizard (caption gen + auto-publish)
│   │   │   ├── audio_preview.py      # YouTube audio preview proxy
│   │   │   ├── usage.py              # Usage stats for users
│   │   │   ├── endpoints/
│   │   │   │   └── profile_optimizer.py  # Profile blueprint analysis
│   │   │   ├── routers/
│   │   │   │   └── profile_auditor_routes.py  # Photo audit
│   │   │   └── schemas/schemas.py    # All pydantic request/response models
│   │   ├── agent/                    # LangGraph multi-agent pipeline
│   │   │   ├── graph_v2.py           # 3-node StateGraph definition
│   │   │   ├── state.py              # AgentState type
│   │   │   └── nodes_v2/
│   │   │       ├── _vision.py        # Screenshot analysis node
│   │   │       ├── _generator.py     # Reply generation node
│   │   │       ├── _auditor.py       # Quality evaluation node
│   │   │       ├── _personality.py   # Archetype derivation
│   │   │       ├── _post_processor.py# Deterministic cleanup
│   │   │       ├── _lc_usage.py      # LangChain Gemini integration
│   │   │       └── _shared.py        # Constants, image helpers, prompts
│   │   ├── prompts/                  # All LLM prompt templates
│   │   │   ├── generator.py          # Screenplay/Coach generator prompts
│   │   │   ├── auditor.py            # Quality auditor prompts
│   │   │   ├── vision_api.py         # Vision analysis prompts
│   │   │   ├── profile_auditor.py    # Photo audit prompts
│   │   │   ├── profile_optimizer.py  # Blueprint prompts
│   │   │   ├── llm_judge.py          # Prompt eval judge
│   │   │   ├── temperature.py        # Dynamic temperature config
│   │   │   ├── prompt_fragments.py   # Shared prompt fragments
│   │   │   └── templates/playbooks.py# Strategy playbook templates
│   │   ├── services/                 # Business logic services
│   │   │   ├── memory_service.py     # 3-tier RAG memory (916 lines)
│   │   │   ├── rag_improvements.py   # MMR, token budgeting, graph extraction
│   │   │   ├── quota_manager.py      # Credits-based quota system
│   │   │   ├── billing.py            # Plan upgrade logic
│   │   │   ├── lead_magnet_service.py# Lead magnet rate limiting + caching
│   │   │   ├── hybrid_stitch_pending.py  # Multi-screenshot stitching
│   │   │   ├── audit_worker.py       # Background audit processing
│   │   │   ├── profile_optimizer_service.py
│   │   │   ├── social_poster.py      # Instagram + YouTube auto-publish
│   │   │   ├── audio_overlay.py      # FFmpeg audio overlay
│   │   │   ├── trending_audio.py     # YouTube trending audio fetcher
│   │   │   └── audio_overlay.py
│   │   ├── infrastructure/           # Cross-cutting concerns
│   │   │   ├── database/models.py    # All SQLAlchemy models (792 lines)
│   │   │   ├── auth/firebase.py      # Firebase admin SDK
│   │   │   ├── auth/jwt.py           # Custom JWT implementation
│   │   │   ├── billing/              # RevenueCat integration
│   │   │   ├── otel_logging.py       # OpenObserver OTLP export
│   │   │   ├── tracing.py           # PyInstrument profiling
│   │   │   ├── metrics.py           # Prometheus metrics
│   │   │   ├── ratelimit.py         # SlowAPI rate limiter
│   │   │   ├── oci_storage.py       # OCI object storage
│   │   │   └── security_headers.py  # Security middleware
│   │   ├── domain/                   # Domain models
│   │   │   ├── tiers.py             # Tier hierarchy + access control
│   │   │   ├── conversation.py      # Conversation context builder
│   │   │   ├── voice_dna.py         # Voice DNA domain model
│   │   │   └── models.py            # AnalysisResult domain model
│   │   ├── core/
│   │   │   ├── tier_config.py       # Master tier config (all limits + features)
│   │   │   ├── embeddings.py        # Gemini text embeddings
│   │   │   └── reranker.py          # FlashRank cross-encoder reranker
│   │   ├── llm/                      # LLM client layer
│   │   │   ├── gemini_client.py     # HTTP-based Gemini client with fallback
│   │   │   ├── genai.py             # Google GenAI SDK wrapper
│   │   │   ├── base.py              # Base LLM interface
│   │   │   └── gemini_pricing.py    # Token cost calculator
│   │   ├── testing/                  # Prompt evaluation framework
│   │   │   ├── runner.py            # Eval runner
│   │   │   ├── reporter.py          # Eval report generator
│   │   │   ├── cache.py             # Eval cache
│   │   │   └── evaluators/rule_based.py  # Rule-based eval checks
│   │   └── config.py                # Pydantic Settings (all env vars)
│   ├── scripts/                      # Utility scripts
│   │   ├── eval_scenario.py         # Multi-turn scenario evaluation
│   │   └── audio_video_factory.py   # Batch video generation
│   └── tests/                        # Test suite
│       ├── test_auth.py
│       ├── test_track.py
│       ├── test_history.py
│       ├── test_referral.py
│       ├── test_webhooks.py
│       ├── test_promo.py
│       ├── test_evaluators.py
│       ├── test_gemini_client_fallback.py
│       └── test_gemini_client_integration.py
├── landing-page/                     # Next.js landing page
│   └── src/
│       ├── app/
│       │   ├── layout.tsx           # Root layout with JSON-LD, PostHog, fonts
│       │   ├── page.tsx             # Landing page (server component → ClientShell)
│       │   ├── admin/page.tsx       # Admin video pipeline dashboard (519 lines)
│       │   ├── blog/                # Blog with 6 articles
│       │   ├── contact/page.tsx     # Contact form + FAQ
│       │   ├── privacy/terms/child-safety/delete-account/  # Legal pages
│       │   ├── ltd/                 # LTD checkout pages
│       │   ├── sitemap.ts           # Auto-generated sitemap
│       │   └── robots.ts            # Robots config
│       ├── components/
│       │   ├── interactive-hero/    # Lead magnet upload widget
│       │   ├── admin/               # Admin dashboard (Remotion pipeline)
│       │   ├── ClientShell.tsx      # Main client wrapper with lazy loading
│       │   ├── Features.tsx         # Feature grid
│       │   ├── Pricing.tsx          # Pricing cards + LTD modal
│       │   ├── CTA.tsx              # Download CTA section
│       │   └── ...
│       └── middleware.ts            # Clerk admin auth
├── RizzBotV2/                       # Android app (Kotlin)
├── design-system/                   # Brand tokens
└── *.md                             # Documentation
```

## Key Architectural Decisions

1. **Credits over rate-limits** — Users spend credits (1/gen, 8/audit, 12/blueprint). Free gets 10 signup + 1/day. Paid gets period pools.
2. **Screenplay Hack** — Netflix India Screenwriter persona reduced prompt tokens by 70% vs traditional Dating Coach prompt.
3. **Auditor rewrite loop** — Max 1 rewrite cycle (2 total generations). Ships after that even if imperfect.
4. **OCI temp storage** — Screenshots uploaded to OCI, auto-delete after 1 day via lifecycle policy.
5. **OpenObserver** — Single vendor for logs + metrics + traces via OTLP. 10% sampling in production.
6. **3-tier RAG** — Raw exchanges (FIFO 6) → Narrative summary → Vector search with MMR reranking.

## Environment Variables

See [`backend/app/config.py`](backend/app/config.py:1) for complete list. Key ones:

| Variable             | Purpose                       |
| -------------------- | ----------------------------- |
| `GEMINI_API_KEY`     | Primary LLM provider          |
| `GENERATOR_PROVIDER` | "gemini" or "groq" (A/B test) |
| `PROMPT_MODE`        | "screenplay" or "coach"       |
| `DATABASE_URL`       | PostgreSQL async URL          |
| `ENVIRONMENT`        | "development" or "production" |
| `OTLP_ENABLED`       | OpenObserver telemetry        |

## Common Tasks

### Run backend locally

```bash
cd backend && docker compose up -d --build
```

### Run eval scenarios

```bash
cd backend && PYTHONPATH=. python scripts/eval_scenario.py
```

### Build Android

```bash
cd RizzBotV2 && ./gradlew assembleStagingDebug
```
