"""Metadata-only session replay built from runtime events and memory summaries."""

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from .. import config
from ..dlp import findings_count, redact_text
from ..events.store import list_events
from .retrieve import list_items
from .store import insert_item


def replay_session(
    project_path: Optional[str] = None,
    client: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 200,
    max_replay_chars: int = 4000,
    dry_run: bool = True,
) -> dict:
    limit = max(1, min(int(limit), 500))
    max_replay_chars = max(800, min(int(max_replay_chars), 20000))
    events = sorted(
        list_events(
            limit=limit,
            client=client,
            project_path=project_path,
            since=since,
            until=until,
        ),
        key=lambda event: event.get("timestamp") or "",
    )
    summaries = _session_summaries(project_path=project_path, client=client, since=since, until=until, limit=limit)
    steps = sorted(
        [_event_step(event) for event in events] + [_summary_step(item) for item in summaries],
        key=lambda step: step.get("timestamp") or "",
    )
    if len(steps) > limit:
        steps = steps[-limit:]

    stats = _stats(events, summaries, steps)
    replay_text, truncated = _replay_text(
        stats=stats,
        steps=steps,
        project_path=project_path,
        client=client,
        since=since,
        until=until,
        max_replay_chars=max_replay_chars,
    )
    replay_item_id = None

    if not dry_run and steps:
        replay_project = project_path or _single_value(events, "project_path") or _single_value(summaries, "project_path") or str(config.REPO_ROOT)
        replay_item_id = insert_item(
            project_path=replay_project,
            source_tool="spectrona_session_replay",
            memory_type="session_summary",
            content=replay_text,
            importance_score=0.7,
            tags=_replay_tags(stats),
            pinned=True,
        )

    return {
        "status": "planned" if dry_run else "applied",
        "dry_run": dry_run,
        "source": "runtime_events+memory_summaries",
        "project_path": project_path,
        "client": client,
        "since": since,
        "until": until,
        "limit": limit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "replay_item_id": replay_item_id,
        "replay_truncated": truncated,
        "replay_text": replay_text,
        "dlp_findings_count": findings_count(replay_text),
        **stats,
        "steps": steps[-50:],
    }


def _session_summaries(
    project_path: Optional[str],
    client: Optional[str],
    since: Optional[str],
    until: Optional[str],
    limit: int,
) -> list[dict]:
    items = list_items(project_path=project_path, memory_type="session_summary", limit=min(limit, 200))
    filtered = []
    for item in items:
        timestamp = item.get("updated_at") or item.get("created_at") or ""
        if since and timestamp < since:
            continue
        if until and timestamp > until:
            continue
        if client and not _summary_matches_client(item, client):
            continue
        filtered.append(item)
    return sorted(filtered, key=lambda item: item.get("updated_at") or item.get("created_at") or "")


def _summary_matches_client(item: dict, client: str) -> bool:
    wanted = f"client:{client}"
    tags = {str(tag) for tag in item.get("tags") or []}
    if wanted in tags:
        return True
    content = _safe_content(item).lower()
    return f"client: {client.lower()}" in content or f"clients: {client.lower()}" in content


def _event_step(event: dict) -> dict:
    provider = _value(event.get("provider_type"))
    model = _value(event.get("model"))
    action = _value(event.get("action"))
    status_code = int(event.get("status_code") or 0)
    dlp_count = int(event.get("dlp_findings_count") or 0)
    total_tokens = int(event.get("total_tokens") or 0)
    summary = (
        f"{_value(event.get('client'))} called {_value(event.get('route'))} "
        f"through {provider}/{model}; action={action}; status={status_code}; "
        f"tokens={total_tokens}; dlp={dlp_count}."
    )
    return _redacted_step({
        "step_type": "runtime_event",
        "timestamp": event.get("timestamp"),
        "title": f"{provider}/{model} {action}",
        "summary": summary,
        "metadata": {
            "event_id": event.get("id"),
            "route": event.get("route"),
            "provider_type": event.get("provider_type"),
            "model": event.get("model"),
            "client": event.get("client"),
            "project_path": event.get("project_path"),
            "action": event.get("action"),
            "policy_action": event.get("policy_action"),
            "policy_rule_id": event.get("policy_rule_id"),
            "dlp_findings_count": dlp_count,
            "request_tokens": int(event.get("request_tokens") or 0),
            "response_tokens": int(event.get("response_tokens") or 0),
            "total_tokens": total_tokens,
            "status_code": status_code,
        },
    })


def _summary_step(item: dict) -> dict:
    content = _short(_safe_content(item).replace("\n", " "), 420)
    source = _value(item.get("source_tool"))
    return _redacted_step({
        "step_type": "memory_summary",
        "timestamp": item.get("updated_at") or item.get("created_at"),
        "title": f"Memory Summary · {source}",
        "summary": content,
        "metadata": {
            "item_id": item.get("id"),
            "memory_type": item.get("memory_type"),
            "source_tool": item.get("source_tool"),
            "project_path": item.get("project_path"),
            "importance_score": float(item.get("importance_score") or 0),
            "pinned": bool(item.get("pinned")),
            "tags": list(item.get("tags") or [])[:10],
        },
    })


def _stats(events: list[dict], summaries: list[dict], steps: list[dict]) -> dict:
    providers = Counter(_value(event.get("provider_type")) for event in events)
    models = Counter(_value(event.get("model")) for event in events)
    clients = Counter(_value(event.get("client")) for event in events)
    routes = Counter(_value(event.get("route")) for event in events)
    actions = Counter(_value(event.get("action")) for event in events)
    projects = Counter(_value(event.get("project_path")) for event in events)
    summary_sources = Counter(_value(item.get("source_tool")) for item in summaries)
    timestamps = [step.get("timestamp") for step in steps if step.get("timestamp")]
    return {
        "step_count": len(steps),
        "event_count": len(events),
        "memory_summary_count": len(summaries),
        "window_start": min(timestamps) if timestamps else None,
        "window_end": max(timestamps) if timestamps else None,
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
        "by_summary_source": dict(sorted(summary_sources.items())),
    }


def _replay_text(
    stats: dict,
    steps: list[dict],
    project_path: Optional[str],
    client: Optional[str],
    since: Optional[str],
    until: Optional[str],
    max_replay_chars: int,
) -> tuple[str, bool]:
    lines = ["Spectrona Session Replay"]
    lines.append("Source: runtime_events metadata + redacted memory summaries")
    lines.append("Content scope: metadata-only; raw prompts and provider responses are not replayed.")
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
    lines.append(
        f"Steps: {stats['step_count']} "
        f"({stats['event_count']} runtime events, {stats['memory_summary_count']} memory summaries)"
    )
    lines.append(f"Successful: {stats['success_count']}")
    lines.append(f"Blocked/errors: {stats['blocked_count']}")
    lines.append(f"Approval-required: {stats['approval_required_count']}")
    lines.append(f"DLP findings: {stats['runtime_dlp_findings_count']}")
    lines.append(f"Tokens: {stats['total_tokens']} total ({stats['request_tokens']} request, {stats['response_tokens']} response)")
    if stats["by_provider"]:
        lines.append(f"Providers: {_top_counts(stats['by_provider'])}")
    if stats["by_summary_source"]:
        lines.append(f"Memory summaries: {_top_counts(stats['by_summary_source'])}")
    lines.append("")
    lines.append("## Replay Steps")
    if not steps:
        lines.append("No runtime events or memory summaries matched the replay filters.")
    for index, step in enumerate(steps, start=1):
        marker = "runtime" if step["step_type"] == "runtime_event" else "memory"
        lines.append(
            f"{index}. [{marker}] {step.get('timestamp') or 'unknown'} "
            f"{step.get('title') or 'step'}"
        )
        lines.append(f"   {step.get('summary') or ''}")

    text = redact_text("\n".join(lines).strip())
    if len(text) <= max_replay_chars:
        return text, False
    return text[: max_replay_chars - 18].rstrip() + "\n[truncated]", True


def _replay_tags(stats: dict) -> list[str]:
    tags = ["session_replay", "runtime", "summary"]
    tags.extend([f"client:{key}" for key in list(stats.get("by_client") or {})[:2] if key != "unknown"])
    tags.extend([f"provider:{key}" for key in list(stats.get("by_provider") or {})[:2] if key != "unknown"])
    if stats.get("runtime_dlp_findings_count"):
        tags.append("dlp")
    if stats.get("blocked_count"):
        tags.append("blocked")
    return tags


def _safe_content(item: dict) -> str:
    content = item.get("redacted_content")
    if content is None:
        content = item.get("content") or ""
    return redact_text(str(content))


def _redacted_step(step: dict) -> dict:
    return _redact_nested(step)


def _redact_nested(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_nested(item) for key, item in value.items()}
    return value


def _top_counts(counts: dict, limit: int = 5) -> str:
    items = sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))[:limit]
    return ", ".join(f"{key}:{count}" for key, count in items)


def _single_value(items: list[dict], key: str) -> Optional[str]:
    values = {item.get(key) for item in items if item.get(key)}
    return next(iter(values)) if len(values) == 1 else None


def _short(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 14].rstrip() + " [truncated]"


def _value(value) -> str:
    return str(value or "unknown")
