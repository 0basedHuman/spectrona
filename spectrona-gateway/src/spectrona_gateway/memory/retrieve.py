"""Basic memory retrieval. No vector search — plain SQL only for now."""

from typing import Optional

from .staleness import annotate_item
from .store import _conn, init_db


def list_items(
    project_path: Optional[str] = None,
    memory_type: Optional[str] = None,
    source_tool: Optional[str] = None,
    tag: Optional[str] = None,
    query_text: Optional[str] = None,
    pinned: Optional[bool] = None,
    limit: int = 50,
) -> list[dict]:
    init_db()
    query = """
        SELECT memory_items.*,
               GROUP_CONCAT(memory_tags.tag, ',') AS tags_csv,
               (
                 SELECT MAX(memory_events.timestamp)
                 FROM memory_events
                 WHERE memory_events.item_id = memory_items.id
                   AND memory_events.event_type = 'attached'
               ) AS last_attached_at
        FROM memory_items
        LEFT JOIN memory_tags ON memory_tags.item_id = memory_items.id
        WHERE 1=1
    """
    params: list = []
    if project_path:
        query += " AND memory_items.project_path = ?"
        params.append(project_path)
    if memory_type:
        query += " AND memory_items.memory_type = ?"
        params.append(memory_type)
    if source_tool:
        query += " AND memory_items.source_tool = ?"
        params.append(source_tool)
    if pinned is not None:
        query += " AND memory_items.pinned = ?"
        params.append(1 if pinned else 0)
    if tag:
        query += """
            AND EXISTS (
                SELECT 1 FROM memory_tags tag_filter
                WHERE tag_filter.item_id = memory_items.id
                  AND tag_filter.tag = ?
            )
        """
        params.append(tag)
    if query_text:
        needle = f"%{query_text.lower()}%"
        query += """
            AND (
                LOWER(COALESCE(memory_items.redacted_content, '')) LIKE ?
                OR LOWER(memory_items.memory_type) LIKE ?
                OR LOWER(COALESCE(memory_items.source_tool, '')) LIKE ?
                OR EXISTS (
                    SELECT 1 FROM memory_tags search_tags
                    WHERE search_tags.item_id = memory_items.id
                      AND LOWER(search_tags.tag) LIKE ?
                )
            )
        """
        params.extend([needle, needle, needle, needle])
    query += " GROUP BY memory_items.id ORDER BY memory_items.pinned DESC, memory_items.updated_at DESC LIMIT ?"
    params.append(limit)

    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_with_tags(dict(r)) for r in rows]


def get_item(item_id: str) -> Optional[dict]:
    init_db()
    query = """
        SELECT memory_items.*,
               GROUP_CONCAT(memory_tags.tag, ',') AS tags_csv,
               (
                 SELECT MAX(memory_events.timestamp)
                 FROM memory_events
                 WHERE memory_events.item_id = memory_items.id
                   AND memory_events.event_type = 'attached'
               ) AS last_attached_at
        FROM memory_items
        LEFT JOIN memory_tags ON memory_tags.item_id = memory_items.id
        WHERE memory_items.id = ?
        GROUP BY memory_items.id
    """
    with _conn() as conn:
        row = conn.execute(query, (item_id,)).fetchone()
    return _with_tags(dict(row)) if row else None


def list_events(item_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    init_db()
    query = "SELECT * FROM memory_events WHERE 1=1"
    params: list = []
    if item_id:
        query += " AND item_id = ?"
        params.append(item_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def _with_tags(row: dict) -> dict:
    tags_csv = row.pop("tags_csv", "") or ""
    row["tags"] = [tag for tag in tags_csv.split(",") if tag]
    row["pinned"] = bool(row.get("pinned"))
    return annotate_item(row)
