from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from ..dlp import findings_count, redact_text
from .retrieve import list_items


_TYPE_LABELS = {
    "project_decision": "Project Decisions",
    "session_summary": "Session Summaries",
    "command_history": "Command History",
    "risk_finding": "Risk Findings",
    "user_preference": "User Preferences",
}


def build_context_package(
    project_path: Optional[str] = None,
    memory_type: Optional[str] = None,
    source_tool: Optional[str] = None,
    tag: Optional[str] = None,
    query_text: Optional[str] = None,
    pinned: Optional[bool] = None,
    include_stale: bool = False,
    limit: int = 20,
    max_chars: int = 4000,
) -> dict:
    limit = max(1, min(int(limit), 50))
    max_chars = max(500, min(int(max_chars), 20000))
    rows = list_items(
        project_path=project_path,
        memory_type=memory_type,
        source_tool=source_tool,
        tag=tag,
        query_text=query_text,
        pinned=pinned,
        limit=min(200, max(limit * 4, 50)),
    )
    stale_excluded_count = sum(1 for row in rows if row.get("stale") and not include_stale)
    selected = [
        _package_item(row)
        for row in rows
        if include_stale or not row.get("stale")
    ][:limit]
    sections = _sections(selected)
    package_text, truncated = _package_text(
        project_path=project_path,
        query_text=query_text,
        sections=sections,
        stale_excluded_count=stale_excluded_count,
        max_chars=max_chars,
    )
    return {
        "project_path": project_path,
        "query": query_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "include_stale": include_stale,
        "item_count": len(selected),
        "source_item_count": len(rows),
        "stale_excluded_count": stale_excluded_count,
        "max_chars": max_chars,
        "truncated": truncated,
        "dlp_findings_count": findings_count(package_text),
        "sections": sections,
        "package_text": package_text,
    }


def _package_item(row: dict) -> dict:
    content = row.get("redacted_content") or redact_text(row.get("content") or "")
    return {
        "id": row["id"],
        "memory_type": row.get("memory_type") or "memory",
        "source_tool": row.get("source_tool"),
        "content": redact_text(content).replace("\n", " ").strip(),
        "importance_score": float(row.get("importance_score") or 0.5),
        "tags": row.get("tags") or [],
        "pinned": bool(row.get("pinned")),
        "stale": bool(row.get("stale")),
        "stale_reason": row.get("stale_reason"),
        "updated_at": row.get("updated_at"),
        "last_attached_at": row.get("last_attached_at"),
    }


def _sections(items: list[dict]) -> list[dict]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for item in items:
        grouped.setdefault(item["memory_type"], []).append(item)
    return [
        {
            "memory_type": memory_type,
            "title": _TYPE_LABELS.get(memory_type, memory_type.replace("_", " ").title()),
            "items": rows,
        }
        for memory_type, rows in grouped.items()
    ]


def _package_text(
    project_path: Optional[str],
    query_text: Optional[str],
    sections: list[dict],
    stale_excluded_count: int,
    max_chars: int,
) -> tuple[str, bool]:
    lines = ["Spectrona Fresh Context"]
    if project_path:
        lines.append(f"Project: {project_path}")
    if query_text:
        lines.append(f"Query: {query_text}")
    lines.append(f"Items: {sum(len(section['items']) for section in sections)}")
    if stale_excluded_count:
        lines.append(f"Stale excluded: {stale_excluded_count}")

    for section in sections:
        lines.append("")
        lines.append(f"## {section['title']}")
        for item in section["items"]:
            suffix = _item_suffix(item)
            content = _clip(item["content"], 320)
            lines.append(f"- {content}{suffix}")

    text = redact_text("\n".join(lines).strip())
    if len(text) <= max_chars:
        return text, False
    return text[: max_chars - 18].rstrip() + "\n[truncated]", True


def _item_suffix(item: dict) -> str:
    parts = []
    if item.get("source_tool"):
        parts.append(f"source:{item['source_tool']}")
    if item.get("pinned"):
        parts.append("pinned")
    tags = [f"#{tag}" for tag in (item.get("tags") or [])[:3]]
    parts.extend(tags)
    return f" ({', '.join(parts)})" if parts else ""


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
