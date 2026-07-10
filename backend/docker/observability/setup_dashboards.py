#!/usr/bin/env python3
"""
OpenObserver monitoring dashboards setup.

Reads dashboard JSON definitions from the `dashboards/` directory
and creates/updates them in OpenObserver via the REST API.

Auto-loaded on container start via `init-dashboards` service
in docker-compose.yml and docker-compose.prod.yml.

Usage (Docker):
    docker compose --env-file .env.dev up -d   # auto-runs via init-dashboards

Usage (manual):
    export ZO_ROOT_USER_EMAIL=admin@example.com
    export ZO_ROOT_USER_PASSWORD=<your-password>
    python docker/observability/setup_dashboards.py

Environment variables:
    OPENOBSERVER_URL      http://openobserver:5001
    ZO_ORG                default
    ZO_ROOT_USER_EMAIL    (required)
    ZO_ROOT_USER_PASSWORD (required)
    DASHBOARDS_DIR        ./dashboards  (relative to this script)
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Configuration — override with env vars
# ---------------------------------------------------------------------------
OPENOBSERVER_URL = os.getenv("OPENOBSERVER_URL", "http://openobserver:5001")
ZO_ORG = os.getenv("ZO_ORG", "default")
ZO_ROOT_USER_EMAIL = os.getenv("ZO_ROOT_USER_EMAIL")
ZO_ROOT_USER_PASSWORD = os.getenv("ZO_ROOT_USER_PASSWORD")

if not ZO_ROOT_USER_EMAIL or not ZO_ROOT_USER_PASSWORD:
    print("[FATAL] ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD must be set in the environment.")
    print("        These are passed automatically by the init-dashboards Docker service.")
    print("        To run locally: export ZO_ROOT_USER_EMAIL=... ZO_ROOT_USER_PASSWORD=...")
    sys.exit(1)

_SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
DASHBOARDS_DIR = pathlib.Path(os.getenv("DASHBOARDS_DIR", str(_SCRIPT_DIR / "dashboards")))

_BASIC_AUTH = base64.b64encode(
    f"{ZO_ROOT_USER_EMAIL}:{ZO_ROOT_USER_PASSWORD}".encode()
).decode()

HEADERS = {
    "Authorization": f"Basic {_BASIC_AUTH}",
    "Content-Type": "application/json",
}


# =========================================================================
#  Dashboard loading
# =========================================================================

def _load_dashboards() -> list[dict]:
    """Load all dashboard JSON files from DASHBOARDS_DIR, sorted by filename."""
    if not DASHBOARDS_DIR.is_dir():
        print(f"  [ERROR] Dashboards directory not found: {DASHBOARDS_DIR}")
        return []

    json_files = sorted(DASHBOARDS_DIR.glob("*.json"))
    if not json_files:
        print(f"  [ERROR] No JSON files found in {DASHBOARDS_DIR}")
        return []

    dashboards = []
    for fpath in json_files:
        try:
            with open(fpath) as f:
                dashboard = json.load(f)
            # Inject the owner email (from env) into each dashboard
            dashboard["owner"] = ZO_ROOT_USER_EMAIL
            dashboards.append(dashboard)
            print(f"  Loaded: {fpath.name}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [WARN] Skipping {fpath.name}: {e}")

    return dashboards


# =========================================================================
#  API helpers
# =========================================================================

def _api_url(path: str) -> str:
    return f"{OPENOBSERVER_URL}/api/{ZO_ORG}/{path.lstrip('/')}"


def _request(method: str, url: str, body: dict | None = None) -> dict:
    """Make an authenticated HTTP request to the OpenObserver API."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode()
            if resp_body:
                return json.loads(resp_body)
            return {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  [ERROR] HTTP {e.code} for {method} {url}: {e.reason} {error_body[:200]}")
        raise
    except urllib.error.URLError as e:
        print(f"  [ERROR] Connection failed for {url}: {e.reason}")
        raise


def _wait_for_openobserver(max_retries: int = 30, delay: int = 2) -> None:
    """Poll the /health endpoint until OpenObserver is ready."""
    health_url = f"{OPENOBSERVER_URL}/health"
    print(f"Waiting for OpenObserver at {OPENOBSERVER_URL} ...")
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(health_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print("  OpenObserver is ready!")
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        print(f"  Attempt {attempt}/{max_retries} — not ready yet, retrying in {delay}s ...")
        time.sleep(delay)
    print("  [WARN] OpenObserver did not become ready. Continuing anyway ...")


def _dashboard_exists(title: str) -> str | None:
    """Check if a dashboard with the given title already exists. Returns dashboard_id if found."""
    url = _api_url("dashboards")
    try:
        resp = _request("GET", url)
        dashboards = resp.get("dashboards", []) if isinstance(resp, dict) else resp
        for d in dashboards:
            if isinstance(d, dict) and d.get("title") == title:
                return d.get("dashboard_id") or d.get("id")
    except Exception:
        pass
    return None


def _upsert_dashboard(dashboard: dict) -> str:
    """Create or update a dashboard. Returns the dashboard URL."""
    title = dashboard["title"]
    print(f"\n{'=' * 60}")
    print(f"Dashboard: {title}")

    existing_id = _dashboard_exists(title)
    if existing_id:
        print(f"  Dashboard already exists (id={existing_id}). Updating ...")
        url = _api_url(f"dashboards/{existing_id}")
        # PUT requires the current stored hash as a *query param* for
        # optimistic-concurrency, or OpenObserve 500s with "missing or
        # invalid hash value" — it is not part of the JSON body.
        current = _request("GET", url)
        _request("PUT", f"{url}?hash={current.get('hash', '')}", dashboard)
        return f"{OPENOBSERVER_URL}/dashboards/{existing_id}"
    else:
        print(f"  Creating ...")
        url = _api_url("dashboards")
        resp = _request("POST", url, dashboard)
        dashboard_id = resp.get("dashboard_id") or resp.get("id", "unknown")
        return f"{OPENOBSERVER_URL}/dashboards/{dashboard_id}"


# =========================================================================
#  Main
# =========================================================================

def main() -> None:
    print("=" * 60)
    print("  OpenObserver Dashboard Setup")
    print(f"  Server      : {OPENOBSERVER_URL}")
    print(f"  Org         : {ZO_ORG}")
    print(f"  User        : {ZO_ROOT_USER_EMAIL}")
    print(f"  Dashboards  : {DASHBOARDS_DIR}")
    print("=" * 60)

    dashboards = _load_dashboards()
    if not dashboards:
        print("  No dashboards to create. Exiting.")
        sys.exit(1)
    print(f"\nLoaded {len(dashboards)} dashboard definitions")

    _wait_for_openobserver()

    dashboard_urls: list[str] = []
    errors: list[str] = []
    for dashboard in dashboards:
        try:
            url = _upsert_dashboard(dashboard)
            dashboard_urls.append(url)
            print(f"  ✓ {url}")
        except Exception as e:
            errors.append(f"  ✗ {dashboard['title']}: {e}")
            print(f"  ✗ Failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"  Results: {len(dashboard_urls)} created/updated, {len(errors)} failed")
    if dashboard_urls:
        print(f"\n  Dashboard URLs:")
        for url in dashboard_urls:
            print(f"    • {url}")
    if errors:
        print(f"\n  Errors:")
        for err in errors:
            print(f"    {err}")
    print(f"\n  OpenObserver UI: {OPENOBSERVER_URL}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
