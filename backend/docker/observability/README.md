# OpenObserver Monitoring Dashboards

Six purpose-built dashboards for monitoring the RizzBot API in OpenObserver.

## Dashboards

### 1. API Health (RED)
**Purpose:** Service-level health for every endpoint.
- Request rate (rps) by endpoint & status
- Error rate (4xx vs 5xx) stacked view
- p50/p95/p99 latency per endpoint
- Health check status gauge

### 2. LLM Performance
**Purpose:** AI model cost, latency, and reliability.
- Call rate by model & operation (generator, vision, auditor, embedding)
- Latency distributions (p50, p95, p99) | critical — 429/503 fallback typically adds 3–5 s
- Token consumption: input vs output per model
- Accumulated cost ($USD) per model
- Fallback activation count (primary→fallback, by reason)

### 3. Business KPIs
**Purpose:** Core product metrics that drive engineering decisions.
- Profile audit jobs (success / failed / cached / skipped)
- Blueprint generations (success / failed / cached)
- Cache hit ratio (hits / misses by layer)
- Tier allocation distribution (free → paid model mapping)
- Notification delivery failures (by channel + reason)

### 4. Infrastructure & Errors
**Purpose:** Saturation, upstream health, and error taxonomy.
- DB pool connections in use (percent of pool)
- Active audit worker count
- Gemini upstream health (vision + embedding probes, 1 = healthy)
- Synthetic probe latency (how fast is Gemini right now?)
- Error breakdown by layer (api / llm / db / auth / agent / infra)
- Error breakdown by severity (fatal / transient / throttle / latent)

### 5. Distributed Traces
**Purpose:** End-to-end trace analysis for latency debugging.
- Trace duration heatmap (count of traces by duration bucket)
- Slowest traces table (sorted by duration, expand to see waterfall)
- p50/p95/p99 trace duration over time
- Error traces list (trace_id, route, status, duration)
- Service dependency graph hint (traces flowing: incoming → fastapi → httpx → gemini)

### 6. Synthetic Monitoring
**Purpose:** Proactive health checks before users feel pain.
- Gemini vision probe (pass/fail per check)
- Gemini embedding probe (pass/fail per check)
- Probe duration (ms) per upstream
- Consecutive failure counter (alert threshold → 3)

---

## Setup

```bash
# 1. Ensure OpenObserver is running
docker compose -f docker-compose.yml up -d openobserver

# 2. Run the setup script
python docker/observability/setup_dashboards.py
```

The script will:
1. Wait for OpenObserver to be ready (poll `/health`)
2. Authenticate with the credentials from `ZO_ROOT_USER_EMAIL` + `ZO_ROOT_USER_PASSWORD`
3. Create all 6 dashboards via the OpenObserver REST API
4. Print dashboard URLs for direct access

## Customisation

- **Time range:** OpenObserver defaults to "Last 15 minutes". Adjust per panel.
- **Refresh interval:** Each dashboard auto-refreshes every 30 s.
- **Variables:** Some dashboards accept `$model`, `$endpoint`, `$severity` variables (set in dashboard settings).
