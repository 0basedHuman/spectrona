import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .commands.config_file import config_path, read_config, spectrona_home


SERVICE_NAME = "spectrona"
SUPPORTED_PROVIDERS = ("openai", "anthropic", "local")
_ACCOUNTS = {
    "openai": "provider:openai:api_key",
    "anthropic": "provider:anthropic:api_key",
    "local": "provider:local:api_key",
}
_CONFIG_SECRET_KEYS = {
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "local": "local_api_key",
}


@dataclass(frozen=True)
class SecretStatus:
    provider: str
    backend: str
    configured: bool

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "backend": self.backend,
            "configured": self.configured,
        }


@dataclass(frozen=True)
class MigrationResult:
    status: str
    backend: str
    config_path: str
    backup_path: str
    migrated_providers: list[str]
    scrubbed: bool

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "backend": self.backend,
            "config_path": self.config_path,
            "backup_path": self.backup_path,
            "migrated_providers": self.migrated_providers,
            "scrubbed": self.scrubbed,
        }


def normalize_provider(provider: str) -> str:
    value = provider.strip().lower().replace("_api_key", "")
    if value not in SUPPORTED_PROVIDERS:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        raise ValueError(f"unsupported secret provider: {provider}. Supported providers: {supported}")
    return value


def current_backend() -> str:
    requested = os.getenv("SPECTRONA_SECRETS_BACKEND", "").strip().lower()
    if requested:
        if requested not in {"keychain", "file"}:
            raise ValueError("SPECTRONA_SECRETS_BACKEND must be keychain or file")
        return requested
    return "keychain" if platform.system() == "Darwin" else "file"


def set_provider_secret(provider: str, value: str, backend: Optional[str] = None) -> None:
    provider = normalize_provider(provider)
    if value == "":
        raise ValueError("secret value cannot be empty")
    selected = backend or current_backend()
    _backend(selected).set(provider, value)


def get_provider_secret(provider: str, backend: Optional[str] = None) -> str:
    provider = normalize_provider(provider)
    selected = backend or current_backend()
    return _backend(selected).get(provider)


def delete_provider_secret(provider: str, backend: Optional[str] = None) -> bool:
    provider = normalize_provider(provider)
    selected = backend or current_backend()
    return _backend(selected).delete(provider)


def provider_secret_status(provider: str, backend: Optional[str] = None) -> SecretStatus:
    provider = normalize_provider(provider)
    selected = backend or current_backend()
    return SecretStatus(
        provider=provider,
        backend=selected,
        configured=_backend(selected).exists(provider),
    )


def provider_secret_statuses(backend: Optional[str] = None) -> list[SecretStatus]:
    selected = backend or current_backend()
    return [provider_secret_status(provider, backend=selected) for provider in SUPPORTED_PROVIDERS]


def statuses_to_json(statuses: list[SecretStatus]) -> str:
    return json.dumps([status.to_dict() for status in statuses], indent=2)


def migration_to_json(result: MigrationResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def prompt_secret(provider: str) -> str:
    return getpass.getpass(f"{normalize_provider(provider)} API key: ")


def migrate_config_secrets(path: Optional[Path] = None, backend: Optional[str] = None) -> MigrationResult:
    selected = backend or current_backend()
    target = (path or config_path()).expanduser()
    if not target.exists():
        raise FileNotFoundError(f"config file not found: {target}")

    cfg = read_config(target)
    providers = cfg.get("providers", {})
    candidates = [
        (provider, key, providers.get(key, ""))
        for provider, key in _CONFIG_SECRET_KEYS.items()
        if providers.get(key, "")
    ]
    if not candidates:
        return MigrationResult(
            status="no_changes",
            backend=selected,
            config_path=str(target),
            backup_path="",
            migrated_providers=[],
            scrubbed=False,
        )

    original_text = target.read_text()
    backup = _write_config_backup(target)
    for provider, _key, value in candidates:
        set_provider_secret(provider, value, backend=selected)

    scrubbed_text = _scrub_config_provider_keys(original_text, {key for _provider, key, _value in candidates})
    target.write_text(scrubbed_text)
    try:
        target.chmod(0o600)
    except OSError:
        pass

    return MigrationResult(
        status="migrated",
        backend=selected,
        config_path=str(target),
        backup_path=str(backup),
        migrated_providers=[provider for provider, _key, _value in candidates],
        scrubbed=True,
    )


def _backend(name: str):
    if name == "keychain":
        return _KeychainBackend()
    if name == "file":
        return _FileBackend()
    raise ValueError("secret backend must be keychain or file")


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


def _scrub_config_provider_keys(text: str, keys: set[str]) -> str:
    lines = text.splitlines(keepends=True)
    current_section = ""
    scrubbed = []
    for raw_line in lines:
        body = raw_line[:-1] if raw_line.endswith("\n") else raw_line
        newline = "\n" if raw_line.endswith("\n") else ""
        without_comment = body.split("#", 1)[0].rstrip()

        if without_comment and not without_comment.startswith(" ") and without_comment.endswith(":"):
            current_section = without_comment[:-1].strip()
        elif without_comment and not body.startswith(" "):
            current_section = ""

        if current_section == "providers" and without_comment.startswith("  ") and ":" in without_comment:
            key = without_comment.strip().split(":", 1)[0].strip()
            if key in keys:
                comment = ""
                if "#" in body:
                    comment = body[body.index("#"):].rstrip()
                suffix = f" {comment}" if comment else ""
                scrubbed.append(f"  {key}: \"\"{suffix}{newline}")
                continue

        scrubbed.append(raw_line)

    return "".join(scrubbed)


class _KeychainBackend:
    def set(self, provider: str, value: str) -> None:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-a",
                _ACCOUNTS[provider],
                "-s",
                SERVICE_NAME,
                "-w",
                value,
                "-U",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(_security_error(result.stderr))

    def get(self, provider: str) -> str:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                _ACCOUNTS[provider],
                "-s",
                SERVICE_NAME,
                "-w",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.rstrip("\n")

    def exists(self, provider: str) -> bool:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                _ACCOUNTS[provider],
                "-s",
                SERVICE_NAME,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return result.returncode == 0

    def delete(self, provider: str) -> bool:
        result = subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-a",
                _ACCOUNTS[provider],
                "-s",
                SERVICE_NAME,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return result.returncode == 0


class _FileBackend:
    def set(self, provider: str, value: str) -> None:
        data = self._read()
        data[provider] = value
        self._write(data)

    def get(self, provider: str) -> str:
        return self._read().get(provider, "")

    def exists(self, provider: str) -> bool:
        return provider in self._read()

    def delete(self, provider: str) -> bool:
        data = self._read()
        existed = provider in data
        data.pop(provider, None)
        self._write(data)
        return existed

    def _path(self) -> Path:
        override = os.getenv("SPECTRONA_SECRETS_FILE")
        if override:
            return Path(override).expanduser()
        return spectrona_home() / "secrets.json"

    def _read(self) -> dict:
        path = self._path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, data: dict) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _security_error(stderr: str) -> str:
    detail = stderr.strip()
    if not detail:
        return "macOS Keychain command failed"
    return detail.splitlines()[-1]


def command(argv: list[str]) -> int:
    try:
        return _command(argv)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def _command(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="spectrona secrets")
    parser.add_argument("--backend", choices=("keychain", "file"), help="Override secret backend")
    sub = parser.add_subparsers(dest="secrets_cmd")

    set_p = sub.add_parser("set", help="Store a provider API key")
    set_p.add_argument("provider", choices=SUPPORTED_PROVIDERS)
    set_p.add_argument("--value", help="Secret value for scripted setup")
    set_p.add_argument("--stdin", action="store_true", help="Read secret value from stdin")

    get_p = sub.add_parser("get", help="Print a stored provider API key")
    get_p.add_argument("provider", choices=SUPPORTED_PROVIDERS)

    status_p = sub.add_parser("status", help="Show stored provider API key status")
    status_p.add_argument("provider", nargs="?", choices=SUPPORTED_PROVIDERS)
    status_p.add_argument("--json", action="store_true", help="Output JSON status")

    delete_p = sub.add_parser("delete", help="Delete a stored provider API key")
    delete_p.add_argument("provider", choices=SUPPORTED_PROVIDERS)

    migrate_p = sub.add_parser("migrate-config", help="Move plaintext provider keys from config.yaml into the secret store")
    migrate_p.add_argument("--path", help="Config file path (default: ~/.spectrona/config.yaml)")
    migrate_p.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args(argv)
    backend = args.backend

    if args.secrets_cmd == "set":
        if args.stdin:
            value = sys.stdin.read().strip()
        elif args.value is not None:
            value = args.value
        else:
            value = prompt_secret(args.provider)
        set_provider_secret(args.provider, value, backend=backend)
        print(f"Stored secret for {normalize_provider(args.provider)} using {backend or current_backend()} backend")
        return 0

    if args.secrets_cmd == "get":
        value = get_provider_secret(args.provider, backend=backend)
        if not value:
            print(f"No secret stored for {normalize_provider(args.provider)}", file=sys.stderr)
            return 1
        print(value)
        return 0

    if args.secrets_cmd == "status":
        statuses = (
            [provider_secret_status(args.provider, backend=backend)]
            if args.provider
            else provider_secret_statuses(backend=backend)
        )
        if args.json:
            print(statuses_to_json(statuses))
            return 0
        print("Spectrona secrets status")
        print("─" * 40)
        for item in statuses:
            state = "configured" if item.configured else "missing"
            print(f"  {item.provider:<10}: {state} ({item.backend})")
        return 0

    if args.secrets_cmd == "delete":
        deleted = delete_provider_secret(args.provider, backend=backend)
        state = "Deleted" if deleted else "No stored secret for"
        print(f"{state} {normalize_provider(args.provider)}")
        return 0

    if args.secrets_cmd == "migrate-config":
        result = migrate_config_secrets(
            path=Path(args.path).expanduser() if args.path else None,
            backend=backend,
        )
        if args.json:
            print(migration_to_json(result))
            return 0
        if result.status == "no_changes":
            print(f"No plaintext provider keys found in {result.config_path}")
            return 0
        print(f"Migrated {len(result.migrated_providers)} provider secret(s) using {result.backend} backend")
        print(f"  config : {result.config_path}")
        print(f"  backup : {result.backup_path}")
        print(f"  scrubbed plaintext keys: {', '.join(result.migrated_providers)}")
        return 0

    parser.print_help()
    return 0
