"""SQLite cache for eval results — skips scenarios already scored."""

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

_DB_PATH = Path(__file__).parent / "eval_cache.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS eval_results (
            scenario_id     TEXT NOT NULL,
            variant_id      TEXT NOT NULL,
            run_index       INTEGER NOT NULL,
            scenario_hash   TEXT NOT NULL,
            replies         TEXT NOT NULL,
            judge_report    TEXT,
            auditor_passes  INTEGER,
            auditor_feedback TEXT DEFAULT '',
            latency_ms      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (scenario_id, variant_id, run_index, scenario_hash)
        )
    """)
    con.commit()
    return con


def scenario_hash(scenario_dict: dict) -> str:
    """Hash scenario content — if scenario changes, cache miss forces re-run."""
    stable = json.dumps(scenario_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(stable.encode()).hexdigest()[:16]


def get(scenario_id: str, variant_id: str, run_index: int, s_hash: str) -> dict | None:
    """Return cached row dict, or None on miss."""
    con = _connect()
    row = con.execute(
        "SELECT * FROM eval_results WHERE scenario_id=? AND variant_id=? AND run_index=? AND scenario_hash=?",
        (scenario_id, variant_id, run_index, s_hash),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def put(
    scenario_id: str,
    variant_id: str,
    run_index: int,
    s_hash: str,
    replies: list[str],
    judge_report_dict: dict | None,
    auditor_passes: bool | None,
    auditor_feedback: str,
    latency_ms: int,
) -> None:
    """Insert or replace a result row."""
    con = _connect()
    con.execute(
        """
        INSERT OR REPLACE INTO eval_results
            (scenario_id, variant_id, run_index, scenario_hash,
             replies, judge_report, auditor_passes, auditor_feedback, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scenario_id,
            variant_id,
            run_index,
            s_hash,
            json.dumps(replies),
            json.dumps(judge_report_dict) if judge_report_dict else None,
            int(auditor_passes) if auditor_passes is not None else None,
            auditor_feedback,
            latency_ms,
        ),
    )
    con.commit()
    con.close()


def clear(scenario_id: str | None = None, variant_id: str | None = None) -> int:
    """Delete cache rows. Pass both args to clear one combo, neither to clear all."""
    con = _connect()
    if scenario_id and variant_id:
        cur = con.execute(
            "DELETE FROM eval_results WHERE scenario_id=? AND variant_id=?",
            (scenario_id, variant_id),
        )
    elif scenario_id:
        cur = con.execute("DELETE FROM eval_results WHERE scenario_id=?", (scenario_id,))
    else:
        cur = con.execute("DELETE FROM eval_results")
    count = cur.rowcount
    con.commit()
    con.close()
    return count
