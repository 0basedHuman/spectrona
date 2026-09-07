import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from .config_file import spectrona_home


LABEL = "com.spectrona.gateway"


def _launch_agents_dir() -> Path:
    override = os.getenv("SPECTRONA_LAUNCH_AGENTS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return _launch_agents_dir() / f"{LABEL}.plist"


def _cli_src() -> Path:
    return Path(__file__).resolve().parents[1]


def plist_text() -> str:
    home = spectrona_home()
    log_dir = home / "logs"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{escape(sys.executable)}</string>
    <string>-m</string>
    <string>spectrona_cli</string>
    <string>start</string>
    <string>--foreground</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key>
    <string>{escape(str(_cli_src()))}</string>
    <key>SPECTRONA_HOME</key>
    <string>{escape(str(home))}</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{escape(str(log_dir / "launchagent.out.log"))}</string>
  <key>StandardErrorPath</key>
  <string>{escape(str(log_dir / "launchagent.err.log"))}</string>
</dict>
</plist>
"""


def print_plist() -> int:
    print(plist_text(), end="")
    return 0


def install(path: Optional[str] = None) -> int:
    target = Path(path).expanduser() if path else plist_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    (spectrona_home() / "logs").mkdir(parents=True, exist_ok=True)
    target.write_text(plist_text())
    print(f"Wrote LaunchAgent plist: {target}")
    print(f"Load with:   launchctl load {target}")
    print(f"Unload with: launchctl unload {target}")
    return 0


def _launchctl(action: str, path: Optional[str] = None, dry_run: bool = False) -> int:
    target = Path(path).expanduser() if path else plist_path()
    cmd = ["launchctl", action, str(target)]
    if dry_run:
        print(" ".join(cmd))
        return 0
    if not target.exists():
        print(f"LaunchAgent plist not found: {target}", file=sys.stderr)
        return 1
    return subprocess.run(cmd).returncode


def load(path: Optional[str] = None, dry_run: bool = False) -> int:
    return _launchctl("load", path, dry_run)


def unload(path: Optional[str] = None, dry_run: bool = False) -> int:
    return _launchctl("unload", path, dry_run)


def uninstall(path: Optional[str] = None) -> int:
    target = Path(path).expanduser() if path else plist_path()
    if target.exists():
        target.unlink()
        print(f"Removed LaunchAgent plist: {target}")
    else:
        print(f"LaunchAgent plist not found: {target}")
    return 0
