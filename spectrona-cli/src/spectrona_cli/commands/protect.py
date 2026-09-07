from typing import Optional

from ..routing import (
    apply_routing_integration,
    claude_path,
    codex_path,
    discover_routing_integrations,
    gateway_base,
    routing_statuses_to_json,
    undo_routing_integration,
    vscode_settings,
    vscode_settings_path,
)


def claude(print_only: bool = True, apply: bool = False, undo: bool = False, path: Optional[str] = None) -> int:
    target = claude_path(path)
    if apply:
        apply_routing_integration("claude", path=target)
        print(f"Wrote Claude routing env file: {target}")
        print(f"Load it with: source {target}")
        return 0
    if undo:
        result = undo_routing_integration("claude", path=target)
        changed = result.changed
        print(f"Removed Spectrona Claude routing from: {target}" if changed else f"No Claude routing file found: {target}")
        return 0

    print("To route Claude Code through Spectrona Gateway, set these env vars:\n")
    print(f"  export ANTHROPIC_BASE_URL={gateway_base()}/anthropic")
    print("  export ANTHROPIC_API_KEY=spectrona-local-token")
    print()
    print("Or write a reversible env file:")
    print(f"  spectrona protect claude --apply --path {target}")
    print(f"  source {target}")
    print()
    print("Then start the gateway:  spectrona start")
    print("Verify routing:          spectrona gateway health")
    print()
    print("NOTE: --print does not modify any files.")
    return 0


def codex(print_only: bool = True, apply: bool = False, undo: bool = False, path: Optional[str] = None) -> int:
    target = codex_path(path)
    if apply:
        apply_routing_integration("codex", path=target)
        print(f"Updated Codex config: {target}")
        print(f"Backup path: {target.with_suffix(target.suffix + '.spectrona.bak')}")
        return 0
    if undo:
        result = undo_routing_integration("codex", path=target)
        changed = result.changed
        print(f"Removed Spectrona Codex routing from: {target}" if changed else f"No Codex config found: {target}")
        return 0

    print("To route OpenAI Codex through Spectrona Gateway:\n")
    print("  Add to your Codex config:")
    print()
    print('  model_provider = "spectrona"')
    print()
    print("  [model_providers.spectrona]")
    print('  name = "Spectrona Local Gateway"')
    print(f'  base_url = "{gateway_base()}/openai/v1"')
    print('  env_key = "SPECTRONA_API_KEY"')
    print()
    print("  Set:  export SPECTRONA_API_KEY=spectrona-local-token")
    print()
    print("Or patch it reversibly:")
    print(f"  spectrona protect codex --apply --path {target}")
    print()
    print("NOTE: --print does not modify any files.")
    return 0


def vscode(print_only: bool = True, apply: bool = False, undo: bool = False, path: Optional[str] = None) -> int:
    target = vscode_settings_path(path)
    if apply:
        apply_routing_integration("vscode", path=target)
        print(f"Updated VS Code workspace settings: {target}")
        print(f"Backup path: {target.with_suffix(target.suffix + '.spectrona.bak')}")
        return 0
    if undo:
        result = undo_routing_integration("vscode", path=target)
        changed = result.changed
        print(f"Removed Spectrona VS Code routing from: {target}" if changed else f"No VS Code routing found: {target}")
        return 0

    snippet = vscode_settings()
    print("To route VS Code integrated-terminal AI clients through Spectrona Gateway:\n")
    print("  Add these settings to your workspace .vscode/settings.json:")
    print()
    print("  " + "\n  ".join(_json_snippet(snippet).splitlines()))
    print()
    print("Or patch it reversibly:")
    print(f"  spectrona protect vscode --apply --path {target}")
    print()
    print("NOTE: --print does not modify any files.")
    return 0


def status(output_json: bool = False) -> int:
    statuses = discover_routing_integrations()
    if output_json:
        print(routing_statuses_to_json(statuses))
        return 0

    print("Spectrona provider routing status")
    print("─" * 72)
    for item in statuses:
        marker = _status_marker(item.status)
        print(f"{marker} {item.label:<10} {item.provider:<10} {item.status:<11} action={item.recommended_action}")
        print(f"    {item.path}")
        print(f"    target={item.expected_base_url} backup={'yes' if item.backup_exists else 'no'}")
        if item.drift_detected:
            print(f"    drift=yes reason={item.drift_reason}")
    return 0


def _status_marker(state: str) -> str:
    if state == "protected":
        return "[ok]"
    if state in {"unprotected", "missing", "partial"}:
        return "[!]"
    return "[-]"


def _json_snippet(value: dict) -> str:
    import json

    return json.dumps(value, indent=2)
