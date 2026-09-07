"""
Local SQLite memory store.
New memory writes store redacted content by default. Raw content is opt-in and
policy-gated; encrypted raw storage keeps ciphertext in encrypted_content.
"""

import sqlite3
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from .. import config
from .protection import prepare_content_storage

MemoryType = Literal[
    "project_decision",
    "session_summary",
    "command_history",
    "risk_finding",
    "user_preference",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    source_tool TEXT,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    redacted_content TEXT,
    encrypted_content TEXT,
    raw_storage_mode TEXT DEFAULT 'redacted',
    raw_storage_reason TEXT DEFAULT 'redacted_by_default',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    importance_score REAL DEFAULT 0.5,
    pinned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memory_tags (
    item_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES memory_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_events (
    id TEXT PRIMARY KEY,
    item_id TEXT,
    event_type TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES memory_items(id) ON DELETE SET NULL
);
"""


def _db_path() -> Path:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return config.DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        _migrate_memory_items(conn)


def _migrate_memory_items(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(memory_items)").fetchall()
    }
    if "pinned" not in columns:
        conn.execute("ALTER TABLE memory_items ADD COLUMN pinned INTEGER DEFAULT 0")
    if "encrypted_content" not in columns:
        conn.execute("ALTER TABLE memory_items ADD COLUMN encrypted_content TEXT")
    if "raw_storage_mode" not in columns:
        conn.execute("ALTER TABLE memory_items ADD COLUMN raw_storage_mode TEXT DEFAULT 'legacy_plaintext'")
    if "raw_storage_reason" not in columns:
        conn.execute("ALTER TABLE memory_items ADD COLUMN raw_storage_reason TEXT DEFAULT 'legacy_plaintext_existing_row'")
    conn.execute(
        "UPDATE memory_items SET raw_storage_mode = 'legacy_plaintext' "
        "WHERE raw_storage_mode IS NULL OR raw_storage_mode = ''"
    )
    conn.execute(
        "UPDATE memory_items SET raw_storage_reason = 'legacy_plaintext_existing_row' "
        "WHERE raw_storage_reason IS NULL OR raw_storage_reason = ''"
    )


def insert_item(
    project_path: str,
    memory_type: MemoryType,
    content: str,
    source_tool: Optional[str] = None,
    importance_score: float = 0.5,
    tags: Optional[list[str]] = None,
    pinned: bool = False,
    raw_storage_mode: Optional[str] = None,
) -> str:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())
    storage = prepare_content_storage(content, raw_storage_mode)

    with _conn() as conn:
        conn.execute(
            """INSERT INTO memory_items
               (id, project_path, source_tool, memory_type, content, redacted_content,
                encrypted_content, raw_storage_mode, raw_storage_reason, created_at,
                updated_at, importance_score, pinned)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                project_path,
                source_tool,
                memory_type,
                storage.content,
                storage.redacted_content,
                storage.encrypted_content,
                storage.raw_storage_mode,
                storage.raw_storage_reason,
                now,
                now,
                _bounded_importance(importance_score),
                int(bool(pinned)),
            ),
        )
        for tag in _clean_tags(tags):
            conn.execute(
                "INSERT INTO memory_tags (item_id, tag) VALUES (?, ?)",
                (item_id, tag),
            )
        conn.execute(
            "INSERT INTO memory_events (id, item_id, event_type, details, timestamp) VALUES (?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                item_id,
                "created",
                json.dumps({
                    "item_id": item_id,
                    "raw_storage_mode": storage.raw_storage_mode,
                    "raw_content_stored": storage.raw_content_stored,
                    "encrypted_content_stored": storage.encrypted_content_stored,
                }),
                now,
            ),
        )
    return item_id


def update_item(item_id: str, updates: dict, tags: Optional[list[str]] = None) -> bool:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    values = {}

    if "project_path" in updates:
        values["project_path"] = str(updates["project_path"] or "")
    if "source_tool" in updates:
        source_tool = updates["source_tool"]
        values["source_tool"] = str(source_tool) if source_tool is not None else None
    if "memory_type" in updates:
        values["memory_type"] = str(updates["memory_type"] or "project_decision")
    if "importance_score" in updates:
        values["importance_score"] = _bounded_importance(float(updates["importance_score"]))
    if "pinned" in updates:
        values["pinned"] = int(bool(updates["pinned"]))
    if "content" in updates:
        content = str(updates["content"] or "")
        storage = prepare_content_storage(content, updates.get("raw_storage_mode"))
        values["content"] = storage.content
        values["redacted_content"] = storage.redacted_content
        values["encrypted_content"] = storage.encrypted_content
        values["raw_storage_mode"] = storage.raw_storage_mode
        values["raw_storage_reason"] = storage.raw_storage_reason

    with _conn() as conn:
        exists = conn.execute("SELECT id FROM memory_items WHERE id = ?", (item_id,)).fetchone()
        if not exists:
            return False

        if values or tags is not None:
            values["updated_at"] = now

        if values:
            assignments = ", ".join(f"{column} = ?" for column in values)
            conn.execute(
                f"UPDATE memory_items SET {assignments} WHERE id = ?",
                [*values.values(), item_id],
            )

        if tags is not None:
            conn.execute("DELETE FROM memory_tags WHERE item_id = ?", (item_id,))
            for tag in _clean_tags(tags):
                conn.execute("INSERT INTO memory_tags (item_id, tag) VALUES (?, ?)", (item_id, tag))

        conn.execute(
            "INSERT INTO memory_events (id, item_id, event_type, details, timestamp) VALUES (?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                item_id,
                "updated",
                json.dumps({
                    "item_id": item_id,
                    "raw_storage_mode": values.get("raw_storage_mode"),
                    "raw_content_stored": values.get("raw_storage_mode") in {"plaintext", "legacy_plaintext"},
                    "encrypted_content_stored": bool(values.get("encrypted_content")),
                }),
                now,
            ),
        )
    return True


def delete_item(item_id: str) -> bool:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        exists = conn.execute("SELECT id FROM memory_items WHERE id = ?", (item_id,)).fetchone()
        if not exists:
            return False
        conn.execute(
            "INSERT INTO memory_events (id, item_id, event_type, details, timestamp) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), item_id, "deleted", json.dumps({"item_id": item_id}), now),
        )
        conn.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
    return True


def record_item_event(item_id: str, event_type: str, details: Optional[dict] = None) -> bool:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    payload = {"item_id": item_id}
    payload.update(details or {})
    with _conn() as conn:
        exists = conn.execute("SELECT id FROM memory_items WHERE id = ?", (item_id,)).fetchone()
        if not exists:
            return False
        conn.execute(
            "INSERT INTO memory_events (id, item_id, event_type, details, timestamp) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), item_id, event_type, json.dumps(payload), now),
        )
    return True


def _clean_tags(tags: Optional[list[str]]) -> list[str]:
    clean = []
    seen = set()
    for tag in tags or []:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        clean.append(value)
        seen.add(value)
    return clean


def _bounded_importance(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
