from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from policy_engine import load_policy_text
from policy_engine.defaults import DEFAULT_POLICY_TEXT
from policy_engine.presets import PolicyPreset, get_policy_preset, list_policy_presets

from .. import config
from ..dlp import redact_text


router = APIRouter()


@router.get("")
async def current_policy() -> dict:
    return _current_policy_response()


@router.get("/presets")
async def policy_presets() -> dict:
    current = _load_current_policy()
    return {
        "status": "ok",
        "active_preset_id": _active_preset_id(current["policy"]),
        "presets": [_preset_summary(preset) for preset in list_policy_presets()],
    }


@router.get("/presets/{preset_id}")
async def policy_preset(preset_id: str) -> dict:
    try:
        preset = get_policy_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "status": "ok",
        **_preset_summary(preset),
        "policy": _policy_dict(load_policy_text(preset.text)),
    }


@router.get("/backups")
async def policy_backups() -> dict:
    backups = [_backup_summary(path) for path in _policy_backup_files(config.POLICY_PATH.expanduser())]
    return {
        "status": "ok",
        "path": str(config.POLICY_PATH.expanduser()),
        "backups": backups,
        "summary": {
            "total": len(backups),
            "restorable": sum(1 for item in backups if item.get("status") == "ok"),
        },
    }


@router.post("/backups/{backup_id}/restore")
async def restore_policy_backup(backup_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    policy_path = config.POLICY_PATH.expanduser()
    backup_path = _backup_by_id(policy_path, backup_id)
    if backup_path is None:
        raise HTTPException(status_code=404, detail=f"Unknown policy backup: {backup_id}")

    try:
        restored_text = backup_path.read_text()
        restored_policy = load_policy_text(restored_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"policy backup could not be loaded: {redact_text(str(exc))}") from exc

    current_text = _current_policy_text()
    changed = _normalized(current_text) != _normalized(restored_text)
    current_backup_path = ""
    if changed:
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        if policy_path.exists():
            current_backup = _next_backup_path(policy_path)
            current_backup.write_text(policy_path.read_text())
            _chmod_user_only(current_backup)
            current_backup_path = str(current_backup)
        policy_path.write_text(restored_text)
        _chmod_user_only(policy_path)

    return {
        "status": "ok",
        "action": "restore_backup",
        "action_time": datetime.now(timezone.utc).isoformat(),
        "backup_id": backup_id,
        "changed": changed,
        "path": str(policy_path),
        "restored_from": str(backup_path),
        "current_backup_path": current_backup_path,
        "policy": _policy_dict(restored_policy),
        "active_preset_id": _active_preset_id(restored_policy),
    }


@router.post("/presets/{preset_id}/apply")
async def apply_policy_preset(preset_id: str, body: Optional[dict] = Body(default=None)) -> dict:
    _require_confirm(body)
    try:
        preset = get_policy_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    policy_path = config.POLICY_PATH.expanduser()
    current_text = _current_policy_text()
    changed = _normalized(current_text) != _normalized(preset.text)
    backup_path = ""
    if changed:
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        if policy_path.exists():
            backup = _next_backup_path(policy_path)
            backup.write_text(policy_path.read_text())
            _chmod_user_only(backup)
            backup_path = str(backup)
        policy_path.write_text(preset.text)
        _chmod_user_only(policy_path)

    return {
        "status": "ok",
        "action": "apply_preset",
        "action_time": datetime.now(timezone.utc).isoformat(),
        "preset_id": preset.id,
        "changed": changed,
        "path": str(policy_path),
        "backup_path": backup_path,
        "policy": _policy_dict(load_policy_text(preset.text)),
        "active_preset_id": preset.id,
    }


def _current_policy_response() -> dict:
    base = {
        "path": str(config.POLICY_PATH.expanduser()),
        "exists": config.POLICY_PATH.expanduser().exists(),
        "dry_run": config.POLICY_DRY_RUN,
        "presets": [_preset_summary(preset) for preset in list_policy_presets()],
    }
    try:
        loaded = _load_current_policy()
    except Exception as exc:
        return {
            "status": "error",
            **base,
            "error": redact_text(str(exc)),
            "active_preset_id": "unknown",
            "policy": {"default_action": "deny", "rules": []},
            "summary": {"rules": 0, "enabled_rules": 0},
        }
    policy = loaded["policy"]
    return {
        "status": "ok",
        **base,
        "active_preset_id": _active_preset_id(policy),
        "policy": _policy_dict(policy),
        "summary": _policy_summary(policy),
    }


def _load_current_policy() -> dict:
    text = _current_policy_text()
    return {"text": text, "policy": load_policy_text(text)}


def _current_policy_text() -> str:
    policy_path = config.POLICY_PATH.expanduser()
    if not policy_path.exists():
        return DEFAULT_POLICY_TEXT
    return policy_path.read_text()


def _preset_summary(preset: PolicyPreset) -> dict:
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
        policy = load_policy_text(path.read_text())
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
            "error": redact_text(str(exc)),
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
    for preset in list_policy_presets():
        if policy == load_policy_text(preset.text):
            return preset.id
    return "custom"


def _policy_backup_files(path: Path) -> list[Path]:
    if not path.parent.exists():
        return []
    prefix = path.name + ".spectrona.bak"
    backups = [candidate for candidate in path.parent.glob(prefix + "*") if candidate.is_file()]
    return sorted(backups, key=lambda item: (item.stat().st_mtime, item.name), reverse=True)


def _backup_by_id(policy_path: Path, backup_id: str) -> Optional[Path]:
    if "/" in backup_id or "\\" in backup_id:
        return None
    for backup in _policy_backup_files(policy_path):
        if backup.name == backup_id:
            return backup
    return None


def _redact_value(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {redact_text(str(key)): _redact_value(item) for key, item in value.items()}
    return value


def _normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _require_confirm(body: Optional[dict]) -> None:
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="confirm=true is required for policy changes")


def _next_backup_path(path: Path) -> Path:
    first = path.with_name(path.name + ".spectrona.bak")
    if not first.exists():
        return first
    for index in range(1, 1000):
        candidate = path.with_name(path.name + f".spectrona.bak.{index}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("could not allocate policy backup path")


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return ""


def _chmod_user_only(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass
