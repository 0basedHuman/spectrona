from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query

from .. import config
from .providers import _ensure_cli_importable, _gateway_base


router = APIRouter()


@router.get("")
async def integrations_status(live: bool = Query(default=False)) -> dict:
    try:
        _ensure_cli_importable()
        from spectrona_cli.integration_manager import collect_status

        return collect_status(
            repo_root=config.REPO_ROOT,
            home=_app_home(),
            gateway_base_url=_gateway_base(),
            live_local_llms=live,
        )
    except Exception as exc:
        return {
            "status": "error",
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "gateway_base_url": _gateway_base(),
            "repo_root": str(config.REPO_ROOT),
            "home": str(_app_home()),
            "error": f"could not inspect integrations: {exc}",
            "summary": _empty_summary(),
            "provider_routing": [],
            "mcp_apps": [],
            "local_llms": [],
            "local_llm_summary": {
                "total": 0,
                "configured": 0,
                "reachable": 0,
                "ok": 0,
                "unreachable": 0,
                "fallback": 0,
                "live_checked": live,
            },
        }


@router.post("/repair")
async def repair_integrations(body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    try:
        _ensure_cli_importable()
        from spectrona_cli.integration_manager import repair

        return repair(
            repo_root=config.REPO_ROOT,
            home=_app_home(),
            gateway_base_url=_gateway_base(),
            policy_path=config.POLICY_PATH,
            audit_log=config.LOG_DIR / "mcp_audit.jsonl",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not repair integrations: {exc}") from exc


def _app_home():
    if config.MCP_APP_HOME:
        from pathlib import Path

        return Path(config.MCP_APP_HOME).expanduser()
    return None


def _require_confirm(body: Optional[dict]) -> None:
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="confirm=true is required for integration repair")


def _empty_summary() -> dict:
    return {
        "total": 0,
        "protected": 0,
        "unprotected": 0,
        "partial": 0,
        "missing": 0,
        "invalid": 0,
        "empty": 0,
        "actionable": 0,
        "drifted": 0,
        "provider_total": 0,
        "provider_actionable": 0,
        "mcp_total": 0,
        "mcp_actionable": 0,
        "local_llm_total": 0,
        "local_llm_configured": 0,
        "local_llm_fallback": 0,
        "local_llm_reachable": 0,
    }
