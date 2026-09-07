import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .local_llms import discover_local_llms, local_llm_summary
from .routing import apply_routing_integration, discover_routing_integrations, gateway_base


def collect_status(
    repo_root: Optional[Path] = None,
    home: Optional[Path] = None,
    gateway_base_url: Optional[str] = None,
    live_local_llms: bool = False,
) -> dict:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_apps import discover_mcp_apps

    base = gateway_base(gateway_base_url)
    root = (repo_root or Path.cwd()).expanduser().resolve()
    home_path = home.expanduser() if home else Path.home()

    provider_items = [item.to_dict() for item in discover_routing_integrations(gateway_base_url=base, repo_root=root)]
    mcp_items = [item.to_dict() for item in discover_mcp_apps(repo_root=root, home=home_path)]
    local_llms = discover_local_llms(live=live_local_llms)
    local_llm_items = [item.to_dict() for item in local_llms]
    return {
        "status": "ok",
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "gateway_base_url": base,
        "repo_root": str(root),
        "home": str(home_path),
        "summary": _combined_summary(provider_items, mcp_items, local_llm_items),
        "provider_routing": provider_items,
        "mcp_apps": mcp_items,
        "local_llms": local_llm_items,
        "local_llm_summary": local_llm_summary(local_llms),
    }


def repair(
    repo_root: Optional[Path] = None,
    home: Optional[Path] = None,
    gateway_base_url: Optional[str] = None,
    policy_path: Optional[Path] = None,
    audit_log: Optional[Path] = None,
    spectrona_command: str = "spectrona",
) -> dict:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_apps import protect_mcp_app, unprotect_mcp_app

    base = gateway_base(gateway_base_url)
    root = (repo_root or Path.cwd()).expanduser().resolve()
    home_path = home.expanduser() if home else Path.home()
    before = collect_status(repo_root=root, home=home_path, gateway_base_url=base)

    provider_results = []
    mcp_results = []
    errors = []

    for item in before["provider_routing"]:
        action = item.get("recommended_action")
        if not item.get("repair_available") or action not in {"setup", "repair"}:
            continue
        try:
            result = apply_routing_integration(item["integration_id"], path=Path(item["path"]), gateway_base_url=base)
            provider_results.append(result.to_dict())
        except Exception as exc:
            errors.append(_error("provider_routing", item.get("integration_id", ""), exc))

    for item in before["mcp_apps"]:
        action = item.get("recommended_action")
        if not item.get("repair_available") or action not in {"protect", "repair", "restore"}:
            continue
        try:
            if action in {"protect", "repair"}:
                result = protect_mcp_app(
                    app_id=item["app_id"],
                    repo_root=root,
                    home=home_path,
                    policy_path=policy_path,
                    audit_log=audit_log,
                    spectrona_command=spectrona_command,
                )
            else:
                result = unprotect_mcp_app(app_id=item["app_id"], repo_root=root, home=home_path)
            mcp_results.append(result.to_dict())
        except Exception as exc:
            errors.append(_error("mcp_app", item.get("app_id", ""), exc))

    after = collect_status(repo_root=root, home=home_path, gateway_base_url=base)
    status = "ok" if not errors else "partial_error"
    return {
        "status": status,
        "action": "repair",
        "action_time": datetime.now(timezone.utc).isoformat(),
        "gateway_base_url": base,
        "repo_root": str(root),
        "home": str(home_path),
        "summary": {
            "provider_attempted": len(provider_results),
            "mcp_attempted": len(mcp_results),
            "changed": sum(1 for item in provider_results + mcp_results if item.get("changed")),
            "errors": len(errors),
            "before": before["summary"],
            "after": after["summary"],
        },
        "provider_results": provider_results,
        "mcp_results": mcp_results,
        "errors": errors,
    }


def status_to_json(status: dict) -> str:
    return json.dumps(status, indent=2)


def repair_to_json(result: dict) -> str:
    return json.dumps(result, indent=2)


def _combined_summary(provider_items: list[dict], mcp_items: list[dict], local_llm_items: list[dict]) -> dict:
    protectable_items = provider_items + mcp_items
    summary = {
        "total": len(protectable_items),
        "protected": 0,
        "unprotected": 0,
        "partial": 0,
        "missing": 0,
        "invalid": 0,
        "empty": 0,
        "actionable": 0,
        "drifted": 0,
        "provider_total": len(provider_items),
        "provider_actionable": 0,
        "mcp_total": len(mcp_items),
        "mcp_actionable": 0,
        "local_llm_total": len(local_llm_items),
        "local_llm_configured": 0,
        "local_llm_fallback": 0,
        "local_llm_reachable": 0,
    }
    for item in protectable_items:
        status = item.get("status", "missing")
        if status in summary:
            summary[status] += 1
        if item.get("repair_available"):
            summary["actionable"] += 1
        if item.get("drift_detected"):
            summary["drifted"] += 1
    summary["provider_actionable"] = sum(1 for item in provider_items if item.get("repair_available"))
    summary["mcp_actionable"] = sum(1 for item in mcp_items if item.get("repair_available"))
    summary["local_llm_configured"] = sum(1 for item in local_llm_items if item.get("selected_config"))
    summary["local_llm_fallback"] = sum(1 for item in local_llm_items if item.get("fallback_config"))
    summary["local_llm_reachable"] = sum(1 for item in local_llm_items if item.get("reachable"))
    return summary


def _error(kind: str, item_id: str, exc: Exception) -> dict:
    return {
        "kind": kind,
        "id": item_id,
        "error": _redact_text(str(exc)),
    }


def _redact_text(value: str) -> str:
    text = str(value)
    for marker in ("sk-", "ghp_", "github_pat_", "xoxb-", "xoxp-"):
        idx = text.find(marker)
        while idx != -1:
            end = idx
            while end < len(text) and text[end] not in " \t\r\n'\"`":
                end += 1
            token = text[idx:end]
            if len(token) > len(marker):
                text = text.replace(token, marker + "[REDACTED_SECRET]")
            idx = text.find(marker, idx + len(marker))
    return text


def _ensure_runtime_guard_importable() -> None:
    try:
        import runtime_guard  # noqa: F401
        return
    except ImportError:
        component_root = _component_root()
        for src in (
            component_root / "spectrona-detection" / "src",
            component_root / "runtime-guard" / "src",
            component_root / "policy-engine" / "src",
        ):
            if src.exists() and str(src) not in sys.path:
                sys.path.insert(0, str(src))


def _component_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "runtime-guard" / "src").exists():
            return parent
    return current.parents[3]
