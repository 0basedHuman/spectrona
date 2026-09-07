from fastapi import APIRouter, Query

from ..events.store import block_summary, dlp_summary, list_events, token_usage_summary

router = APIRouter()


@router.get("/recent")
async def recent_events(
    limit: int = Query(default=50, ge=1, le=500),
    provider_type: str = Query(default=""),
    client: str = Query(default=""),
    project_path: str = Query(default=""),
    action: str = Query(default=""),
) -> list[dict]:
    return list_events(
        limit=limit,
        provider_type=provider_type or None,
        client=client or None,
        project_path=project_path or None,
        action=action or None,
    )


@router.get("/token-usage")
async def token_usage() -> dict:
    return token_usage_summary()


@router.get("/blocks")
async def blocks(limit: int = Query(default=10, ge=1, le=100)) -> dict:
    return block_summary(limit=limit)


@router.get("/dlp")
async def dlp(limit: int = Query(default=10, ge=1, le=100)) -> dict:
    return dlp_summary(limit=limit)
