import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .config_file import read_config, spectrona_home


def _runtime_python_path() -> str:
    root = Path(__file__).resolve().parents[4]
    paths = [
        root / "spectrona-cli" / "src",
        root / "spectrona-detection" / "src",
        root / "spectrona-gateway" / "src",
        root / "policy-engine" / "src",
        root / "mcp-inspector" / "src",
        root / "runtime-guard" / "src",
    ]
    return os.pathsep.join(str(path) for path in paths)


def _gateway_settings() -> tuple:
    cfg = read_config()
    gateway = cfg.get("gateway", {})
    host = os.getenv("SPECTRONA_HOST", gateway.get("host", "127.0.0.1"))
    port = os.getenv("SPECTRONA_PORT", gateway.get("port", "8787"))
    mock_mode = os.getenv("SPECTRONA_MOCK_MODE", gateway.get("mock_mode", "true"))
    return host, port, mock_mode


def _validate_host(host: str) -> str:
    normalized = (host or "").strip()
    if normalized in {"0.0.0.0", "::", "[::]"}:
        raise ValueError("Spectrona gateway refuses to bind all interfaces; use 127.0.0.1 or localhost.")
    return normalized or "127.0.0.1"


def _pid_path() -> Path:
    return spectrona_home() / "gateway.pid"


def _log_path() -> Path:
    return spectrona_home() / "logs" / "gateway.log"


def _read_pid() -> int:
    try:
        return int(_pid_path().read_text().strip())
    except Exception:
        return 0


def _is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _gateway_command(host: str, port: str) -> list:
    return [
        sys.executable, "-m", "uvicorn",
        "spectrona_gateway.app:app",
        "--host", host,
        "--port", port,
    ]


def _gateway_env(src: str, mock_mode: str) -> dict:
    return {**os.environ, "PYTHONPATH": src, "SPECTRONA_MOCK_MODE": mock_mode}


def start(background: bool = False) -> int:
    python_path = _runtime_python_path()
    host, port, mock_mode = _gateway_settings()
    try:
        host = _validate_host(host)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    pid = _read_pid()
    if background and _is_running(pid):
        print(f"Spectrona gateway already running (pid={pid})")
        return 0

    print(f"Starting Spectrona gateway on http://{host}:{port} ...")
    print(f"  SPECTRONA_MOCK_MODE={mock_mode}  (set to false to enable real forwarding)")

    if background:
        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _pid_path().parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "ab") as log_file:
            proc = subprocess.Popen(
                _gateway_command(host, port),
                env=_gateway_env(python_path, mock_mode),
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )
        _pid_path().write_text(str(proc.pid))
        print(f"  pid: {proc.pid}")
        print(f"  log: {log_path}")
        return 0

    print("  Ctrl-C to stop\n")
    return subprocess.run(
        _gateway_command(host, port),
        env=_gateway_env(python_path, mock_mode),
    ).returncode


def stop() -> int:
    pid_path = _pid_path()
    pid = _read_pid()
    if not _is_running(pid):
        if pid_path.exists():
            pid_path.unlink()
        print("Spectrona gateway is not running.")
        return 0

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 5
    while time.time() < deadline:
        if not _is_running(pid):
            break
        time.sleep(0.2)

    if _is_running(pid):
        print(f"Gateway did not stop after SIGTERM (pid={pid})", file=sys.stderr)
        return 1

    if pid_path.exists():
        pid_path.unlink()
    print(f"Stopped Spectrona gateway (pid={pid})")
    return 0


def restart(background: bool = True) -> int:
    stopped = stop()
    if stopped != 0:
        return stopped
    return start(background=background)


def health() -> None:
    host, port, _ = _gateway_settings()
    try:
        import httpx
        r = httpx.get(f"http://{host}:{port}/health", timeout=3)
        print(r.json())
    except Exception as e:
        print(f"Gateway not reachable: {e}", file=sys.stderr)
        sys.exit(1)
