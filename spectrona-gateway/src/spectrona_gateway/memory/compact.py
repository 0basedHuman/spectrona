from collections import OrderedDict
from datetime import datetime, timezone
import re
from typing import Optional

from ..dlp import findings_count, redact_text
from .retrieve import list_items
from .store import insert_item, update_item


def compact(
    project_path: Optional[str] = None,
    dry_run: bool = True,
    limit: int = 200,
    max_summary_chars: int = 2000,
    low_importance_threshold: float = 0.35,
) -> dict:
    limit = max(1, min(int(limit), 500))
    max_summary_chars = max(500, min(int(max_summary_chars), 10000))
    low_importance_threshold = max(0.0, min(float(low_importance_threshold), 1.0))

    rows = list_items(project_path=project_path, limit=limit)
    duplicate_groups = _duplicate_groups(rows)
    duplicate_actions = _duplicate_actions(duplicate_groups)
    stale_actions = _stale_actions(
        rows=rows,
        low_importance_threshold=low_importance_threshold,
        excluded_item_ids={action["item_id"] for action in duplicate_actions if action.get("item_id")},
    )
    summary_text, truncated = _summary_text(
        rows=rows,
        duplicate_groups=duplicate_groups,
        stale_actions=stale_actions,
        max_summary_chars=max_summary_chars,
        project_path=project_path,
    )

    actions = [*duplicate_actions, *stale_actions]
    summary_action = _summary_action(rows=rows, project_path=project_path, summary_text=summary_text)
    if summary_action:
        actions.append(summary_action)

    summary_item_id = None
    applied_action_count = 0
    if not dry_run:
        applied_action_count, summary_item_id = _apply_actions(actions, rows, summary_text)
        for action in actions:
            action["applied"] = bool(action.get("applied"))

    return {
        "status": "planned" if dry_run else "applied",
        "dry_run": dry_run,
        "project_path": project_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanned_item_count": len(rows),
        "duplicate_group_count": len(duplicate_groups),
        "stale_candidate_count": len(stale_actions),
        "summary_item_id": summary_item_id,
        "summary_truncated": truncated,
        "summary_text": summary_text,
        "dlp_findings_count": findings_count(summary_text),
        "applied_action_count": applied_action_count,
        "actions": actions,
    }


def _duplicate_groups(rows: list[dict]) -> list[list[dict]]:
    groups: OrderedDict[tuple[str, str, str], list[dict]] = OrderedDict()
    for row in rows:
        key = (
            row.get("project_path") or "",
            row.get("memory_type") or "",
            _normalize(_visible_content(row)),
        )
        if len(key[2]) < 24:
            continue
        groups.setdefault(key, []).append(row)
    return [group for group in groups.values() if len(group) > 1]


def _duplicate_actions(groups: list[list[dict]]) -> list[dict]:
    actions = []
    for group in groups:
        canonical = _canonical_item(group)
        actions.append(
            {
                "action": "pin_canonical",
                "item_id": canonical["id"],
                "duplicate_of": None,
                "reason": "duplicate_canonical",
                "memory_type": canonical.get("memory_type"),
                "project_path": canonical.get("project_path"),
                "tags_added": ["canonical", "compacted"],
                "applied": False,
            }
        )
        for row in group:
            if row["id"] == canonical["id"]:
                continue
            actions.append(
                {
                    "action": "tag_duplicate",
                    "item_id": row["id"],
                    "duplicate_of": canonical["id"],
                    "reason": "duplicate_redacted_content",
                    "memory_type": row.get("memory_type"),
                    "project_path": row.get("project_path"),
                    "tags_added": ["duplicate", "stale", "compacted"],
                    "applied": False,
                }
            )
    return actions


def _stale_actions(
    rows: list[dict],
    low_importance_threshold: float,
    excluded_item_ids: set[str],
) -> list[dict]:
    actions = []
    for row in rows:
        item_id = row["id"]
        if item_id in excluded_item_ids:
            continue
        if row.get("pinned"):
            continue
        if not row.get("stale"):
            continue
        importance = float(row.get("importance_score") or 0.0)
        if importance > low_importance_threshold:
            continue
        actions.append(
            {
                "action": "tag_stale_candidate",
                "item_id": item_id,
                "duplicate_of": None,
                "reason": "stale_low_importance",
                "memory_type": row.get("memory_type"),
                "project_path": row.get("project_path"),
                "tags_added": ["compaction_candidate", "stale", "low_importance"],
                "applied": False,
            }
        )
    return actions


def _summary_action(rows: list[dict], project_path: Optional[str], summary_text: str) -> Optional[dict]:
    summary_project = project_path or _single_project_path(rows)
    if not summary_project or not summary_text.strip():
        return None
    return {
        "action": "create_compaction_summary",
        "item_id": None,
        "duplicate_of": None,
        "reason": "redacted_project_memory_summary",
        "memory_type": "session_summary",
        "project_path": summary_project,
        "tags_added": ["compacted", "summary"],
        "applied": False,
    }


def _apply_actions(actions: list[dict], rows: list[dict], summary_text: str) -> tuple[int, Optional[str]]:
    by_id = {row["id"]: row for row in rows}
    applied = 0
    summary_item_id = None
    for action in actions:
        name = action.get("action")
        if name == "pin_canonical":
            row = by_id.get(action["item_id"])
            if row and update_item(
                row["id"],
                {
                    "pinned": True,
                    "importance_score": max(float(row.get("importance_score") or 0.0), 0.75),
                },
                tags=_merge_tags(row.get("tags") or [], action["tags_added"]),
            ):
                action["applied"] = True
                applied += 1
        elif name in {"tag_duplicate", "tag_stale_candidate"}:
            row = by_id.get(action["item_id"])
            if row and update_item(row["id"], {}, tags=_merge_tags(row.get("tags") or [], action["tags_added"])):
                action["applied"] = True
                applied += 1
        elif name == "create_compaction_summary":
            summary_item_id = insert_item(
                project_path=action["project_path"],
                memory_type="session_summary",
                content=summary_text,
                source_tool="spectrona_compactor",
                importance_score=0.7,
                tags=action["tags_added"],
                pinned=True,
            )
            action["item_id"] = summary_item_id
            action["applied"] = True
            applied += 1
    return applied, summary_item_id


def _summary_text(
    rows: list[dict],
    duplicate_groups: list[list[dict]],
    stale_actions: list[dict],
    max_summary_chars: int,
    project_path: Optional[str],
) -> tuple[str, bool]:
    lines = ["Spectrona Memory Compaction"]
    if project_path:
        lines.append(f"Project: {project_path}")
    lines.append(f"Items scanned: {len(rows)}")
    lines.append(f"Duplicate groups: {len(duplicate_groups)}")
    lines.append(f"Stale low-importance candidates: {len(stale_actions)}")

    keepers = _keepers(rows, duplicate_groups)
    if keepers:
        lines.append("")
        lines.append("## Canonical Context")
        for row in keepers[:8]:
            lines.append(f"- {_clip(_visible_content(row), 220)}{_suffix(row)}")

    if duplicate_groups:
        lines.append("")
        lines.append("## Duplicate Groups")
        for group in duplicate_groups[:6]:
            canonical = _canonical_item(group)
            lines.append(f"- keep {canonical['id']} and mark {len(group) - 1} duplicate(s)")

    if stale_actions:
        lines.append("")
        lines.append("## Stale Candidates")
        for action in stale_actions[:8]:
            lines.append(f"- mark {action['item_id']} as compaction candidate")

    text = redact_text("\n".join(lines).strip())
    if len(text) <= max_summary_chars:
        return text, False
    return text[: max_summary_chars - 18].rstrip() + "\n[truncated]", True


def _keepers(rows: list[dict], duplicate_groups: list[list[dict]]) -> list[dict]:
    duplicate_ids = {
        row["id"]
        for group in duplicate_groups
        for row in group
        if row["id"] != _canonical_item(group)["id"]
    }
    candidates = [
        row for row in rows
        if row["id"] not in duplicate_ids and (row.get("pinned") or not row.get("stale"))
    ]
    return sorted(
        candidates,
        key=lambda row: (
            bool(row.get("pinned")),
            float(row.get("importance_score") or 0.0),
            str(row.get("updated_at") or ""),
        ),
        reverse=True,
    )


def _canonical_item(rows: list[dict]) -> dict:
    return sorted(
        rows,
        key=lambda row: (
            bool(row.get("pinned")),
            float(row.get("importance_score") or 0.0),
            str(row.get("updated_at") or ""),
        ),
        reverse=True,
    )[0]


def _visible_content(row: dict) -> str:
    return redact_text(row.get("redacted_content") or row.get("content") or "").replace("\n", " ").strip()


def _normalize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", " ", value.lower())
    return re.sub(r"\s+", " ", text).strip()


def _suffix(row: dict) -> str:
    parts = []
    if row.get("memory_type"):
        parts.append(str(row["memory_type"]))
    if row.get("source_tool"):
        parts.append(f"source:{row['source_tool']}")
    if row.get("pinned"):
        parts.append("pinned")
    tags = [f"#{tag}" for tag in (row.get("tags") or [])[:3]]
    parts.extend(tags)
    return f" ({', '.join(parts)})" if parts else ""


def _merge_tags(existing: list[str], additions: list[str]) -> list[str]:
    clean = []
    seen = set()
    for tag in [*existing, *additions]:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        clean.append(value)
        seen.add(value)
    return clean


def _single_project_path(rows: list[dict]) -> Optional[str]:
    paths = {row.get("project_path") for row in rows if row.get("project_path")}
    return next(iter(paths)) if len(paths) == 1 else None


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
