import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query

from .. import config
from ..providers.passthrough import check_provider_health


router = APIRouter()


@router.get("/health")
async def providers_health(live: bool = Query(default=False)) -> dict:
    return await check_provider_health(live=live)


@router.get("/integrations")
async def provider_integrations() -> dict:
    base = _gateway_base()
    try:
        _ensure_cli_importable()
        from spectrona_cli.routing import discover_routing_integrations

        statuses = discover_routing_integrations(gateway_base_url=base)
    except Exception as exc:
        return {
            "status": "error",
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "gateway_base_url": base,
            "error": f"could not inspect provider routing integrations: {exc}",
            "summary": _integration_summary([]),
            "integrations": [],
        }

    integrations = [status.to_dict() for status in statuses]
    return {
        "status": "ok",
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "gateway_base_url": base,
        "summary": _integration_summary(integrations),
        "integrations": integrations,
    }


@router.post("/local-runtimes/{runtime_id}/select")
async def select_local_runtime(runtime_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    try:
        _ensure_cli_importable()
        from spectrona_cli.local_llms import local_config_env_overrides, select_local_llm

        overrides = local_config_env_overrides()
        if overrides:
            raise HTTPException(
                status_code=409,
                detail=f"cannot select local runtime while env override is active: {', '.join(overrides)}",
            )

        result = select_local_llm(runtime_id)
        config.apply_local_provider(
            provider=result.after_provider,
            base_url=result.after_base_url,
            health_path=result.after_health_path,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not select local runtime: {exc}") from exc

    return _mutation_response("select_local_runtime", _gateway_base(), result.to_dict())


@router.post("/integrations/{integration_id}/protect")
async def protect_provider_integration(integration_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    base = _gateway_base()
    try:
        _ensure_cli_importable()
        from spectrona_cli.routing import apply_routing_integration

        result = apply_routing_integration(integration_id=integration_id, gateway_base_url=base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not protect provider routing integration: {exc}") from exc

    return _mutation_response("protect", base, result.to_dict())


@router.post("/integrations/{integration_id}/unprotect")
async def unprotect_provider_integration(integration_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    base = _gateway_base()
    try:
        _ensure_cli_importable()
        from spectrona_cli.routing import undo_routing_integration

        result = undo_routing_integration(integration_id=integration_id, gateway_base_url=base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not unprotect provider routing integration: {exc}") from exc

    return _mutation_response("unprotect", base, result.to_dict())


def _gateway_base() -> str:
    return f"http://{config.HOST}:{config.PORT}"


def _ensure_cli_importable() -> None:
    try:
        import spectrona_cli  # noqa: F401
        return
    except ImportError:
        repo_root = Path(__file__).resolve().parents[4]
        cli_src = repo_root / "spectrona-cli" / "src"
        if cli_src.exists() and str(cli_src) not in sys.path:
            sys.path.insert(0, str(cli_src))


def _integration_summary(integrations: list[dict]) -> dict:
    summary = {
        "total": len(integrations),
        "protected": 0,
        "unprotected": 0,
        "partial": 0,
        "missing": 0,
        "actionable": 0,
        "drifted": 0,
    }
    for item in integrations:
        status = item.get("status", "missing")
        if status in summary:
            summary[status] += 1
        if item.get("repair_available"):
            summary["actionable"] += 1
        if item.get("drift_detected"):
            summary["drifted"] += 1
    return summary


def _require_confirm(body: Optional[dict]) -> None:
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="confirm=true is required for provider routing config changes")


def _mutation_response(action: str, gateway_base_url: str, result: dict) -> dict:
    return {
        "status": "ok",
        "action": action,
        "action_time": datetime.now(timezone.utc).isoformat(),
        "gateway_base_url": gateway_base_url,
        "result": result,
    }
