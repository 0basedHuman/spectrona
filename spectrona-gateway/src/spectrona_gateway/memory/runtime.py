import json
import re
from dataclasses import dataclass
from typing import Mapping, Optional

from .. import audit, config
from ..dlp import findings_count, redact_text
from .retrieve import list_items
from .staleness import is_stale
from .store import insert_item, record_item_event


_MEMORY_MARKER = re.compile(r"(?:^|\n)\s*(?:remember|spectrona memory)\s*:\s*(.+)", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")


@dataclass(frozen=True)
class RuntimeMemoryResult:
    body_bytes: bytes
    body_str: str
    attached_item_ids: list[str]
    captured_item_ids: list[str]


def prepare_request_memory(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    body_bytes: bytes,
    body_str: str,
    headers: Mapping[str, str],
) -> RuntimeMemoryResult:
    project_path = _project_path(headers)
    body = _decode_json(body_bytes)
    request_text = _request_text(provider_type, body)
    should_inject = _memory_injection_enabled(headers) and isinstance(body, dict)
    items = _relevant_items(project_path, request_text) if should_inject else []
    captured_ids = _capture_candidates(
        project_path=project_path,
        source_tool=client,
        provider_type=provider_type,
        content=request_text,
        memory_type="user_preference",
        phase="request",
    )

    if not should_inject:
        return RuntimeMemoryResult(body_bytes, body_str, [], captured_ids)

    if not items:
        return RuntimeMemoryResult(body_bytes, body_str, [], captured_ids)

    context = _context_text(items)
    updated = _inject_context(provider_type, body, context)
    if updated is body:
        return RuntimeMemoryResult(body_bytes, body_str, [], captured_ids)

    updated_bytes = json.dumps(updated, separators=(",", ":")).encode("utf-8")
    updated_str = updated_bytes.decode("utf-8", errors="replace")
    attached_ids = [item["id"] for item in items]
    details = {
        "route": route,
        "provider_type": provider_type,
        "model": model,
        "client": client,
    }
    for item_id in attached_ids:
        record_item_event(item_id, "attached", details)
    audit.log_event(
        route=route,
        provider_type="memory",
        model=model,
        estimated_input_chars=len(context),
        dlp_findings_count=findings_count(context),
        action="memory_attach",
        client=client,
    )
    return RuntimeMemoryResult(updated_bytes, updated_str, attached_ids, captured_ids)


def capture_response_memory(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    headers: Mapping[str, str],
    response_content: bytes,
) -> list[str]:
    project_path = _project_path(headers)
    text = _response_text(provider_type, _decode_json(response_content))
    captured = _capture_candidates(
        project_path=project_path,
        source_tool=client,
        provider_type=provider_type,
        content=text,
        memory_type="session_summary",
        phase="response",
    )
    return captured


def _capture_candidates(
    project_path: str,
    source_tool: str,
    provider_type: str,
    content: str,
    memory_type: str,
    phase: str,
) -> list[str]:
    if not config.MEMORY_CAPTURE:
        return []

    ids = []
    for candidate in _marked_memory(content):
        safe_content = redact_text(candidate)
        item_id = insert_item(
            project_path=project_path,
            source_tool=source_tool,
            memory_type=memory_type,
            content=safe_content,
            importance_score=0.7,
            tags=["runtime", phase, provider_type],
        )
        ids.append(item_id)
        audit.log_event(
            route="/memory/runtime",
            provider_type="memory",
            model="",
            estimated_input_chars=len(safe_content),
            dlp_findings_count=findings_count(candidate),
            action="memory_capture_request" if phase == "request" else "memory_capture_response",
            client=source_tool,
        )
    return ids


def _marked_memory(content: str) -> list[str]:
    candidates = []
    for match in _MEMORY_MARKER.finditer(content or ""):
        value = match.group(1).strip()
        if value:
            candidates.append(value[:800])
    return candidates


def _relevant_items(project_path: str, request_text: str) -> list[dict]:
    limit = max(1, min(config.MEMORY_MAX_ATTACHMENTS, 10))
    rows = list_items(project_path=project_path, limit=50)
    tokens = _tokens(request_text)
    scored = []
    for row in rows:
        if is_stale(row):
            continue
        content = row.get("redacted_content") or row.get("content") or ""
        row_tokens = _tokens(" ".join([content, row.get("memory_type") or "", " ".join(row.get("tags") or [])]))
        score = len(tokens & row_tokens)
        if row.get("pinned"):
            score += 100
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: (item[0], item[1].get("updated_at") or ""), reverse=True)
    return [row for _, row in scored[:limit]]


def _context_text(items: list[dict]) -> str:
    lines = ["Spectrona memory context:"]
    for item in items:
        content = item.get("redacted_content") or item.get("content") or ""
        content = redact_text(content).replace("\n", " ").strip()
        if len(content) > 240:
            content = content[:237].rstrip() + "..."
        lines.append(f"- {content}")
    return "\n".join(lines)


def _inject_context(provider_type: str, body: dict, context: str) -> dict:
    if provider_type in {"openai", "local"}:
        messages = body.get("messages")
        if not isinstance(messages, list):
            return body
        updated = dict(body)
        updated["messages"] = [{"role": "system", "content": context}, *messages]
        return updated

    if provider_type == "anthropic":
        updated = dict(body)
        existing = updated.get("system")
        if isinstance(existing, str) and existing.strip():
            updated["system"] = f"{context}\n\n{existing}"
        elif isinstance(existing, list):
            updated["system"] = [{"type": "text", "text": context}, *existing]
        else:
            updated["system"] = context
        return updated

    return body


def _request_text(provider_type: str, body: Optional[dict]) -> str:
    if not isinstance(body, dict):
        return ""
    if provider_type in {"openai", "local"}:
        return "\n".join(_message_text(message) for message in body.get("messages") or [])
    if provider_type == "anthropic":
        return "\n".join(_message_text(message) for message in body.get("messages") or [])
    return ""


def _response_text(provider_type: str, body: Optional[dict]) -> str:
    if not isinstance(body, dict):
        return ""
    if provider_type in {"openai", "local"}:
        choices = body.get("choices") or []
        return "\n".join(_content_text((choice.get("message") or {}).get("content")) for choice in choices if isinstance(choice, dict))
    if provider_type == "anthropic":
        return _content_text(body.get("content"))
    return ""


def _message_text(message) -> str:
    if not isinstance(message, dict):
        return ""
    return _content_text(message.get("content"))


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text") or ""))
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part)
    return ""


def _decode_json(content: bytes) -> Optional[dict]:
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _project_path(headers: Mapping[str, str]) -> str:
    return headers.get("x-spectrona-project-path") or headers.get("x-spectrona-repo-root") or str(config.REPO_ROOT)


def _memory_injection_enabled(headers: Mapping[str, str]) -> bool:
    value = headers.get("x-spectrona-memory-injection")
    if value is not None:
        return value.lower() in {"1", "true", "yes", "on"}
    return config.MEMORY_INJECTION


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value or "")}
