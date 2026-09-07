import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config_file import policy_path as default_policy_path


_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{8,}"),
)


def status(path: Optional[str], output_json: bool) -> int:
    try:
        info = _current_policy_response(_target_policy_path(path))
    except Exception as exc:
        print(f"Error: could not load policy: {_redact_text(str(exc))}", file=sys.stderr)
        return 2

    if output_json:
        print(json.dumps(info))
        return 0

    print("Spectrona policy")
    print("─" * 72)
    print(f"Path: {info['path']}")
    print(f"Exists: {'yes' if info['exists'] else 'no'}")
    print(f"Active preset: {info['active_preset_id']}")
    print(f"Default action: {info['policy']['default_action']}")
    print(f"Rules: {info['summary']['enabled_rules']} enabled / {info['summary']['rules']} total")
    for rule in info["policy"]["rules"]:
        state = "on" if rule.get("enabled") else "off"
        print(f"  [{state}] {rule.get('id')} -> {rule.get('action')}")
    return 0


def presets(output_json: bool) -> int:
    _ensure_policy_engine_importable()
    from policy_engine.presets import list_policy_presets

    items = [_preset_summary(preset) for preset in list_policy_presets()]
    if output_json:
        print(json.dumps(items))
        return 0

    print("Spectrona policy presets")
    print("─" * 72)
    for item in items:
        print(f"{item['preset_id']:<10} {item['enabled_rules']} enabled / {item['rules']} rules")
        print(f"    {item['description']}")
    return 0


def apply_preset(path: Optional[str], preset_id: str, confirm: bool, output_json: bool) -> int:
    if not confirm:
        print("Error: policy changes require --confirm", file=sys.stderr)
        return 2
    try:
        result = _apply_preset(_target_policy_path(path), preset_id)
    except Exception as exc:
        print(f"Error: could not apply policy preset: {_redact_text(str(exc))}", file=sys.stderr)
        return 2

    if output_json:
        print(json.dumps(result))
        return 0

    print(f"Applied policy preset: {result['preset_id']}")
    print(f"Path: {result['path']}")
    if result["backup_path"]:
        print(f"Backup: {result['backup_path']}")
    print(f"Changed: {'yes' if result['changed'] else 'no'}")
    return 0


def backups(path: Optional[str], output_json: bool) -> int:
    target = _target_policy_path(path)
    items = [_backup_summary(item) for item in _policy_backup_files(target)]
    result = {
        "status": "ok",
        "path": str(target),
        "backups": items,
        "summary": {
            "total": len(items),
            "restorable": sum(1 for item in items if item.get("status") == "ok"),
        },
    }
    if output_json:
        print(json.dumps(result))
        return 0

    print("Spectrona policy backups")
    print("─" * 72)
    if not items:
        print("No policy backups found.")
        return 0
    for item in items:
        print(f"{item['backup_id']}  {item['status']}  {item['active_preset_id']}")
        print(f"    modified={item['modified_at']} size={item['size_bytes']}")
    return 0


def restore(path: Optional[str], backup_id: str, confirm: bool, output_json: bool) -> int:
    if not confirm:
        print("Error: policy restore requires --confirm", file=sys.stderr)
        return 2
    try:
        result = _restore_backup(_target_policy_path(path), backup_id)
    except Exception as exc:
        print(f"Error: could not restore policy backup: {_redact_text(str(exc))}", file=sys.stderr)
        return 2

    if output_json:
        print(json.dumps(result))
        return 0

    print(f"Restored policy backup: {result['backup_id']}")
    print(f"Path: {result['path']}")
    print(f"Restored from: {result['restored_from']}")
    if result["current_backup_path"]:
        print(f"Current policy backup: {result['current_backup_path']}")
    print(f"Changed: {'yes' if result['changed'] else 'no'}")
    return 0


def _target_policy_path(path: Optional[str]) -> Path:
    return Path(path).expanduser() if path else default_policy_path()


def _current_policy_response(path: Path) -> dict:
    policy = _load_policy(path)
    return {
        "status": "ok",
        "path": str(path),
        "exists": path.exists(),
        "active_preset_id": _active_preset_id(policy),
        "policy": _policy_dict(policy),
        "summary": _policy_summary(policy),
    }


def _apply_preset(path: Path, preset_id: str) -> dict:
    _ensure_policy_engine_importable()
    from policy_engine import load_policy_text
    from policy_engine.presets import get_policy_preset

    preset = get_policy_preset(preset_id)
    current_text = _current_policy_text(path)
    changed = _normalized(current_text) != _normalized(preset.text)
    backup_path = ""
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup = _next_backup_path(path)
            backup.write_text(path.read_text())
            _chmod_user_only(backup)
            backup_path = str(backup)
        path.write_text(preset.text)
        _chmod_user_only(path)

    policy = load_policy_text(preset.text)
    return {
        "status": "ok",
        "action": "apply_preset",
        "action_time": datetime.now(timezone.utc).isoformat(),
        "preset_id": preset.id,
        "changed": changed,
        "path": str(path),
        "backup_path": backup_path,
        "active_preset_id": preset.id,
        "policy": _policy_dict(policy),
    }


def _restore_backup(path: Path, backup_id: str) -> dict:
    _ensure_policy_engine_importable()
    from policy_engine import load_policy_text

    backup_path = _backup_by_id(path, backup_id)
    if backup_path is None:
        candidate = Path(backup_id).expanduser()
        if candidate.exists() and candidate.is_file():
            backup_path = candidate
        else:
            raise ValueError(f"Unknown policy backup: {backup_id}")

    restored_text = backup_path.read_text()
    restored_policy = load_policy_text(restored_text)
    current_text = _current_policy_text(path)
    changed = _normalized(current_text) != _normalized(restored_text)
    current_backup_path = ""
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            current_backup = _next_backup_path(path)
            current_backup.write_text(path.read_text())
            _chmod_user_only(current_backup)
            current_backup_path = str(current_backup)
        path.write_text(restored_text)
        _chmod_user_only(path)

    return {
        "status": "ok",
        "action": "restore_backup",
        "action_time": datetime.now(timezone.utc).isoformat(),
        "backup_id": backup_path.name,
        "changed": changed,
        "path": str(path),
        "restored_from": str(backup_path),
        "current_backup_path": current_backup_path,
        "active_preset_id": _active_preset_id(restored_policy),
        "policy": _policy_dict(restored_policy),
    }


def _load_policy(path: Path):
    _ensure_policy_engine_importable()
    from policy_engine import load_policy_text
    from policy_engine.defaults import DEFAULT_POLICY_TEXT

    return load_policy_text(path.read_text() if path.exists() else DEFAULT_POLICY_TEXT)


def _current_policy_text(path: Path) -> str:
    _ensure_policy_engine_importable()
    from policy_engine.defaults import DEFAULT_POLICY_TEXT

    return path.read_text() if path.exists() else DEFAULT_POLICY_TEXT


def _preset_summary(preset) -> dict:
    from policy_engine import load_policy_text

    policy = load_policy_text(preset.text)
    return {
        "preset_id": preset.id,
        "label": preset.label,
        "description": preset.description,
        **_policy_summary(policy),
    }


def _backup_summary(path: Path) -> dict:
    item = {
        "backup_id": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "modified_at": _mtime_iso(path),
    }
    try:
        policy = _load_policy(path)
        return {
            **item,
            "status": "ok",
            "active_preset_id": _active_preset_id(policy),
            "summary": _policy_summary(policy),
        }
    except Exception as exc:
        return {
            **item,
            "status": "error",
            "error": _redact_text(str(exc)),
            "active_preset_id": "unknown",
            "summary": {"rules": 0, "enabled_rules": 0},
        }


def _policy_summary(policy) -> dict:
    return {
        "default_action": policy.default_action,
        "rules": len(policy.rules),
        "enabled_rules": sum(1 for rule in policy.rules if rule.enabled),
        "actions": _action_counts(policy),
    }


def _action_counts(policy) -> dict:
    counts = {"allow": 0, "deny": 0, "redact": 0, "require_approval": 0}
    for rule in policy.rules:
        if rule.enabled and rule.action in counts:
            counts[rule.action] += 1
    return counts


def _policy_dict(policy) -> dict:
    return {
        "default_action": policy.default_action,
        "rules": [_redact_value(asdict(rule)) for rule in policy.rules],
    }


def _active_preset_id(policy) -> str:
    from policy_engine.presets import list_policy_presets

    for preset in list_policy_presets():
        if policy == _load_policy_text(preset.text):
            return preset.id
    return "custom"


def _load_policy_text(text: str):
    from policy_engine import load_policy_text

    return load_policy_text(text)


def _policy_backup_files(path: Path) -> list[Path]:
    if not path.parent.exists():
        return []
    prefix = path.name + ".spectrona.bak"
    backups_found = [candidate for candidate in path.parent.glob(prefix + "*") if candidate.is_file()]
    return sorted(backups_found, key=lambda item: (item.stat().st_mtime, item.name), reverse=True)


def _backup_by_id(policy_path: Path, backup_id: str) -> Optional[Path]:
    if "/" in backup_id or "\\" in backup_id:
        return None
    for backup in _policy_backup_files(policy_path):
        if backup.name == backup_id:
            return backup
    return None


def _next_backup_path(path: Path) -> Path:
    first = path.with_name(path.name + ".spectrona.bak")
    if not first.exists():
        return first
    for index in range(1, 1000):
        candidate = path.with_name(path.name + f".spectrona.bak.{index}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("could not allocate policy backup path")


def _normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return ""


def _redact_value(value):
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {_redact_text(str(key)): _redact_value(item) for key, item in value.items()}
    return value


def _redact_text(value: str) -> str:
    text = value
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED_SECRET]", text)
    return text


def _chmod_user_only(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _ensure_policy_engine_importable() -> None:
    root = Path(__file__).resolve().parents[4]
    src = root / "policy-engine" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
