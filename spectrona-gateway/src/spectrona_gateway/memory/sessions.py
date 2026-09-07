from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from .. import config
from ..dlp import findings_count, redact_text
from ..events.store import list_events
from .store import insert_item


def extract_session(
    project_path: Optional[str] = None,
    client: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 200,
    max_summary_chars: int = 2000,
    dry_run: bool = True,
) -> dict:
    limit = max(1, min(int(limit), 500))
    max_summary_chars = max(500, min(int(max_summary_chars), 10000))
    events = list_events(
        limit=limit,
        client=client,
        project_path=project_path,
        since=since,
        until=until,
    )
    events = sorted(events, key=lambda event: event.get("timestamp") or "")
    summary_text, truncated = _summary_text(
        events=events,
        project_path=project_path,
        client=client,
        since=since,
        until=until,
        max_summary_chars=max_summary_chars,
    )
    stats = _stats(events)
    summary_item_id = None

    if not dry_run and events:
        summary_project = project_path or _single_value(events, "project_path") or str(config.REPO_ROOT)
        summary_item_id = insert_item(
            project_path=summary_project,
            source_tool="spectrona_session_extractor",
            memory_type="session_summary",
            content=summary_text,
            importance_score=0.75,
            tags=_summary_tags(stats),
            pinned=True,
        )

    return {
        "status": "planned" if dry_run else "applied",
        "dry_run": dry_run,
        "source": "runtime_events",
        "project_path": project_path,
        "client": client,
        "since": since,
        "until": until,
        "limit": limit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_item_id": summary_item_id,
        "summary_truncated": truncated,
        "summary_text": summary_text,
        "dlp_findings_count": findings_count(summary_text),
        **stats,
        "events": [_event_summary(event) for event in events[-20:]],
    }


def _stats(events: list[dict]) -> dict:
    providers = Counter(_value(event.get("provider_type")) for event in events)
    models = Counter(_value(event.get("model")) for event in events)
    clients = Counter(_value(event.get("client")) for event in events)
    routes = Counter(_value(event.get("route")) for event in events)
    actions = Counter(_value(event.get("action")) for event in events)
    projects = Counter(_value(event.get("project_path")) for event in events)
    statuses = Counter(str(int(event.get("status_code") or 0)) for event in events)
    first_seen = events[0].get("timestamp") if events else None
    last_seen = events[-1].get("timestamp") if events else None
    return {
        "event_count": len(events),
        "window_start": first_seen,
        "window_end": last_seen,
        "success_count": sum(1 for event in events if int(event.get("status_code") or 0) < 400),
        "blocked_count": sum(1 for event in events if int(event.get("status_code") or 0) >= 400 or event.get("action") == "blocked"),
        "approval_required_count": sum(1 for event in events if "approval" in str(event.get("action") or "")),
        "request_tokens": sum(int(event.get("request_tokens") or 0) for event in events),
        "response_tokens": sum(int(event.get("response_tokens") or 0) for event in events),
        "total_tokens": sum(int(event.get("total_tokens") or 0) for event in events),
        "runtime_dlp_findings_count": sum(int(event.get("dlp_findings_count") or 0) for event in events),
        "by_provider": dict(sorted(providers.items())),
        "by_model": dict(sorted(models.items())),
        "by_client": dict(sorted(clients.items())),
        "by_route": dict(sorted(routes.items())),
        "by_action": dict(sorted(actions.items())),
        "by_project_path": dict(sorted(projects.items())),
        "by_status_code": dict(sorted(statuses.items())),
    }


def _summary_text(
    events: list[dict],
    project_path: Optional[str],
    client: Optional[str],
    since: Optional[str],
    until: Optional[str],
    max_summary_chars: int,
) -> tuple[str, bool]:
    stats = _stats(events)
    lines = ["Spectrona Session Extraction"]
    lines.append("Source: runtime_events metadata")
    if project_path:
        lines.append(f"Project: {project_path}")
    elif stats["by_project_path"]:
        lines.append(f"Projects: {_top_counts(stats['by_project_path'])}")
    if client:
        lines.append(f"Client: {client}")
    elif stats["by_client"]:
        lines.append(f"Clients: {_top_counts(stats['by_client'])}")
    if since or until:
        lines.append(f"Requested window: {since or 'beginning'} to {until or 'now'}")
    if stats["window_start"] or stats["window_end"]:
        lines.append(f"Observed window: {stats['window_start'] or 'unknown'} to {stats['window_end'] or 'unknown'}")
    lines.append(f"Model calls: {stats['event_count']}")
    lines.append(f"Successful: {stats['success_count']}")
    lines.append(f"Blocked/errors: {stats['blocked_count']}")
    lines.append(f"Approval-required: {stats['approval_required_count']}")
    lines.append(f"DLP findings: {stats['runtime_dlp_findings_count']}")
    lines.append(f"Tokens: {stats['total_tokens']} total ({stats['request_tokens']} request, {stats['response_tokens']} response)")
    if stats["by_provider"]:
        lines.append(f"Providers: {_top_counts(stats['by_provider'])}")
    if stats["by_model"]:
        lines.append(f"Models: {_top_counts(stats['by_model'])}")
    if stats["by_route"]:
        lines.append(f"Routes: {_top_counts(stats['by_route'])}")
    if stats["by_action"]:
        lines.append(f"Actions: {_top_counts(stats['by_action'])}")
    if events:
        lines.append("")
        lines.append("## Recent Runtime Events")
        for event in events[-8:]:
            lines.append(
                "- "
                f"{event.get('timestamp') or 'unknown'} "
                f"{event.get('client') or 'unknown'} "
                f"{event.get('provider_type') or 'unknown'} "
                f"{event.get('model') or 'unknown'} "
                f"{event.get('action') or 'unknown'} "
                f"status:{int(event.get('status_code') or 0)} "
                f"dlp:{int(event.get('dlp_findings_count') or 0)}"
            )
    else:
        lines.append("No runtime events matched the extraction filters.")

    text = redact_text("\n".join(lines).strip())
    if len(text) <= max_summary_chars:
        return text, False
    return text[: max_summary_chars - 18].rstrip() + "\n[truncated]", True


def _event_summary(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "timestamp": event.get("timestamp"),
        "route": event.get("route"),
        "provider_type": event.get("provider_type"),
        "model": event.get("model"),
        "client": event.get("client"),
        "project_path": event.get("project_path"),
        "action": event.get("action"),
        "policy_action": event.get("policy_action"),
        "policy_rule_id": event.get("policy_rule_id"),
        "dlp_findings_count": int(event.get("dlp_findings_count") or 0),
        "request_tokens": int(event.get("request_tokens") or 0),
        "response_tokens": int(event.get("response_tokens") or 0),
        "total_tokens": int(event.get("total_tokens") or 0),
        "status_code": int(event.get("status_code") or 0),
    }


def _summary_tags(stats: dict) -> list[str]:
    tags = ["session_extraction", "runtime", "summary"]
    tags.extend([f"client:{key}" for key in list(stats.get("by_client") or {})[:2] if key != "unknown"])
    tags.extend([f"provider:{key}" for key in list(stats.get("by_provider") or {})[:2] if key != "unknown"])
    if stats.get("runtime_dlp_findings_count"):
        tags.append("dlp")
    if stats.get("blocked_count"):
        tags.append("blocked")
    return tags


def _top_counts(counts: dict, limit: int = 5) -> str:
    items = sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))[:limit]
    return ", ".join(f"{key}:{count}" for key, count in items)


def _single_value(events: list[dict], key: str) -> Optional[str]:
    values = {event.get(key) for event in events if event.get(key)}
    return next(iter(values)) if len(values) == 1 else None


def _value(value) -> str:
    return str(value or "unknown")
