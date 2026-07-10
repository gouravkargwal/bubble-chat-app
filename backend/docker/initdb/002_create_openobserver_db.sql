-- Create the openobserver database for production metadata storage.
-- OpenObserver uses Postgres for metadata (users, dashboards, stream schemas)
-- when ZO_POSTGRES_DSN is set. The actual observability data (logs, traces,
-- metrics) is stored in OpenObserver's internal columnar format, not here.
--
-- Dev environments use SQLite (default) and don't need this.
-- Production environments should set ZO_POSTGRES_DSN in .env.prod:
--   ZO_POSTGRES_DSN=postgres://cookd:cookd@postgres:5432/openobserver

CREATE DATABASE openobserver;
