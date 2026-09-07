import json
from collections import Counter
from typing import Optional

from ..dlp import redact_text
from .retrieve import _with_tags
from .store import _conn, init_db


def memory_timeline(
    project_path: Optional[str] = None,
    item_id: Optional[str] = None,
    limit: int = 100,
) -> dict:
    init_db()
    limit = max(1, min(int(limit), 500))
    query = """
        SELECT
            memory_events.id,
            memory_events.item_id,
            memory_events.event_type,
            memory_events.details,
            memory_events.timestamp,
            memory_items.project_path,
            memory_items.source_tool,
            memory_items.memory_type,
            memory_items.content,
            memory_items.redacted_content,
            memory_items.created_at,
            memory_items.updated_at,
            memory_items.importance_score,
            memory_items.pinned,
            GROUP_CONCAT(memory_tags.tag, ',') AS tags_csv
        FROM memory_events
        LEFT JOIN memory_items ON memory_items.id = memory_events.item_id
        LEFT JOIN memory_tags ON memory_tags.item_id = memory_items.id
        WHERE 1=1
    """
    params: list = []
    if project_path:
        query += " AND memory_items.project_path = ?"
        params.append(project_path)
    if item_id:
        query += " AND (memory_events.item_id = ? OR memory_events.details LIKE ?)"
        params.extend([item_id, f'%"{item_id}"%'])
    query += " GROUP BY memory_events.id ORDER BY memory_events.timestamp DESC LIMIT ?"
    params.append(limit)

    with _conn() as conn:
        rows = [dict(row) for row in conn.execute(query, params).fetchall()]

    events = [_timeline_event(row) for row in rows]
    counts = Counter(event["event_type"] for event in events)
    return {
        "event_count": len(events),
        "limit": limit,
        "project_path": project_path,
        "item_id": item_id,
        "by_event_type": dict(sorted(counts.items())),
        "events": events,
    }


def _timeline_event(row: dict) -> dict:
    item = _item(row) if row.get("project_path") else None
    details = _safe_details(row.get("details"))
    event_type = str(row.get("event_type") or "unknown")
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "event_type": event_type,
        "item_id": row.get("item_id") or details.get("item_id"),
        "project_path": row.get("project_path"),
        "memory_type": row.get("memory_type"),
        "source_tool": row.get("source_tool"),
        "summary": _summary(event_type, row, item, details),
        "details": details,
        "item": item,
    }


def _item(row: dict) -> dict:
    item = _with_tags(dict(row))
    content = item.get("redacted_content") or redact_text(item.get("content") or "")
    return {
        "id": item["item_id"],
        "project_path": item["project_path"],
        "source_tool": item.get("source_tool"),
        "memory_type": item["memory_type"],
        "content": redact_text(content),
        "updated_at": item["updated_at"],
        "importance_score": float(item.get("importance_score") or 0.5),
        "tags": item.get("tags", []),
        "pinned": bool(item.get("pinned")),
        "stale": bool(item.get("stale")),
        "stale_reason": item.get("stale_reason"),
    }


def _summary(event_type: str, row: dict, item: Optional[dict], details: dict) -> str:
    memory_type = row.get("memory_type") or "memory item"
    source = row.get("source_tool") or details.get("client") or details.get("source_tool") or "unknown"
    if event_type == "attached":
        route = details.get("route") or "model call"
        return redact_text(f"attached {memory_type} for {source} via {route}")
    if event_type == "deleted":
        return "deleted memory item"
    if event_type == "created":
        return redact_text(f"created {memory_type} from {source}{_snippet(item)}")
    if event_type == "updated":
        return redact_text(f"updated {memory_type} from {source}{_snippet(item)}")
    return redact_text(f"{event_type} {memory_type} from {source}{_snippet(item)}")


def _snippet(item: Optional[dict]) -> str:
    if not item:
        return ""
    text = str(item.get("content") or "").replace("\n", " ").strip()
    if not text:
        return ""
    if len(text) > 96:
        text = text[:93].rstrip() + "..."
    return f": {text}"


def _safe_details(value) -> dict:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except Exception:
        return {"raw": redact_text(str(value))}
    if not isinstance(decoded, dict):
        return {"value": _redact_nested(decoded)}
    return {str(key): _redact_nested(item) for key, item in decoded.items()}


def _redact_nested(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_nested(item) for key, item in value.items()}
    return value
