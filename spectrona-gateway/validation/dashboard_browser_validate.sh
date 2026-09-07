#!/usr/bin/env bash
# Browser validation - renders the dashboard with Chrome headless and checks the
# post-JS DOM plus screenshot pixels. Skips cleanly when browser tooling is absent.

set -euo pipefail

PASS=0
FAIL=0
SKIP=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATEWAY_SRC="$ROOT/spectrona-gateway/src"
CLI_SRC="$ROOT/spectrona-cli/src"
POLICY_SRC="$ROOT/policy-engine/src"
INSPECTOR_SRC="$ROOT/mcp-inspector/src"
RUNTIME_GUARD_SRC="$ROOT/runtime-guard/src"
DETECTION_SRC="$ROOT/spectrona-detection/src"
RUNTIME_PYTHONPATH="$DETECTION_SRC:$GATEWAY_SRC:$CLI_SRC:$POLICY_SRC:$INSPECTOR_SRC:$RUNTIME_GUARD_SRC"
PORT="${SPECTRONA_BROWSER_VALIDATE_PORT:-19006}"
BASE="http://127.0.0.1:$PORT"
AUTH_TOKEN="dashboard-browser-auth-token"
CHROME="${SPECTRONA_BROWSER_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
TMP_ROOT="/tmp/spectrona_dashboard_browser_$$"
TEST_DB="$TMP_ROOT/events.db"
TEST_HOME="$TMP_ROOT/home"
TEST_LOG_DIR="$TMP_ROOT/logs"
TEST_POLICY="$TMP_ROOT/policy.yaml"
TEST_CONFIG="$TMP_ROOT/config.yaml"
TEST_MCP="$TMP_ROOT/mcp.json"
TEST_SCREENSHOT="$TMP_ROOT/dashboard.png"
TEST_DOM="$TMP_ROOT/dashboard.dom.html"
TEST_PROFILE="$TMP_ROOT/chrome-profile"
GW_PID=""

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
_skip() { echo "  [SKIP] $1"; SKIP=$((SKIP + 1)); }
curl() { command curl -H "Authorization: Bearer $AUTH_TOKEN" "$@"; }

_cleanup() {
  [ -n "$GW_PID" ] && kill "$GW_PID" 2>/dev/null && wait "$GW_PID" 2>/dev/null || true
  if [ "${SPECTRONA_BROWSER_VALIDATE_KEEP_TMP:-false}" = "true" ]; then
    echo "  [INFO] kept browser validation artifacts: $TMP_ROOT"
  else
    rm -rf "$TMP_ROOT"
  fi
}
trap _cleanup EXIT

echo ""
echo "=== Dashboard Browser Validation ==="
echo ""

if [ ! -x "$CHROME" ]; then
  _skip "Chrome headless binary not found: $CHROME"
  echo ""
  echo "=== Dashboard Browser Result: $PASS passed, $FAIL failed, $SKIP skipped ==="
  exit 0
fi

mkdir -p "$TMP_ROOT" "$TEST_HOME" "$TEST_LOG_DIR" "$TEST_PROFILE"

cat > "$TEST_POLICY" <<'EOF'
version: 1
default_action: allow
rules:
  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Redact known secrets.
    match:
      dlp_findings_min: 1
EOF

cat > "$TEST_MCP" <<'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
EOF

cat > "$TEST_CONFIG" <<EOF
gateway:
  host: 127.0.0.1
  port: $PORT
  auth_token: $AUTH_TOKEN
  mock_mode: true
  policy_dry_run: false
paths:
  log_dir: $TEST_LOG_DIR
  db_path: $TEST_DB
  policy_path: $TEST_POLICY
  mcp_config_path: $TEST_MCP
  mcp_app_home: $TEST_HOME
  repo_root: $ROOT
providers:
  openai_base_url: https://api.openai.com/v1
  openai_health_path: /models
  openai_api_key: ""
  anthropic_base_url: https://api.anthropic.com/v1
  anthropic_health_path: /models
  anthropic_api_key: ""
  anthropic_version: 2023-06-01
  local_provider: openai-compatible
  local_base_url: http://127.0.0.1:11434/v1
  local_health_path: /models
  local_fallbacks: ""
  local_api_key: ""
EOF

PYTHONPATH="$RUNTIME_PYTHONPATH" \
SPECTRONA_CONFIG_PATH="$TEST_CONFIG" \
SPECTRONA_HOME="$TEST_HOME" \
SPECTRONA_MOCK_MODE=true \
SPECTRONA_PORT="$PORT" \
SPECTRONA_GATEWAY_AUTH_TOKEN="$AUTH_TOKEN" \
SPECTRONA_DB_PATH="$TEST_DB" \
SPECTRONA_LOG_DIR="$TEST_LOG_DIR" \
SPECTRONA_POLICY_PATH="$TEST_POLICY" \
SPECTRONA_MCP_CONFIG_PATH="$TEST_MCP" \
SPECTRONA_MCP_APP_HOME="$TEST_HOME" \
SPECTRONA_REPO_ROOT="$ROOT" \
  python3 -m uvicorn spectrona_gateway.app:app \
  --host 127.0.0.1 --port "$PORT" \
  --log-level error &
GW_PID=$!

for i in $(seq 1 20); do
  sleep 0.5
  if curl -sf "$BASE/health" >/dev/null 2>&1; then
    _pass "gateway started for browser validation"
    break
  fi
  if [ "$i" -eq 20 ]; then
    _fail "gateway did not start for browser validation"
    echo ""
    echo "=== Dashboard Browser Result: $PASS passed, $FAIL failed, $SKIP skipped ==="
    exit 1
  fi
done

curl -sf -X POST "$BASE/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-spectrona-client: dashboard-browser" \
  -H "x-spectrona-project-path: /validate/browser" \
  -d '{"model":"gpt-dashboard-browser","messages":[{"role":"user","content":"render dashboard with sk-proj-browserrawsecret9999"}]}' >/dev/null

curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/browser","source_tool":"dashboard-browser","memory_type":"project_decision","content":"dashboard browser validation memory sk-proj-browsermemorysecret9999","importance_score":0.8,"tags":["dashboard","browser"],"pinned":true}' >/dev/null

_pass "browser validation fixtures created"

run_chrome() {
  local mode="$1"
  CHROME_BIN="$CHROME" \
  TEST_PROFILE="$TEST_PROFILE" \
  TEST_SCREENSHOT="$TEST_SCREENSHOT" \
  TEST_DOM="$TEST_DOM" \
  DASHBOARD_URL="$BASE/ui?token=$AUTH_TOKEN" \
  CHROME_MODE="$mode" \
  python3 - <<'PY'
import os
import subprocess
import sys

chrome = os.environ["CHROME_BIN"]
profile = os.environ["TEST_PROFILE"]
url = os.environ["DASHBOARD_URL"]
mode = os.environ["CHROME_MODE"]
cmd = [
    chrome,
    "--headless=new",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--disable-extensions",
    "--no-first-run",
    "--no-default-browser-check",
    "--run-all-compositor-stages-before-draw",
    f"--user-data-dir={profile}",
    "--window-size=1440,1200",
    "--virtual-time-budget=6000",
]
if mode == "screenshot":
    cmd.extend([f"--screenshot={os.environ['TEST_SCREENSHOT']}", url])
    stdout = subprocess.DEVNULL
elif mode == "dom":
    cmd.extend(["--dump-dom", url])
    stdout = subprocess.PIPE
else:
    raise SystemExit(f"unknown Chrome mode: {mode}")

try:
    completed = subprocess.run(cmd, stdout=stdout, stderr=subprocess.PIPE, timeout=25, check=False)
except subprocess.TimeoutExpired as exc:
    if mode == "screenshot" and os.path.exists(os.environ["TEST_SCREENSHOT"]) and os.path.getsize(os.environ["TEST_SCREENSHOT"]) > 0:
        raise SystemExit(0)
    if mode == "dom" and exc.stdout:
        with open(os.environ["TEST_DOM"], "wb") as handle:
            handle.write(exc.stdout)
        raise SystemExit(0)
    raise SystemExit("Chrome headless timed out without producing the expected artifact")

if completed.returncode != 0:
    if mode == "screenshot" and os.path.exists(os.environ["TEST_SCREENSHOT"]) and os.path.getsize(os.environ["TEST_SCREENSHOT"]) > 0:
        raise SystemExit(0)
    sys.stderr.write(completed.stderr.decode("utf-8", errors="replace")[-4000:])
    raise SystemExit(completed.returncode)

if mode == "dom":
    with open(os.environ["TEST_DOM"], "wb") as handle:
        handle.write(completed.stdout or b"")
PY
}

if run_chrome screenshot >/dev/null 2>&1; then
  _pass "Chrome captured dashboard screenshot"
else
  _fail "Chrome failed to capture dashboard screenshot"
fi

if run_chrome dom >/dev/null 2>&1; then
  _pass "Chrome dumped dashboard DOM after scripts"
else
  _fail "Chrome failed to dump dashboard DOM"
fi

if TEST_SCREENSHOT="$TEST_SCREENSHOT" python3 - <<'PY' >/dev/null 2>&1
import os
import struct
import zlib
from pathlib import Path

path = Path(os.environ["TEST_SCREENSHOT"])
data = path.read_bytes()
assert data.startswith(b"\x89PNG\r\n\x1a\n")
offset = 8
width = height = bit_depth = color_type = None
idat = []
while offset < len(data):
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    chunk_type = data[offset + 4:offset + 8]
    payload = data[offset + 8:offset + 8 + length]
    offset += 12 + length
    if chunk_type == b"IHDR":
        width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", payload)
    elif chunk_type == b"IDAT":
        idat.append(payload)
    elif chunk_type == b"IEND":
        break

assert width and height
assert width >= 1200 and height >= 900
assert bit_depth == 8
assert color_type in {2, 6}
channels = 3 if color_type == 2 else 4
bpp = channels
raw = zlib.decompress(b"".join(idat))
stride = width * channels
rows = []
pos = 0
prev = bytearray(stride)
for _ in range(height):
    filter_type = raw[pos]
    pos += 1
    row = bytearray(raw[pos:pos + stride])
    pos += stride
    for i in range(stride):
        left = row[i - bpp] if i >= bpp else 0
        up = prev[i]
        upper_left = prev[i - bpp] if i >= bpp else 0
        if filter_type == 1:
            row[i] = (row[i] + left) & 0xff
        elif filter_type == 2:
            row[i] = (row[i] + up) & 0xff
        elif filter_type == 3:
            row[i] = (row[i] + ((left + up) // 2)) & 0xff
        elif filter_type == 4:
            p = left + up - upper_left
            pa = abs(p - left)
            pb = abs(p - up)
            pc = abs(p - upper_left)
            predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
            row[i] = (row[i] + predictor) & 0xff
    rows.append(row)
    prev = row

sampled = []
step_y = max(1, height // 60)
step_x = max(1, width // 80)
for y in range(0, height, step_y):
    row = rows[y]
    for x in range(0, width, step_x):
        start = x * channels
        sampled.append(tuple(row[start:start + 3]))
unique = set(sampled)
near_white = sum(1 for rgb in sampled if all(channel >= 245 for channel in rgb))
near_black = sum(1 for rgb in sampled if all(channel <= 10 for channel in rgb))
assert len(unique) >= 20
assert near_white < len(sampled) * 0.95
assert near_black < len(sampled) * 0.95
PY
then
  _pass "dashboard screenshot is a nonblank PNG with expected dimensions"
else
  _fail "dashboard screenshot PNG validation failed"
fi

if TEST_DOM="$TEST_DOM" python3 - <<'PY' >/dev/null
import os
import sys
from pathlib import Path

html = Path(os.environ["TEST_DOM"]).read_text(errors="replace")
required = [
    "Spectrona",
    "Local guard dashboard",
    "Providers",
    "Provider Routing",
    "Protected Apps",
    "MCP Scan",
    "Token Usage",
    "Memory",
    "Session Replay",
    "Updated ",
    "Running",
    "dashboard-browser",
    "[REDACTED_SECRET]",
]
missing = []
for text in required:
    if text not in html:
        missing.append(text)
for raw in ("browserrawsecret9999", "browsermemorysecret9999"):
    if raw in html:
        missing.append(f"raw secret leaked: {raw}")
if missing:
    sys.stderr.write("missing/invalid DOM markers: " + ", ".join(missing) + "\n")
    raise SystemExit(1)
PY
then
  _pass "dashboard rendered post-JS DOM with expected panels and redaction"
else
  _fail "dashboard DOM validation failed"
fi

echo ""
echo "=== Dashboard Browser Result: $PASS passed, $FAIL failed, $SKIP skipped ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
