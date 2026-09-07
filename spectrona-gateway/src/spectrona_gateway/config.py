import os
import sys
from pathlib import Path
from typing import Dict


def _spectrona_home() -> Path:
    return Path(os.getenv("SPECTRONA_HOME", str(Path.home() / ".spectrona"))).expanduser()


def _config_path() -> Path:
    override = os.getenv("SPECTRONA_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return _spectrona_home() / "config.yaml"


def _read_config() -> Dict[str, Dict[str, str]]:
    path = _config_path()
    if not path.exists():
        return {}

    config: Dict[str, Dict[str, str]] = {}
    current = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            config[current] = {}
            continue
        if current and line.startswith("  ") and ":" in line:
            key, value = line.strip().split(":", 1)
            config[current][key.strip()] = value.strip().strip('"').strip("'")
    return config


_CONFIG = _read_config()
_GATEWAY = _CONFIG.get("gateway", {})
_PATHS = _CONFIG.get("paths", {})
_PROVIDERS = _CONFIG.get("providers", {})


def _value(env_name: str, section: Dict[str, str], key: str, default: str) -> str:
    value = os.getenv(env_name)
    if value is not None:
        return value
    return section.get(key, default)


def _stored_provider_secret(provider: str) -> str:
    try:
        from spectrona_cli.secrets import get_provider_secret
    except ImportError:
        repo_root = Path(__file__).resolve().parents[3]
        cli_src = repo_root / "spectrona-cli" / "src"
        if cli_src.exists() and str(cli_src) not in sys.path:
            sys.path.insert(0, str(cli_src))
        try:
            from spectrona_cli.secrets import get_provider_secret
        except Exception:
            return ""

    try:
        return get_provider_secret(provider)
    except Exception:
        return ""


def _provider_api_key(
    spectrona_env_name: str,
    common_env_name: str,
    provider: str,
    config_key: str,
) -> str:
    value = os.getenv(spectrona_env_name)
    if value is not None:
        return value
    value = os.getenv(common_env_name)
    if value is not None:
        return value
    stored = _stored_provider_secret(provider)
    if stored:
        return stored
    return _PROVIDERS.get(config_key, "")


def _local_provider_api_key() -> str:
    value = os.getenv("SPECTRONA_LOCAL_API_KEY")
    if value is not None:
        return value
    stored = _stored_provider_secret("local")
    if stored:
        return stored
    return _PROVIDERS.get("local_api_key", "")


MOCK_MODE: bool = _value("SPECTRONA_MOCK_MODE", _GATEWAY, "mock_mode", "true").lower() == "true"
POLICY_DRY_RUN: bool = _value("SPECTRONA_POLICY_DRY_RUN", _GATEWAY, "policy_dry_run", "false").lower() == "true"
GATEWAY_AUTH_TOKEN: str = _value("SPECTRONA_GATEWAY_AUTH_TOKEN", _GATEWAY, "auth_token", "")
MEMORY_CAPTURE: bool = _value("SPECTRONA_MEMORY_CAPTURE", _GATEWAY, "memory_capture", "true").lower() == "true"
MEMORY_INJECTION: bool = _value("SPECTRONA_MEMORY_INJECTION", _GATEWAY, "memory_injection", "false").lower() == "true"
MEMORY_MAX_ATTACHMENTS: int = int(_value("SPECTRONA_MEMORY_MAX_ATTACHMENTS", _GATEWAY, "memory_max_attachments", "5"))
MEMORY_STALE_AFTER_DAYS: int = int(_value("SPECTRONA_MEMORY_STALE_AFTER_DAYS", _GATEWAY, "memory_stale_after_days", "30"))
MEMORY_RAW_STORAGE: str = _value("SPECTRONA_MEMORY_RAW_STORAGE", _GATEWAY, "memory_raw_storage", "redacted").lower()
MEMORY_ALLOW_PLAINTEXT: bool = _value("SPECTRONA_MEMORY_ALLOW_PLAINTEXT", _GATEWAY, "memory_plaintext_allowed", "false").lower() == "true"
PORT: int = int(_value("SPECTRONA_PORT", _GATEWAY, "port", "8787"))
HOST: str = _value("SPECTRONA_HOST", _GATEWAY, "host", "127.0.0.1")
if HOST.strip() in {"0.0.0.0", "::", "[::]"}:
    raise RuntimeError("Spectrona gateway refuses to bind all interfaces; use 127.0.0.1 or localhost.")
LOG_DIR: Path = Path(_value("SPECTRONA_LOG_DIR", _PATHS, "log_dir", str(_spectrona_home() / "logs"))).expanduser()
DB_PATH: Path = Path(_value("SPECTRONA_DB_PATH", _PATHS, "db_path", str(_spectrona_home() / "memory.db"))).expanduser()
POLICY_PATH: Path = Path(_value("SPECTRONA_POLICY_PATH", _PATHS, "policy_path", str(_spectrona_home() / "policy.yaml"))).expanduser()
MEMORY_ENCRYPTION_KEY_PATH: Path = Path(_value("SPECTRONA_MEMORY_ENCRYPTION_KEY_PATH", _PATHS, "memory_encryption_key_path", str(_spectrona_home() / "memory.key"))).expanduser()
MCP_CONFIG_PATH: str = _value("SPECTRONA_MCP_CONFIG_PATH", _PATHS, "mcp_config_path", "")
MCP_APP_HOME: str = _value("SPECTRONA_MCP_APP_HOME", _PATHS, "mcp_app_home", "")
_REPO_ROOT_VALUE = _value("SPECTRONA_REPO_ROOT", _PATHS, "repo_root", "")
REPO_ROOT: Path = Path(_REPO_ROOT_VALUE).expanduser() if _REPO_ROOT_VALUE else Path(os.getcwd())

OPENAI_BASE_URL: str = _value("SPECTRONA_OPENAI_BASE_URL", _PROVIDERS, "openai_base_url", "https://api.openai.com/v1").rstrip("/")
OPENAI_HEALTH_PATH: str = _value("SPECTRONA_OPENAI_HEALTH_PATH", _PROVIDERS, "openai_health_path", "/models")
OPENAI_API_KEY: str = _provider_api_key("SPECTRONA_OPENAI_API_KEY", "OPENAI_API_KEY", "openai", "openai_api_key")

ANTHROPIC_BASE_URL: str = _value("SPECTRONA_ANTHROPIC_BASE_URL", _PROVIDERS, "anthropic_base_url", "https://api.anthropic.com/v1").rstrip("/")
ANTHROPIC_HEALTH_PATH: str = _value("SPECTRONA_ANTHROPIC_HEALTH_PATH", _PROVIDERS, "anthropic_health_path", "/models")
ANTHROPIC_API_KEY: str = _provider_api_key(
    "SPECTRONA_ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY",
    "anthropic",
    "anthropic_api_key",
)
ANTHROPIC_VERSION: str = _value("SPECTRONA_ANTHROPIC_VERSION", _PROVIDERS, "anthropic_version", "2023-06-01")

LOCAL_PROVIDER: str = _value("SPECTRONA_LOCAL_PROVIDER", _PROVIDERS, "local_provider", "openai-compatible")
LOCAL_BASE_URL: str = _value("SPECTRONA_LOCAL_BASE_URL", _PROVIDERS, "local_base_url", "http://127.0.0.1:11434/v1").rstrip("/")
LOCAL_HEALTH_PATH: str = _value("SPECTRONA_LOCAL_HEALTH_PATH", _PROVIDERS, "local_health_path", "/models")
LOCAL_FALLBACKS: str = _value("SPECTRONA_LOCAL_FALLBACKS", _PROVIDERS, "local_fallbacks", "")
LOCAL_API_KEY: str = _local_provider_api_key()


def apply_local_provider(provider: str, base_url: str, health_path: str) -> None:
    global LOCAL_PROVIDER, LOCAL_BASE_URL, LOCAL_HEALTH_PATH
    LOCAL_PROVIDER = provider or "openai-compatible"
    LOCAL_BASE_URL = (base_url or "http://127.0.0.1:11434/v1").rstrip("/")
    LOCAL_HEALTH_PATH = health_path or "/models"
