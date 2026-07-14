# OpenObserver Setup Guide

OpenObserver provides unified observability (logs, metrics, traces) in a single binary.

## Quick Start (Development)

```bash
# Start services
docker-compose up -d

# OpenObserver will be available at http://localhost:5001
# API traces/logs/metrics are automatically sent to OpenObserver
```

## Configuration

### Environment Variables (.env.dev / .env.prod)

| Variable                    | Description                                                  | Required                  |
| --------------------------- | ------------------------------------------------------------ | ------------------------- |
| `OPENOBSERVER_ENDPOINT`     | URL of OpenObserver service (default: http://localhost:5001) | No (uses default)         |
| `OPENOBSERVER_API_KEY`      | API key for authentication                                   | Yes (production)          |
| `OPENOBSERVER_SERVICE_NAME` | Service name in traces/metrics                               | No (default: rizzbot-api) |
| `OTLP_ENABLED`              | Enable OpenTelemetry export                                  | No (default: true)        |
| `OTLP_SAMPLE_RATE`          | Sampling rate for traces (0.0-1.0)                           | No (default: 0.1)         |

### Production Setup

1. Set `OPENOBSERVER_API_KEY` in `.env.prod`:

   ```
   OPENOBSERVER_API_KEY=your-secure-api-key-here
   ```

2. Secure OpenObserver with a reverse proxy (nginx, caddy, etc.) for HTTPS

3. For HA/production, consider:
   - Using PostgreSQL backend instead of SQLite (update config.yaml)
   - Setting up proper retention policies
   - Configuring authentication

## Endpoints

- **Traces**: `http://localhost:5001/api/default/v1/traces`
- **Metrics**: `http://localhost:5001/api/default/v1/metrics`
- **Logs**: `http://localhost:5001/api/default/v1/logs`
- **Health**: `http://localhost:5001/health`

## Features

### Distributed Tracing

- Automatic FastAPI request tracing
- HTTPX client instrumentation (LLM calls)
- Correlation with logs via trace_id

### Metrics

- Prometheus-compatible metrics via `/metrics` endpoint
- RED metrics (Rate, Errors, Duration) for HTTP
- LLM usage and cost metrics
- Business metrics (audits, blueprints)

### Logs

- Structured JSON logs with OpenTelemetry integration
- Automatic trace-log correlation
- Sentry integration for error alerting (optional)

## Migration from Grafana Stack

The old Grafana/Prometheus/Loki stack has been removed:

| Old Service            | New Service               |
| ---------------------- | ------------------------- |
| Loki (logs)            | OpenObserver OTLP Logs    |
| Prometheus (metrics)   | OpenObserver OTLP Metrics |
| Grafana (UI)           | OpenObserver Built-in UI  |
| Promtail (log shipper) | OpenTelemetry Python SDK  |

Your existing dashboards can be recreated in OpenObserver's dashboard UI.
