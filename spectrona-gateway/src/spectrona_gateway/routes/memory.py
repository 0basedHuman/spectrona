import json
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from .. import audit
from ..dlp import findings_count, redact_text
from ..memory.compact import compact
from ..memory.context import build_context_package
from ..memory.protection import redaction_was_applied, storage_metadata
from ..memory.replay import replay_session
from ..memory.sessions import extract_session
from ..memory.store import delete_item, insert_item, update_item
from ..memory.retrieve import get_item, list_events, list_items
from ..memory.timeline import memory_timeline

router = APIRouter()


class MemoryItemCreate(BaseModel):
    project_path: str
    source_tool: Optional[str] = None
    memory_type: str = "project_decision"
    content: str
    importance_score: float = 0.5
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    raw_storage_mode: Optional[str] = None


class MemoryItemUpdate(BaseModel):
    project_path: Optional[str] = None
    source_tool: Optional[str] = None
    memory_type: Optional[str] = None
    content: Optional[str] = None
    importance_score: Optional[float] = None
    tags: Optional[list[str]] = None
    pinned: Optional[bool] = None
    raw_storage_mode: Optional[str] = None


class MemoryItemResponse(BaseModel):
    id: str
    project_path: str
    source_tool: Optional[str] = None
    memory_type: str
    content: str       # always redacted_content — never raw
    created_at: str
    updated_at: str
    importance_score: float
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    redacted: bool = False
    stale: bool = False
    stale_reason: Optional[str] = None
    age_days: Optional[float] = None
    stale_after_days: int = 30
    last_attached_at: Optional[str] = None
    raw_storage_mode: str = "redacted"
    raw_storage_reason: str = "redacted_by_default"
    raw_content_stored: bool = False
    encrypted_content_stored: bool = False


class MemoryEventResponse(BaseModel):
    id: str
    item_id: Optional[str] = None
    event_type: str
    details: dict = Field(default_factory=dict)
    timestamp: str


class MemoryContextItemResponse(BaseModel):
    id: str
    memory_type: str
    source_tool: Optional[str] = None
    content: str
    importance_score: float
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    stale: bool = False
    stale_reason: Optional[str] = None
    updated_at: str
    last_attached_at: Optional[str] = None


class MemoryContextSectionResponse(BaseModel):
    memory_type: str
    title: str
    items: list[MemoryContextItemResponse] = Field(default_factory=list)


class MemoryContextPackageResponse(BaseModel):
    project_path: Optional[str] = None
    query: Optional[str] = None
    generated_at: str
    include_stale: bool = False
    item_count: int
    source_item_count: int
    stale_excluded_count: int
    max_chars: int
    truncated: bool = False
    dlp_findings_count: int
    sections: list[MemoryContextSectionResponse] = Field(default_factory=list)
    package_text: str


class MemoryCompactActionResponse(BaseModel):
    action: str
    item_id: Optional[str] = None
    duplicate_of: Optional[str] = None
    reason: str
    memory_type: Optional[str] = None
    project_path: Optional[str] = None
    tags_added: list[str] = Field(default_factory=list)
    applied: bool = False


class MemoryCompactResponse(BaseModel):
    status: str
    dry_run: bool = True
    project_path: Optional[str] = None
    generated_at: str
    scanned_item_count: int
    duplicate_group_count: int
    stale_candidate_count: int
    summary_item_id: Optional[str] = None
    summary_truncated: bool = False
    summary_text: str
    dlp_findings_count: int
    applied_action_count: int = 0
    actions: list[MemoryCompactActionResponse] = Field(default_factory=list)


class MemoryCompactRequest(BaseModel):
    project_path: Optional[str] = None
    limit: int = 200
    max_summary_chars: int = 2000
    low_importance_threshold: float = 0.35
    confirm: bool = False


class MemorySessionEventResponse(BaseModel):
    id: Optional[str] = None
    timestamp: Optional[str] = None
    route: Optional[str] = None
    provider_type: Optional[str] = None
    model: Optional[str] = None
    client: Optional[str] = None
    project_path: Optional[str] = None
    action: Optional[str] = None
    policy_action: Optional[str] = None
    policy_rule_id: Optional[str] = None
    dlp_findings_count: int = 0
    request_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0
    status_code: int = 0


class MemorySessionExtractionResponse(BaseModel):
    status: str
    dry_run: bool = True
    source: str
    project_path: Optional[str] = None
    client: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int
    generated_at: str
    summary_item_id: Optional[str] = None
    summary_truncated: bool = False
    summary_text: str
    dlp_findings_count: int
    event_count: int
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    success_count: int
    blocked_count: int
    approval_required_count: int
    request_tokens: int
    response_tokens: int
    total_tokens: int
    runtime_dlp_findings_count: int
    by_provider: dict = Field(default_factory=dict)
    by_model: dict = Field(default_factory=dict)
    by_client: dict = Field(default_factory=dict)
    by_route: dict = Field(default_factory=dict)
    by_action: dict = Field(default_factory=dict)
    by_project_path: dict = Field(default_factory=dict)
    by_status_code: dict = Field(default_factory=dict)
    events: list[MemorySessionEventResponse] = Field(default_factory=list)


class MemorySessionExtractRequest(BaseModel):
    project_path: Optional[str] = None
    client: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int = 200
    max_summary_chars: int = 2000
    confirm: bool = False


class MemoryReplayStepResponse(BaseModel):
    step_type: str
    timestamp: Optional[str] = None
    title: str
    summary: str
    metadata: dict = Field(default_factory=dict)


class MemoryReplayResponse(BaseModel):
    status: str
    dry_run: bool = True
    source: str
    project_path: Optional[str] = None
    client: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int
    generated_at: str
    replay_item_id: Optional[str] = None
    replay_truncated: bool = False
    replay_text: str
    dlp_findings_count: int
    step_count: int
    event_count: int
    memory_summary_count: int
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    success_count: int
    blocked_count: int
    approval_required_count: int
    request_tokens: int
    response_tokens: int
    total_tokens: int
    runtime_dlp_findings_count: int
    by_provider: dict = Field(default_factory=dict)
    by_model: dict = Field(default_factory=dict)
    by_client: dict = Field(default_factory=dict)
    by_route: dict = Field(default_factory=dict)
    by_action: dict = Field(default_factory=dict)
    by_project_path: dict = Field(default_factory=dict)
    by_summary_source: dict = Field(default_factory=dict)
    steps: list[MemoryReplayStepResponse] = Field(default_factory=list)


class MemoryReplayRequest(BaseModel):
    project_path: Optional[str] = None
    client: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int = 200
    max_replay_chars: int = 4000
    confirm: bool = False


class MemoryTimelineItemResponse(BaseModel):
    id: str
    project_path: str
    source_tool: Optional[str] = None
    memory_type: str
    content: str
    updated_at: str
    importance_score: float
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    stale: bool = False
    stale_reason: Optional[str] = None


class MemoryTimelineEventResponse(BaseModel):
    id: str
    timestamp: str
    event_type: str
    item_id: Optional[str] = None
    project_path: Optional[str] = None
    memory_type: Optional[str] = None
    source_tool: Optional[str] = None
    summary: str
    details: dict = Field(default_factory=dict)
    item: Optional[MemoryTimelineItemResponse] = None


class MemoryTimelineResponse(BaseModel):
    event_count: int
    limit: int
    project_path: Optional[str] = None
    item_id: Optional[str] = None
    by_event_type: dict = Field(default_factory=dict)
    events: list[MemoryTimelineEventResponse] = Field(default_factory=list)


@router.post("/items", status_code=201)
async def create_memory_item(body: MemoryItemCreate) -> dict:
    dlp_hits = findings_count(body.content)

    item_id = insert_item(
        project_path=body.project_path,
        memory_type=body.memory_type,
        content=body.content,
        source_tool=body.source_tool,
        importance_score=body.importance_score,
        tags=body.tags,
        pinned=body.pinned,
        raw_storage_mode=body.raw_storage_mode,
    )
    row = get_item(item_id) or {}
    metadata = storage_metadata(row)

    audit.log_event(
        route="/memory/items",
        provider_type="memory",
        model="",
        estimated_input_chars=len(body.content),
        dlp_findings_count=dlp_hits,
        action="memory_insert",
    )

    return {"id": item_id, "dlp_findings_count": dlp_hits, **metadata}


@router.get("/items", response_model=list[MemoryItemResponse])
async def get_memory_items(
    project_path: Optional[str] = Query(default=None),
    memory_type: Optional[str] = Query(default=None),
    source_tool: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    pinned: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[MemoryItemResponse]:
    rows = list_items(
        project_path=project_path,
        memory_type=memory_type,
        source_tool=source_tool,
        tag=tag,
        query_text=q,
        pinned=pinned,
        limit=limit,
    )
    return [_memory_response(row) for row in rows]


@router.get("/context", response_model=MemoryContextPackageResponse)
async def get_memory_context(
    project_path: Optional[str] = Query(default=None),
    memory_type: Optional[str] = Query(default=None),
    source_tool: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    pinned: Optional[bool] = Query(default=None),
    include_stale: bool = Query(default=False),
    limit: int = Query(default=20, le=50),
    max_chars: int = Query(default=4000, le=20000),
) -> MemoryContextPackageResponse:
    result = build_context_package(
        project_path=project_path,
        memory_type=memory_type,
        source_tool=source_tool,
        tag=tag,
        query_text=q,
        pinned=pinned,
        include_stale=include_stale,
        limit=limit,
        max_chars=max_chars,
    )
    audit.log_event(
        route="/memory/context",
        provider_type="memory",
        model="",
        estimated_input_chars=len(result["package_text"]),
        dlp_findings_count=result["dlp_findings_count"],
        action="memory_context_package",
    )
    return MemoryContextPackageResponse(**result)


@router.get("/extract", response_model=MemorySessionExtractionResponse)
async def get_memory_session_extraction_preview(
    project_path: Optional[str] = Query(default=None),
    client: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
    max_summary_chars: int = Query(default=2000, le=10000),
) -> MemorySessionExtractionResponse:
    result = extract_session(
        project_path=project_path,
        client=client,
        since=since,
        until=until,
        limit=limit,
        max_summary_chars=max_summary_chars,
        dry_run=True,
    )
    return MemorySessionExtractionResponse(**result)


@router.post("/extract", response_model=MemorySessionExtractionResponse)
async def apply_memory_session_extraction(body: MemorySessionExtractRequest) -> MemorySessionExtractionResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required for memory session extraction")

    result = extract_session(
        project_path=body.project_path,
        client=body.client,
        since=body.since,
        until=body.until,
        limit=body.limit,
        max_summary_chars=body.max_summary_chars,
        dry_run=False,
    )
    audit.log_event(
        route="/memory/extract",
        provider_type="memory",
        model="",
        estimated_input_chars=len(result["summary_text"]),
        dlp_findings_count=result["dlp_findings_count"],
        action="memory_extract_session",
        client=body.client or "",
    )
    return MemorySessionExtractionResponse(**result)


@router.get("/compact", response_model=MemoryCompactResponse)
async def get_memory_compaction_preview(
    project_path: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
    max_summary_chars: int = Query(default=2000, le=10000),
    low_importance_threshold: float = Query(default=0.35, ge=0.0, le=1.0),
) -> MemoryCompactResponse:
    result = compact(
        project_path=project_path,
        dry_run=True,
        limit=limit,
        max_summary_chars=max_summary_chars,
        low_importance_threshold=low_importance_threshold,
    )
    return MemoryCompactResponse(**result)


@router.post("/compact", response_model=MemoryCompactResponse)
async def apply_memory_compaction(body: MemoryCompactRequest) -> MemoryCompactResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required for memory compaction")

    result = compact(
        project_path=body.project_path,
        dry_run=False,
        limit=body.limit,
        max_summary_chars=body.max_summary_chars,
        low_importance_threshold=body.low_importance_threshold,
    )
    audit.log_event(
        route="/memory/compact",
        provider_type="memory",
        model="",
        estimated_input_chars=len(result["summary_text"]),
        dlp_findings_count=result["dlp_findings_count"],
        action="memory_compact",
    )
    return MemoryCompactResponse(**result)


@router.get("/replay", response_model=MemoryReplayResponse)
async def get_memory_replay_preview(
    project_path: Optional[str] = Query(default=None),
    client: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
    max_replay_chars: int = Query(default=4000, le=20000),
) -> MemoryReplayResponse:
    result = replay_session(
        project_path=project_path,
        client=client,
        since=since,
        until=until,
        limit=limit,
        max_replay_chars=max_replay_chars,
        dry_run=True,
    )
    return MemoryReplayResponse(**result)


@router.post("/replay", response_model=MemoryReplayResponse)
async def apply_memory_replay(body: MemoryReplayRequest) -> MemoryReplayResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required for memory replay")

    result = replay_session(
        project_path=body.project_path,
        client=body.client,
        since=body.since,
        until=body.until,
        limit=body.limit,
        max_replay_chars=body.max_replay_chars,
        dry_run=False,
    )
    audit.log_event(
        route="/memory/replay",
        provider_type="memory",
        model="",
        estimated_input_chars=len(result["replay_text"]),
        dlp_findings_count=result["dlp_findings_count"],
        action="memory_replay_session",
        client=body.client or "",
    )
    return MemoryReplayResponse(**result)


@router.get("/timeline", response_model=MemoryTimelineResponse)
async def get_memory_timeline(
    project_path: Optional[str] = Query(default=None),
    item_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> MemoryTimelineResponse:
    return MemoryTimelineResponse(**memory_timeline(project_path=project_path, item_id=item_id, limit=limit))


@router.get("/events", response_model=list[MemoryEventResponse])
async def get_memory_events(
    item_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> list[MemoryEventResponse]:
    return [_event_response(row) for row in list_events(item_id=item_id, limit=limit)]


@router.patch("/items/{item_id}", response_model=MemoryItemResponse)
async def patch_memory_item(item_id: str, body: MemoryItemUpdate) -> MemoryItemResponse:
    fields = _fields_set(body)
    updates = {
        field: getattr(body, field)
        for field in fields
        if field != "tags"
    }
    tags = body.tags if "tags" in fields else None
    dlp_hits = findings_count(body.content) if "content" in fields and body.content is not None else 0

    if not update_item(item_id, updates, tags=tags):
        raise HTTPException(status_code=404, detail="memory item not found")

    row = get_item(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="memory item not found")

    audit.log_event(
        route=f"/memory/items/{item_id}",
        provider_type="memory",
        model="",
        estimated_input_chars=len(body.content or "") if "content" in fields else 0,
        dlp_findings_count=dlp_hits,
        action="memory_update",
    )
    return _memory_response(row)


@router.delete("/items/{item_id}")
async def remove_memory_item(
    item_id: str,
    confirm: bool = Query(default=False),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required for memory delete")

    if not delete_item(item_id):
        raise HTTPException(status_code=404, detail="memory item not found")

    audit.log_event(
        route=f"/memory/items/{item_id}",
        provider_type="memory",
        model="",
        estimated_input_chars=0,
        dlp_findings_count=0,
        action="memory_delete",
    )
    return {"status": "deleted", "id": item_id}


def _memory_response(row: dict) -> MemoryItemResponse:
    content = row.get("content") or ""
    redacted_content = row.get("redacted_content")
    safe_content = redacted_content if redacted_content is not None else redact_text(content)
    return MemoryItemResponse(
        id=row["id"],
        project_path=row["project_path"],
        source_tool=row["source_tool"],
        memory_type=row["memory_type"],
        content=safe_content,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        importance_score=row["importance_score"],
        tags=row.get("tags", []),
        pinned=bool(row.get("pinned")),
        redacted=redaction_was_applied(safe_content, content),
        stale=bool(row.get("stale")),
        stale_reason=row.get("stale_reason"),
        age_days=row.get("age_days"),
        stale_after_days=int(row.get("stale_after_days") or 30),
        last_attached_at=row.get("last_attached_at"),
        **storage_metadata(row),
    )


def _event_response(row: dict) -> MemoryEventResponse:
    return MemoryEventResponse(
        id=row["id"],
        item_id=row.get("item_id"),
        event_type=row["event_type"],
        details=_safe_details(row.get("details")),
        timestamp=row["timestamp"],
    )


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


def _fields_set(model: BaseModel) -> set:
    return set(getattr(model, "model_fields_set", getattr(model, "__fields_set__", set())))
