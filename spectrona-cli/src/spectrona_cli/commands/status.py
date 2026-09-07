from pathlib import Path

from .config_file import config_path, read_config, spectrona_home
from ..secrets import provider_secret_status


def _configured_path(value: str, fallback: Path) -> Path:
    if value:
        return Path(value).expanduser()
    return fallback


def _stored(provider: str) -> bool:
    try:
        return provider_secret_status(provider).configured
    except Exception:
        return False


def _provider_key_state(config_value: str, provider: str) -> str:
    if config_value:
        return "configured"
    if _stored(provider):
        return "stored"
    return "missing"


def _local_key_state(value: str) -> str:
    if value:
        return "configured optional"
    if _stored("local"):
        return "stored optional"
    return "not required"


def run() -> None:
    cfg = read_config()
    gateway = cfg.get("gateway", {})
    paths = cfg.get("paths", {})
    providers = cfg.get("providers", {})
    host = gateway.get("host", "127.0.0.1")
    port = gateway.get("port", "8787")
    mock_mode = gateway.get("mock_mode", "true")
    policy_dry_run = gateway.get("policy_dry_run", "false")
    home = spectrona_home()
    log_dir = _configured_path(paths.get("log_dir", ""), home / "logs")
    db_path = _configured_path(paths.get("db_path", ""), home / "memory.db")
    policy_file = _configured_path(paths.get("policy_path", ""), home / "policy.yaml")

    print("Spectrona status")
    print("─" * 40)

    path = config_path()
    if path.exists():
        print(f"  config      : {path}")
    else:
        print("  config      : missing  (run: spectrona init)")

    print(f"  mode        : {'MOCK' if mock_mode.lower() == 'true' else 'PASSTHROUGH'}")
    print(f"  policy dry-run: {'ON' if policy_dry_run.lower() == 'true' else 'off'}")
    print(f"  logs        : {log_dir}")
    print(f"  memory db   : {db_path}")
    if policy_file.exists():
        print(f"  policy      : {policy_file}")
    else:
        print(f"  policy      : missing  (run: spectrona init)")

    # Gateway
    try:
        import httpx
        r = httpx.get(f"http://{host}:{port}/health", timeout=2)
        if r.status_code == 200:
            print(f"  gateway     : RUNNING  (http://{host}:{port})")
        else:
            print(f"  gateway     : ERROR ({r.status_code})")
    except Exception:
        print("  gateway     : STOPPED  (run: spectrona gateway start)")

    # mcp-inspector
    inspector = Path(__file__).resolve().parents[4] / "mcp-inspector" / "bin" / "mcp-inspector"
    if inspector.exists():
        print(f"  mcp-inspector: found at {inspector}")
    else:
        print("  mcp-inspector: not found")

    print("  providers   :")
    print(
        "    openai    : "
        f"{providers.get('openai_base_url', 'https://api.openai.com/v1')} "
        f"({ _provider_key_state(providers.get('openai_api_key', ''), 'openai') } key)"
    )
    print(
        "    anthropic : "
        f"{providers.get('anthropic_base_url', 'https://api.anthropic.com/v1')} "
        f"({ _provider_key_state(providers.get('anthropic_api_key', ''), 'anthropic') } key)"
    )
    print(
        "    local     : "
        f"{providers.get('local_base_url', 'http://127.0.0.1:11434/v1')} "
        f"({providers.get('local_provider', 'openai-compatible')}, "
        f"{_local_key_state(providers.get('local_api_key', ''))} key, "
        f"fallbacks {providers.get('local_fallbacks', '') or 'none'})"
    )

    # Audit log
    audit_log = log_dir / "audit.jsonl"
    if audit_log.exists():
        lines = sum(1 for _ in open(audit_log))
        print(f"  audit log   : {audit_log} ({lines} events)")
    else:
        print("  audit log   : no events yet")

    print()
