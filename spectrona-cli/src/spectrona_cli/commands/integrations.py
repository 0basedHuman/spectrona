import sys
from pathlib import Path
from typing import Optional

from ..integration_manager import collect_status, repair as repair_integrations, repair_to_json, status_to_json


def status(repo_root: Optional[str], home: Optional[str], live: bool, output_json: bool) -> int:
    try:
        result = collect_status(
            repo_root=Path(repo_root).expanduser() if repo_root else None,
            home=Path(home).expanduser() if home else None,
            live_local_llms=live,
        )
    except Exception as exc:
        print(f"Error: could not inspect integrations: {exc}", file=sys.stderr)
        return 2

    if output_json:
        print(status_to_json(result))
        return 0

    print("Spectrona integration manager")
    print("-" * 72)
    summary = result["summary"]
    print(
        f"Protected: {summary['protected']}/{summary['total']}  "
        f"Actionable: {summary['actionable']}  Drifted: {summary['drifted']}"
    )
    print("")
    print("Provider routing")
    for item in result["provider_routing"]:
        _print_provider(item)
    print("")
    print("MCP apps")
    for item in result["mcp_apps"]:
        _print_mcp(item)
    print("")
    print("Local LLM runtimes")
    for item in result["local_llms"]:
        _print_local_llm(item)
    return 0


def repair(
    repo_root: Optional[str],
    home: Optional[str],
    policy_path: Optional[str],
    audit_log: Optional[str],
    spectrona_command: str,
    confirm: bool,
    output_json: bool,
) -> int:
    if not confirm:
        print("Error: integrations repair requires --confirm", file=sys.stderr)
        return 2

    try:
        result = repair_integrations(
            repo_root=Path(repo_root).expanduser() if repo_root else None,
            home=Path(home).expanduser() if home else None,
            policy_path=Path(policy_path).expanduser() if policy_path else None,
            audit_log=Path(audit_log).expanduser() if audit_log else None,
            spectrona_command=spectrona_command,
        )
    except Exception as exc:
        print(f"Error: could not repair integrations: {exc}", file=sys.stderr)
        return 2

    if output_json:
        print(repair_to_json(result))
        return 0 if result["status"] == "ok" else 1

    summary = result["summary"]
    print("Spectrona integration repair")
    print("-" * 72)
    print(f"Provider actions: {summary['provider_attempted']}")
    print(f"MCP actions: {summary['mcp_attempted']}")
    print(f"Changed: {summary['changed']}")
    if result["errors"]:
        print(f"Errors: {summary['errors']}")
        for item in result["errors"]:
            print(f"  {item['kind']}:{item['id']} {item['error']}")
        return 1
    print("Errors: 0")
    return 0


def _print_provider(item: dict) -> None:
    marker = _status_marker(item.get("status", ""))
    print(
        f"{marker} {item['label']:<10} {item['status']:<11} "
        f"action={item['recommended_action']} target={item['expected_base_url']}"
    )
    if item.get("drift_detected"):
        print(f"    drift=yes reason={item.get('drift_reason', '')}")


def _print_mcp(item: dict) -> None:
    marker = _status_marker(item.get("status", ""))
    print(
        f"{marker} {item['label']:<18} {item['scope']:<9} {item['status']:<11} "
        f"action={item['recommended_action']} servers={item['servers']}"
    )
    if item.get("drift_detected"):
        print(f"    drift=yes reason={item.get('drift_reason', '')}")


def _print_local_llm(item: dict) -> None:
    marker = _status_marker(item.get("status", ""))
    selected = "selected" if item.get("selected_config") else "fallback" if item.get("fallback_config") else "candidate"
    live = "live" if item.get("live_checked") else "not checked"
    print(
        f"{marker} {item['label']:<18} {item['status']:<11} "
        f"{selected:<9} {live:<11} {item['base_url']}"
    )


def _status_marker(status: str) -> str:
    if status in {"protected", "ok", "configured"}:
        return "[ok]"
    if status in {"unprotected", "missing", "partial", "unreachable", "auth_error", "upstream_error", "missing_api_key"}:
        return "[!]"
    if status == "invalid":
        return "[x]"
    return "[-]"
