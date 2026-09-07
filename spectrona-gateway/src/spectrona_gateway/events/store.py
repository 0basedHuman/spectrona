import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .. import config
from ..dlp import redact_text


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    route TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    model TEXT,
    client TEXT,
    project_path TEXT,
    action TEXT NOT NULL,
    policy_action TEXT,
    policy_rule_id TEXT,
    dlp_findings_count INTEGER DEFAULT 0,
    estimated_input_chars INTEGER DEFAULT 0,
    request_tokens INTEGER DEFAULT 0,
    response_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    status_code INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_runtime_events_timestamp
    ON runtime_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_runtime_events_provider
    ON runtime_events(provider_type);
CREATE INDEX IF NOT EXISTS idx_runtime_events_client
    ON runtime_events(client);
CREATE INDEX IF NOT EXISTS idx_runtime_events_project
    ON runtime_events(project_path);
CREATE INDEX IF NOT EXISTS idx_runtime_events_action
    ON runtime_events(action);
"""


def _db_path() -> Path:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return config.DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        _migrate_runtime_events(conn)


def _migrate_runtime_events(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(runtime_events)").fetchall()
    }
    if "project_path" not in columns:
        conn.execute("ALTER TABLE runtime_events ADD COLUMN project_path TEXT")


def record_model_event(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    project_path: str,
    action: str,
    policy_action: str,
    policy_rule_id: str,
    dlp_findings_count: int,
    estimated_input_chars: int,
    request_tokens: int,
    response_tokens: int,
    total_tokens: int,
    latency_ms: int,
    status_code: int,
) -> str:
    init_db()
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO runtime_events (
                id, timestamp, event_type, route, provider_type, model, client,
                project_path, action, policy_action, policy_rule_id, dlp_findings_count,
                estimated_input_chars, request_tokens, response_tokens,
                total_tokens, latency_ms, status_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                now,
                "model_call",
                route,
                provider_type,
                redact_text(model),
                redact_text(client),
                redact_text(project_path),
                action,
                policy_action,
                redact_text(policy_rule_id),
                max(0, int(dlp_findings_count)),
                max(0, int(estimated_input_chars)),
                max(0, int(request_tokens)),
                max(0, int(response_tokens)),
                max(0, int(total_tokens)),
                max(0, int(latency_ms)),
                max(0, int(status_code)),
            ),
        )
    return event_id


def list_events(
    limit: int = 100,
    provider_type: Optional[str] = None,
    client: Optional[str] = None,
    project_path: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[dict]:
    init_db()
    query = "SELECT * FROM runtime_events WHERE 1=1"
    params: list = []
    if provider_type:
        query += " AND provider_type = ?"
        params.append(provider_type)
    if client:
        query += " AND client = ?"
        params.append(client)
    if project_path:
        query += " AND project_path = ?"
        params.append(project_path)
    if action:
        query += " AND action = ?"
        params.append(action)
    if since:
        query += " AND timestamp >= ?"
        params.append(since)
    if until:
        query += " AND timestamp <= ?"
        params.append(until)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def token_usage_summary() -> dict:
    init_db()
    today_key = datetime.now(timezone.utc).date().isoformat()
    successful_where = "event_type = 'model_call' AND status_code < 400"
    with _conn() as conn:
        totals = _usage_totals(conn, successful_where)
        today = _usage_totals(conn, f"{successful_where} AND substr(timestamp, 1, 10) = ?", [today_key])
        by_provider = _group_usage(conn, "provider_type")
        by_model = _group_usage(conn, "model")
        by_client = _group_usage(conn, "client")
        by_route = _group_usage(conn, "route")
        by_day = _group_usage_by_day(conn)

    return {
        "request_tokens": int(totals["request_tokens"]),
        "response_tokens": int(totals["response_tokens"]),
        "total_tokens": int(totals["total_tokens"]),
        "events": int(totals["events"]),
        "today": {
            "date": today_key,
            "request_tokens": int(today["request_tokens"]),
            "response_tokens": int(today["response_tokens"]),
            "total_tokens": int(today["total_tokens"]),
            "events": int(today["events"]),
        },
        "by_provider": by_provider,
        "by_model": by_model,
        "by_client": by_client,
        "by_route": by_route,
        "by_day": by_day,
    }


def block_summary(limit: int = 10) -> dict:
    init_db()
    where = (
        "event_type = 'model_call' AND "
        "(action IN ('blocked', 'approval_required') "
        "OR action LIKE 'would_block%' "
        "OR action LIKE 'would_response_block%' "
        "OR action LIKE 'would_require_approval%' "
        "OR action LIKE 'would_response_require_approval%' "
        "OR policy_action IN ('deny', 'require_approval') "
        "OR status_code = 403)"
    )
    with _conn() as conn:
        totals = conn.execute(
            f"""SELECT
                    COUNT(*) AS events,
                    COALESCE(SUM(CASE
                        WHEN action = 'blocked' OR policy_action = 'deny' THEN 1
                        ELSE 0
                    END), 0) AS blocked,
                    COALESCE(SUM(CASE
                        WHEN action = 'approval_required' OR policy_action = 'require_approval' THEN 1
                        ELSE 0
                    END), 0) AS approval_required,
                    COALESCE(SUM(CASE
                        WHEN action LIKE 'would_block%' OR action LIKE 'would_response_block%' THEN 1
                        ELSE 0
                    END), 0) AS would_blocked,
                    COALESCE(SUM(CASE
                        WHEN action LIKE 'would_require_approval%' OR action LIKE 'would_response_require_approval%' THEN 1
                        ELSE 0
                    END), 0) AS would_approval_required
                FROM runtime_events
                WHERE {where}"""
        ).fetchone()
        recent = _recent_matching_events(conn, where, limit)
        by_rule = _group_event_counts(conn, where, "policy_rule_id")
        by_client = _group_event_counts(conn, where, "client")
        by_route = _group_event_counts(conn, where, "route")

    return {
        "events": int(totals["events"]),
        "blocked": int(totals["blocked"]),
        "approval_required": int(totals["approval_required"]),
        "would_blocked": int(totals["would_blocked"]),
        "would_approval_required": int(totals["would_approval_required"]),
        "by_rule": by_rule,
        "by_client": by_client,
        "by_route": by_route,
        "recent": recent,
    }


def dlp_summary(limit: int = 10) -> dict:
    init_db()
    where = "event_type = 'model_call' AND dlp_findings_count > 0"
    with _conn() as conn:
        totals = conn.execute(
            f"""SELECT
                    COUNT(*) AS events,
                    COALESCE(SUM(dlp_findings_count), 0) AS findings,
                    COALESCE(SUM(CASE
                        WHEN action LIKE 'redacted%' OR policy_action = 'redact' THEN 1
                        ELSE 0
                    END), 0) AS redacted_events,
                    COALESCE(SUM(CASE
                        WHEN action LIKE 'would_redact%' OR action LIKE 'would_response_redact%'
                            OR policy_action = 'dry_run_redact' THEN 1
                        ELSE 0
                    END), 0) AS would_redact_events,
                    COALESCE(SUM(CASE
                        WHEN status_code >= 400 THEN 1
                        ELSE 0
                    END), 0) AS blocked_events
                FROM runtime_events
                WHERE {where}"""
        ).fetchone()
        recent = _recent_matching_events(conn, where, limit)
        by_provider = _group_event_counts(conn, where, "provider_type")
        by_client = _group_event_counts(conn, where, "client")
        by_route = _group_event_counts(conn, where, "route")

    return {
        "events": int(totals["events"]),
        "findings": int(totals["findings"]),
        "redacted_events": int(totals["redacted_events"]),
        "would_redact_events": int(totals["would_redact_events"]),
        "blocked_events": int(totals["blocked_events"]),
        "by_provider": by_provider,
        "by_client": by_client,
        "by_route": by_route,
        "recent": recent,
    }


def _group_usage(conn: sqlite3.Connection, field: str) -> list[dict]:
    rows = conn.execute(
        f"""SELECT
                {field} AS key,
                COALESCE(SUM(request_tokens), 0) AS request_tokens,
                COALESCE(SUM(response_tokens), 0) AS response_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COUNT(*) AS events
            FROM runtime_events
            WHERE event_type = 'model_call' AND status_code < 400
            GROUP BY {field}
            ORDER BY total_tokens DESC, key ASC"""
    ).fetchall()
    return [
        {
            "key": row["key"] or "unknown",
            "request_tokens": int(row["request_tokens"]),
            "response_tokens": int(row["response_tokens"]),
            "total_tokens": int(row["total_tokens"]),
            "events": int(row["events"]),
        }
        for row in rows
    ]


def _group_usage_by_day(conn: sqlite3.Connection, limit: int = 14) -> list[dict]:
    rows = conn.execute(
        """SELECT
                substr(timestamp, 1, 10) AS key,
                COALESCE(SUM(request_tokens), 0) AS request_tokens,
                COALESCE(SUM(response_tokens), 0) AS response_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COUNT(*) AS events
            FROM runtime_events
            WHERE event_type = 'model_call' AND status_code < 400
            GROUP BY substr(timestamp, 1, 10)
            ORDER BY key DESC
            LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()
    return [
        {
            "key": row["key"] or "unknown",
            "request_tokens": int(row["request_tokens"]),
            "response_tokens": int(row["response_tokens"]),
            "total_tokens": int(row["total_tokens"]),
            "events": int(row["events"]),
        }
        for row in rows
    ]


def _usage_totals(conn: sqlite3.Connection, where: str, params: Optional[list] = None) -> sqlite3.Row:
    return conn.execute(
        f"""SELECT
                COALESCE(SUM(request_tokens), 0) AS request_tokens,
                COALESCE(SUM(response_tokens), 0) AS response_tokens,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COUNT(*) AS events
            FROM runtime_events
            WHERE {where}""",
        params or [],
    ).fetchone()


def _group_event_counts(conn: sqlite3.Connection, where: str, field: str) -> list[dict]:
    rows = conn.execute(
        f"""SELECT
                {field} AS key,
                COUNT(*) AS events,
                COALESCE(SUM(dlp_findings_count), 0) AS dlp_findings
            FROM runtime_events
            WHERE {where}
            GROUP BY {field}
            ORDER BY events DESC, key ASC"""
    ).fetchall()
    return [
        {
            "key": row["key"] or "unknown",
            "events": int(row["events"]),
            "dlp_findings": int(row["dlp_findings"]),
        }
        for row in rows
    ]


def _recent_matching_events(conn: sqlite3.Connection, where: str, limit: int) -> list[dict]:
    rows = conn.execute(
        f"""SELECT
                id, timestamp, route, provider_type, model, client, action,
                policy_action, policy_rule_id, dlp_findings_count, status_code
            FROM runtime_events
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT ?""",
        (max(1, int(limit)),),
    ).fetchall()
    return [dict(row) for row in rows]
