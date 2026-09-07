import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from .. import config


router = APIRouter()

_LOCAL_SEARCH = [".claude/mcp.json", ".mcp.json", "mcp.json"]
_GLOBAL_SEARCH = [Path.home() / ".claude" / "mcp.json"]


def _empty_summary() -> dict:
    return {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}


def _repo_root() -> Path:
    return config.REPO_ROOT.expanduser().resolve()


def _configured_mcp_path() -> Optional[Path]:
    if not config.MCP_CONFIG_PATH.strip():
        return None
    return Path(config.MCP_CONFIG_PATH).expanduser()


def _candidate_paths(repo_root: Path) -> list[Path]:
    configured = _configured_mcp_path()
    if configured:
        return [configured]
    return [repo_root / rel for rel in _LOCAL_SEARCH] + _GLOBAL_SEARCH


def _find_mcp_config(repo_root: Path) -> tuple[Optional[Path], list[str]]:
    candidates = _candidate_paths(repo_root)
    searched = [str(path) for path in candidates]
    for path in candidates:
        if path.exists():
            return path, searched
    return None, searched


def _ensure_inspector_importable() -> None:
    try:
        import mcp_inspector  # noqa: F401
        return
    except ImportError:
        repo_root = Path(__file__).resolve().parents[4]
        inspector_src = repo_root / "mcp-inspector" / "src"
        if inspector_src.exists() and str(inspector_src) not in sys.path:
            sys.path.insert(0, str(inspector_src))


def _ensure_runtime_guard_importable() -> None:
    try:
        import runtime_guard  # noqa: F401
        return
    except ImportError:
        repo_root = Path(__file__).resolve().parents[4]
        runtime_src = repo_root / "runtime-guard" / "src"
        policy_src = repo_root / "policy-engine" / "src"
        for src in (runtime_src, policy_src):
            if src.exists() and str(src) not in sys.path:
                sys.path.insert(0, str(src))


def _app_home() -> Optional[Path]:
    if not config.MCP_APP_HOME.strip():
        return None
    return Path(config.MCP_APP_HOME).expanduser()


def _server_name(source: str) -> str:
    marker = "mcpServers."
    if marker not in source:
        return "unknown"
    tail = source.split(marker, 1)[1]
    return tail.split(".", 1)[0]


def _finding_dict(finding) -> dict:
    data = asdict(finding)
    data["server_name"] = _server_name(data.get("source", ""))
    return data


@router.get("/scan")
async def scan_mcp() -> dict:
    repo_root = _repo_root()
    config_path, searched = _find_mcp_config(repo_root)
    base = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "scan_target": str(config_path) if config_path else None,
        "repo_root": str(repo_root),
        "searched": searched,
    }
    if config_path is None:
        return {
            **base,
            "status": "not_found",
            "summary": _empty_summary(),
            "findings": [],
        }

    try:
        _ensure_inspector_importable()
        from mcp_inspector.scanner import scan_mcp_config

        findings = scan_mcp_config(str(config_path), str(repo_root))
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "error": f"could not scan MCP config: {exc}",
            "summary": _empty_summary(),
            "findings": [],
        }

    summary = _empty_summary()
    for finding in findings:
        summary[finding.severity] = summary.get(finding.severity, 0) + 1
    summary["total"] = sum(summary[level] for level in ("critical", "high", "medium", "low"))

    return {
        **base,
        "status": "scanned",
        "summary": summary,
        "findings": [_finding_dict(finding) for finding in findings],
    }


@router.get("/apps")
async def mcp_apps() -> dict:
    repo_root = _repo_root()
    home = _app_home()
    base = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "home": str(home) if home else str(Path.home()),
    }

    try:
        _ensure_runtime_guard_importable()
        from runtime_guard.mcp_apps import discover_mcp_apps

        statuses = discover_mcp_apps(repo_root=repo_root, home=home)
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "error": f"could not inspect MCP app configs: {exc}",
            "summary": _app_summary([]),
            "apps": [],
        }

    apps = [status.to_dict() for status in statuses]
    return {
        **base,
        "status": "ok",
        "summary": _app_summary(apps),
        "apps": apps,
    }


@router.post("/apps/{app_id}/protect")
async def protect_mcp_app(app_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    repo_root = _repo_root()
    home = _app_home()
    try:
        _ensure_runtime_guard_importable()
        from runtime_guard.mcp_apps import protect_mcp_app as protect

        result = protect(
            app_id=app_id,
            repo_root=repo_root,
            home=home,
            policy_path=config.POLICY_PATH,
            audit_log=config.LOG_DIR / "mcp_audit.jsonl",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not protect MCP app: {exc}") from exc

    return _mutation_response("protect", repo_root, home, result.to_dict())


@router.post("/apps/{app_id}/unprotect")
async def unprotect_mcp_app(app_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    repo_root = _repo_root()
    home = _app_home()
    try:
        _ensure_runtime_guard_importable()
        from runtime_guard.mcp_apps import unprotect_mcp_app as unprotect

        result = unprotect(app_id=app_id, repo_root=repo_root, home=home)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not unprotect MCP app: {exc}") from exc

    return _mutation_response("unprotect", repo_root, home, result.to_dict())


def _app_summary(apps: list[dict]) -> dict:
    summary = {
        "total": len(apps),
        "protected": 0,
        "unprotected": 0,
        "partial": 0,
        "missing": 0,
        "invalid": 0,
        "empty": 0,
        "actionable": 0,
        "drifted": 0,
    }
    for app in apps:
        status = app.get("status", "missing")
        if status in summary:
            summary[status] += 1
        if app.get("repair_available") or status in {"unprotected", "partial", "invalid"}:
            summary["actionable"] += 1
        if app.get("drift_detected"):
            summary["drifted"] += 1
    return summary


def _require_confirm(body: Optional[dict]) -> None:
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="confirm=true is required for MCP app config changes")


def _mutation_response(action: str, repo_root: Path, home: Optional[Path], result: dict) -> dict:
    return {
        "status": "ok",
        "action": action,
        "action_time": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "home": str(home) if home else str(Path.home()),
        "result": result,
    }
