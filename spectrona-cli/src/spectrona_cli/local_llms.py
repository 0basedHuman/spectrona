import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .commands.config_file import config_path, default_config_text, read_config


@dataclass(frozen=True)
class LocalLLMPreset:
    runtime_id: str
    label: str
    adapter: str
    default_base_url: str
    default_health_path: str
    base_url_env: str
    health_path_env: str


@dataclass(frozen=True)
class LocalLLMStatus:
    runtime_id: str
    label: str
    adapter: str
    base_url: str
    health_path: str
    health_url: str
    configured_base_url: str
    configured_provider: str
    selected_config: bool
    fallback_config: bool
    api_key_required: bool
    live_checked: bool
    reachable: bool
    status: str
    status_code: int = 0
    error: str = ""
    recommended_action: str = "configure"
    repair_available: bool = False

    def to_dict(self) -> dict:
        return {
            "runtime_id": self.runtime_id,
            "label": self.label,
            "adapter": self.adapter,
            "base_url": self.base_url,
            "health_path": self.health_path,
            "health_url": self.health_url,
            "configured_base_url": self.configured_base_url,
            "configured_provider": self.configured_provider,
            "selected_config": self.selected_config,
            "fallback_config": self.fallback_config,
            "api_key_required": self.api_key_required,
            "live_checked": self.live_checked,
            "reachable": self.reachable,
            "status": self.status,
            "status_code": self.status_code,
            "error": self.error,
            "recommended_action": self.recommended_action,
            "repair_available": self.repair_available,
        }


@dataclass(frozen=True)
class LocalLLMSelectionResult:
    status: str
    runtime_id: str
    label: str
    adapter: str
    config_path: str
    backup_path: str
    changed: bool
    before_provider: str
    before_base_url: str
    before_health_path: str
    after_provider: str
    after_base_url: str
    after_health_path: str
    restart_required: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "runtime_id": self.runtime_id,
            "label": self.label,
            "adapter": self.adapter,
            "config_path": self.config_path,
            "backup_path": self.backup_path,
            "changed": self.changed,
            "before_provider": self.before_provider,
            "before_base_url": self.before_base_url,
            "before_health_path": self.before_health_path,
            "after_provider": self.after_provider,
            "after_base_url": self.after_base_url,
            "after_health_path": self.after_health_path,
            "restart_required": self.restart_required,
        }


LOCAL_LLM_PRESETS = (
    LocalLLMPreset(
        runtime_id="ollama",
        label="Ollama",
        adapter="openai-compatible",
        default_base_url="http://127.0.0.1:11434/v1",
        default_health_path="/models",
        base_url_env="SPECTRONA_OLLAMA_BASE_URL",
        health_path_env="SPECTRONA_OLLAMA_HEALTH_PATH",
    ),
    LocalLLMPreset(
        runtime_id="lm-studio",
        label="LM Studio",
        adapter="openai-compatible",
        default_base_url="http://127.0.0.1:1234/v1",
        default_health_path="/models",
        base_url_env="SPECTRONA_LM_STUDIO_BASE_URL",
        health_path_env="SPECTRONA_LM_STUDIO_HEALTH_PATH",
    ),
    LocalLLMPreset(
        runtime_id="llama-cpp",
        label="llama.cpp",
        adapter="openai-compatible",
        default_base_url="http://127.0.0.1:8080/v1",
        default_health_path="/models",
        base_url_env="SPECTRONA_LLAMA_CPP_BASE_URL",
        health_path_env="SPECTRONA_LLAMA_CPP_HEALTH_PATH",
    ),
    LocalLLMPreset(
        runtime_id="vllm",
        label="vLLM",
        adapter="openai-compatible",
        default_base_url="http://127.0.0.1:8000/v1",
        default_health_path="/models",
        base_url_env="SPECTRONA_VLLM_BASE_URL",
        health_path_env="SPECTRONA_VLLM_HEALTH_PATH",
    ),
)


def get_local_llm_preset(runtime_id: str) -> LocalLLMPreset:
    normalized = (runtime_id or "").strip().lower()
    for preset in LOCAL_LLM_PRESETS:
        if preset.runtime_id == normalized:
            return preset
    supported = ", ".join(preset.runtime_id for preset in LOCAL_LLM_PRESETS)
    raise ValueError(f"unsupported local LLM runtime id: {runtime_id}. Supported ids: {supported}")


def discover_local_llms(
    configured_base_url: Optional[str] = None,
    configured_provider: Optional[str] = None,
    configured_fallbacks: Optional[str] = None,
    live: bool = False,
    timeout_seconds: float = 0.75,
) -> list[LocalLLMStatus]:
    configured_base, configured_type, fallback_value = _configured_local_provider(
        configured_base_url,
        configured_provider,
        configured_fallbacks,
    )
    fallback_bases = set(local_fallback_base_urls(fallback_value))
    return [
        _status_for_preset(
            preset,
            configured_base_url=configured_base,
            configured_provider=configured_type,
            fallback_base_urls=fallback_bases,
            live=live,
            timeout_seconds=timeout_seconds,
        )
        for preset in LOCAL_LLM_PRESETS
    ]


def local_llm_summary(statuses: list[LocalLLMStatus]) -> dict:
    return {
        "total": len(statuses),
        "configured": sum(1 for item in statuses if item.selected_config),
        "reachable": sum(1 for item in statuses if item.reachable),
        "ok": sum(1 for item in statuses if item.status == "ok"),
        "unreachable": sum(1 for item in statuses if item.status == "unreachable"),
        "fallback": sum(1 for item in statuses if item.fallback_config),
        "live_checked": any(item.live_checked for item in statuses),
    }


def select_local_llm(runtime_id: str, path: Optional[Path] = None) -> LocalLLMSelectionResult:
    preset = get_local_llm_preset(runtime_id)
    target = (path or config_path()).expanduser()
    before = _configured_local_provider_from_file(target)
    after_provider = preset.adapter
    after_base_url = _normalize_url(os.getenv(preset.base_url_env, preset.default_base_url))
    after_health_path = os.getenv(preset.health_path_env, preset.default_health_path)
    changed = (
        not target.exists()
        or before[0] != after_base_url
        or before[1] != after_provider
        or before[2] != after_health_path
    )
    backup = None

    if changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        text = target.read_text() if target.exists() else default_config_text()
        if target.exists():
            backup = _write_config_backup(target)
        updated = _update_simple_config_section(
            text,
            "providers",
            {
                "local_provider": after_provider,
                "local_base_url": after_base_url,
                "local_health_path": after_health_path,
            },
        )
        target.write_text(updated)
        try:
            target.chmod(0o600)
        except OSError:
            pass

    return LocalLLMSelectionResult(
        status="updated" if changed else "unchanged",
        runtime_id=preset.runtime_id,
        label=preset.label,
        adapter=preset.adapter,
        config_path=str(target),
        backup_path=str(backup) if backup else "",
        changed=changed,
        before_provider=before[1],
        before_base_url=before[0],
        before_health_path=before[2],
        after_provider=after_provider,
        after_base_url=after_base_url,
        after_health_path=after_health_path,
    )


def local_config_env_overrides() -> list[str]:
    return [
        name
        for name in ("SPECTRONA_LOCAL_PROVIDER", "SPECTRONA_LOCAL_BASE_URL", "SPECTRONA_LOCAL_HEALTH_PATH")
        if os.getenv(name) is not None
    ]


def local_fallback_base_urls(value: str) -> list[str]:
    bases = []
    for item in parse_local_fallbacks(value):
        if item.startswith("http://") or item.startswith("https://"):
            base_url = _normalize_url(item)
            if not _is_local_base_url(base_url):
                continue
        else:
            try:
                preset = get_local_llm_preset(item)
            except ValueError:
                continue
            base_url = _normalize_url(os.getenv(preset.base_url_env, preset.default_base_url))
        if base_url and base_url not in bases:
            bases.append(base_url)
    return bases


def parse_local_fallbacks(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").replace("\n", ",").split(",")
        if item.strip()
    ]


def statuses_to_json(statuses: list[LocalLLMStatus]) -> str:
    return json.dumps([status.to_dict() for status in statuses], indent=2)


def _status_for_preset(
    preset: LocalLLMPreset,
    configured_base_url: str,
    configured_provider: str,
    fallback_base_urls: set[str],
    live: bool,
    timeout_seconds: float,
) -> LocalLLMStatus:
    base_url = _normalize_url(os.getenv(preset.base_url_env, preset.default_base_url))
    health_path = os.getenv(preset.health_path_env, preset.default_health_path)
    health_url = _join_url(base_url, health_path)
    selected = _normalize_url(configured_base_url) == base_url
    fallback = base_url in fallback_base_urls and not selected

    status = "configured" if selected else "fallback" if fallback else "candidate"
    reachable = False
    status_code = 0
    error = ""

    if live:
        status, reachable, status_code, error = _live_check(health_url, timeout_seconds)

    return LocalLLMStatus(
        runtime_id=preset.runtime_id,
        label=preset.label,
        adapter=preset.adapter,
        base_url=base_url,
        health_path=health_path,
        health_url=health_url,
        configured_base_url=_normalize_url(configured_base_url),
        configured_provider=configured_provider or "openai-compatible",
        selected_config=selected,
        fallback_config=fallback,
        api_key_required=False,
        live_checked=live,
        reachable=reachable,
        status=status,
        status_code=status_code,
        error=_redact_text(error),
        recommended_action="none" if selected else "fallback" if fallback else "configure",
        repair_available=False,
    )


def _configured_local_provider(
    configured_base_url: Optional[str],
    configured_provider: Optional[str],
    configured_fallbacks: Optional[str],
) -> tuple[str, str, str]:
    if configured_base_url:
        return (
            configured_base_url,
            configured_provider or "openai-compatible",
            configured_fallbacks or os.getenv("SPECTRONA_LOCAL_FALLBACKS", ""),
        )
    env_base = os.getenv("SPECTRONA_LOCAL_BASE_URL")
    if env_base:
        return (
            env_base,
            os.getenv("SPECTRONA_LOCAL_PROVIDER", configured_provider or "openai-compatible"),
            configured_fallbacks or os.getenv("SPECTRONA_LOCAL_FALLBACKS", ""),
        )
    cfg = read_config()
    providers = cfg.get("providers", {})
    return (
        providers.get("local_base_url", "http://127.0.0.1:11434/v1"),
        providers.get("local_provider", "openai-compatible"),
        configured_fallbacks
        if configured_fallbacks is not None
        else os.getenv("SPECTRONA_LOCAL_FALLBACKS", providers.get("local_fallbacks", "")),
    )


def _configured_local_provider_from_file(path: Path) -> tuple[str, str, str]:
    cfg = read_config(path) if path.exists() else {}
    providers = cfg.get("providers", {})
    return (
        _normalize_url(providers.get("local_base_url", "http://127.0.0.1:11434/v1")),
        providers.get("local_provider", "openai-compatible"),
        providers.get("local_health_path", "/models"),
    )


def _live_check(url: str, timeout_seconds: float) -> tuple[str, bool, int, str]:
    request = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=max(0.1, float(timeout_seconds))) as response:
            status_code = int(getattr(response, "status", 0) or 0)
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        if status_code in (401, 403):
            return "auth_error", True, status_code, ""
        return "upstream_error", True, status_code, ""
    except Exception as exc:
        return "unreachable", False, 0, str(exc)

    if status_code == 200:
        return "ok", True, status_code, ""
    if status_code in (401, 403):
        return "auth_error", True, status_code, ""
    return "upstream_error", True, status_code, ""


def _normalize_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _is_local_base_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if host.startswith("127."):
        return True
    if host.startswith("10.") or host.startswith("192.168."):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return host.endswith(".local")


def _write_config_backup(path: Path) -> Path:
    backup = _next_backup_path(path)
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    try:
        backup.chmod(0o600)
    except OSError:
        pass
    return backup


def _next_backup_path(path: Path) -> Path:
    first = path.with_name(path.name + ".spectrona.bak")
    if not first.exists():
        return first
    for index in range(1, 1000):
        candidate = path.with_name(path.name + f".spectrona.bak.{index}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate backup path for {path}")


def _update_simple_config_section(text: str, section: str, updates: dict[str, str]) -> str:
    lines = text.splitlines()
    output = []
    in_section = False
    seen_section = False
    seen_keys = set()

    def append_missing() -> None:
        for key, value in updates.items():
            if key not in seen_keys:
                output.append(f"  {key}: {_quote_config_value(value)}")
                seen_keys.add(key)

    for line in lines:
        body = line.split("#", 1)[0].rstrip()
        is_top_level = bool(body) and not line.startswith(" ") and body.endswith(":")
        if is_top_level:
            if in_section:
                append_missing()
            current = body[:-1].strip()
            in_section = current == section
            seen_section = seen_section or in_section

        if in_section and line.startswith("  ") and ":" in line:
            key = line.strip().split(":", 1)[0].strip()
            if key in updates:
                output.append(f"  {key}: {_quote_config_value(updates[key])}")
                seen_keys.add(key)
                continue

        output.append(line)

    if in_section:
        append_missing()
    elif not seen_section:
        if output and output[-1] != "":
            output.append("")
        output.append(f"{section}:")
        append_missing()

    return "\n".join(output).rstrip() + "\n"


def _quote_config_value(value: str) -> str:
    return '""' if value == "" else value


def _redact_text(value: str) -> str:
    text = str(value)
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "~")
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
