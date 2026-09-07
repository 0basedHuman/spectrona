#!/usr/bin/env bash
# Phase 2 validation — spectrona-gateway
# Starts gateway in mock mode, runs curl checks, verifies audit log + DLP.

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATEWAY_SRC="$ROOT/spectrona-gateway/src"
CLI_SRC="$ROOT/spectrona-cli/src"
POLICY_SRC="$ROOT/policy-engine/src"
INSPECTOR_SRC="$ROOT/mcp-inspector/src"
RUNTIME_GUARD_SRC="$ROOT/runtime-guard/src"
DETECTION_SRC="$ROOT/spectrona-detection/src"
RUNTIME_PYTHONPATH="$DETECTION_SRC:$GATEWAY_SRC:$CLI_SRC:$POLICY_SRC:$INSPECTOR_SRC:$RUNTIME_GUARD_SRC"
PORT=18788
BASE="http://127.0.0.1:$PORT"
AUTH_TOKEN="phase2-gateway-auth-token"
GW_PID=""
TEST_DB="/tmp/spectrona_gateway_events_$$.db"
CONFIG_SECRET_FILE="/tmp/spectrona_gateway_config_secrets_$$.json"
STORED_SECRET_FILE="/tmp/spectrona_gateway_stored_secrets_$$.json"
RUNTIME_SECRETS_FILE="/tmp/spectrona_gateway_runtime_secrets_$$.json"
RUNTIME_CONFIG_FILE="/tmp/spectrona_gateway_runtime_config_$$.yaml"
RUNTIME_POLICY_FILE="/tmp/spectrona_gateway_runtime_policy_$$.yaml"
RUNTIME_LOG_DIR="/tmp/spectrona_gateway_runtime_logs_$$"
MCP_APPS_HOME="/tmp/spectrona_gateway_mcp_apps_home_$$"
PROVIDER_ROUTING_HOME="/tmp/spectrona_gateway_provider_routing_$$"
CLAUDE_ROUTING_ENV="$PROVIDER_ROUTING_HOME/claude.env"
CODEX_ROUTING_CONFIG="$PROVIDER_ROUTING_HOME/codex-config.toml"
VSCODE_ROUTING_SETTINGS="$PROVIDER_ROUTING_HOME/vscode-settings.json"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
curl() { command curl -H "Authorization: Bearer $AUTH_TOKEN" "$@"; }

_cleanup() {
  [ -n "$GW_PID" ] && kill "$GW_PID" 2>/dev/null && wait "$GW_PID" 2>/dev/null || true
  rm -f "$TEST_DB"
  rm -f "$CONFIG_SECRET_FILE"
  rm -f "$STORED_SECRET_FILE"
  rm -f "$RUNTIME_SECRETS_FILE"
  rm -f "$RUNTIME_CONFIG_FILE" "$RUNTIME_CONFIG_FILE".spectrona.bak*
  rm -f "$RUNTIME_POLICY_FILE" "$RUNTIME_POLICY_FILE".spectrona.bak*
  rm -rf "$RUNTIME_LOG_DIR"
  rm -rf "$MCP_APPS_HOME"
  rm -rf "$PROVIDER_ROUTING_HOME"
}
trap _cleanup EXIT

check() {
  local desc="$1" path="$2"
  [ -e "$path" ] && _pass "$desc" || _fail "$desc — missing: $path"
}

# ── Scaffold checks ───────────────────────────────────────────────────────────

echo ""
echo "=== Phase 2 Validation: spectrona-gateway ==="
echo ""
echo "--- Scaffold ---"
check "app.py"                    "$ROOT/spectrona-gateway/src/spectrona_gateway/app.py"
check "config.py"                 "$ROOT/spectrona-gateway/src/spectrona_gateway/config.py"
check "audit.py"                  "$ROOT/spectrona-gateway/src/spectrona_gateway/audit.py"
check "dlp.py"                    "$ROOT/spectrona-gateway/src/spectrona_gateway/dlp.py"
check "policy.py"                 "$ROOT/spectrona-gateway/src/spectrona_gateway/policy.py"
check "events/store.py"           "$ROOT/spectrona-gateway/src/spectrona_gateway/events/store.py"
check "events/tokens.py"          "$ROOT/spectrona-gateway/src/spectrona_gateway/events/tokens.py"
check "ui/index.html"             "$ROOT/spectrona-gateway/src/spectrona_gateway/ui/index.html"
check "routes/health.py"          "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/health.py"
check "routes/openai_compat.py"   "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/openai_compat.py"
check "routes/anthropic_compat.py" "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/anthropic_compat.py"
check "routes/local_compat.py"    "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/local_compat.py"
check "routes/events.py"          "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/events.py"
check "routes/integrations.py"    "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/integrations.py"
check "routes/mcp.py"             "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/mcp.py"
check "routes/policy.py"          "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/policy.py"
check "routes/response_guard.py"  "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/response_guard.py"
check "routes/ui.py"              "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/ui.py"
check "routes/providers.py"       "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/providers.py"
check "providers/passthrough.py"  "$ROOT/spectrona-gateway/src/spectrona_gateway/providers/passthrough.py"
check "passthrough validation helper" "$ROOT/spectrona-gateway/validation/passthrough_fake_upstream.py"
check "local LLM discovery validation helper" "$ROOT/spectrona-gateway/validation/local_llm_discovery_validate.py"
check "local fallback validation helper" "$ROOT/spectrona-gateway/validation/local_fallback_validate.py"
check "policy validation helper" "$ROOT/spectrona-gateway/validation/policy_gateway_validate.py"
check "policy dry-run validation helper" "$ROOT/spectrona-gateway/validation/policy_dry_run_validate.py"

# ── Dependency check ─────────────────────────────────────────────────────────

echo ""
echo "--- Dependencies ---"
if PYTHONPATH="$DETECTION_SRC:$CLI_SRC:$POLICY_SRC:$INSPECTOR_SRC:$RUNTIME_GUARD_SRC" python3 -c "import fastapi, uvicorn, httpx, spectrona_cli.routing, spectrona_cli.secrets, spectrona_cli.integration_manager, spectrona_cli.local_llms, policy_engine, mcp_inspector, runtime_guard, spectrona_detection" 2>/dev/null; then
  _pass "fastapi, uvicorn, httpx, spectrona_cli, local_llms, secrets, policy_engine, mcp_inspector, runtime_guard importable"
else
  _fail "fastapi/uvicorn/httpx/spectrona_cli/local_llms/secrets/policy_engine/mcp_inspector/runtime_guard not importable"
  echo ""
  echo "=== Phase 2 Result: $PASS passed, $FAIL failed (deps missing — cannot continue) ==="
  exit 1
fi

echo ""
echo "--- Config file loading ---"
CONFIG_TMP="/tmp/spectrona_gateway_config_$$.yaml"
cat > "$CONFIG_TMP" <<EOF
gateway:
  host: 127.0.0.1
  port: 19191
  auth_token: $AUTH_TOKEN
  mock_mode: false
  policy_dry_run: true
paths:
  log_dir: /tmp/spectrona_gateway_logs_$$
  db_path: /tmp/spectrona_gateway_memory_$$.db
  policy_path: /tmp/spectrona_gateway_policy_$$.yaml
  mcp_config_path: /tmp/spectrona_gateway_mcp_$$.json
  mcp_app_home: /tmp/spectrona_gateway_mcp_apps_home_$$
  repo_root: $ROOT
providers:
  openai_base_url: http://127.0.0.1:19999/v1
  openai_health_path: /models
  openai_api_key: config-openai-key
  anthropic_base_url: http://127.0.0.1:19998/v1
  anthropic_health_path: /models
  anthropic_api_key: config-anthropic-key
  anthropic_version: 2023-06-01
  local_provider: openai-compatible
  local_base_url: http://127.0.0.1:11434/v1
  local_health_path: /models
  local_fallbacks: lm-studio
  local_api_key: config-local-key
EOF

if SPECTRONA_CONFIG_PATH="$CONFIG_TMP" SPECTRONA_SECRETS_BACKEND=file SPECTRONA_SECRETS_FILE="$CONFIG_SECRET_FILE" PYTHONPATH="$RUNTIME_PYTHONPATH" python3 -c "
from spectrona_gateway import config
assert config.PORT == 19191
assert config.GATEWAY_AUTH_TOKEN == '$AUTH_TOKEN'
assert config.MOCK_MODE is False
assert config.POLICY_DRY_RUN is True
assert str(config.LOG_DIR).endswith('spectrona_gateway_logs_$$')
assert str(config.POLICY_PATH).endswith('spectrona_gateway_policy_$$.yaml')
assert config.MCP_CONFIG_PATH.endswith('spectrona_gateway_mcp_$$.json')
assert config.MCP_APP_HOME.endswith('spectrona_gateway_mcp_apps_home_$$')
assert str(config.REPO_ROOT) == '$ROOT'
assert config.OPENAI_BASE_URL == 'http://127.0.0.1:19999/v1'
assert config.OPENAI_HEALTH_PATH == '/models'
assert config.OPENAI_API_KEY == 'config-openai-key'
assert config.ANTHROPIC_BASE_URL == 'http://127.0.0.1:19998/v1'
assert config.ANTHROPIC_HEALTH_PATH == '/models'
assert config.ANTHROPIC_API_KEY == 'config-anthropic-key'
assert config.LOCAL_PROVIDER == 'openai-compatible'
assert config.LOCAL_BASE_URL == 'http://127.0.0.1:11434/v1'
assert config.LOCAL_HEALTH_PATH == '/models'
assert config.LOCAL_FALLBACKS == 'lm-studio'
assert config.LOCAL_API_KEY == 'config-local-key'
" 2>/dev/null; then
  _pass "gateway loads ~/.spectrona/config.yaml-style config"
else
  _fail "gateway failed to load config file values"
fi
rm -f "$CONFIG_TMP"

RESPONSE_POLICY_TMP="/tmp/spectrona_gateway_response_policy_$$.yaml"
cat > "$RESPONSE_POLICY_TMP" <<EOF
version: 1
default_action: allow
rules:
  - id: redact-response-secret
    action: redact
    enabled: true
    reason: Redact response secrets.
    match:
      dlp_findings_min: 1
EOF
if SPECTRONA_POLICY_PATH="$RESPONSE_POLICY_TMP" PYTHONPATH="$RUNTIME_PYTHONPATH" python3 - <<'PY' >/dev/null 2>&1
from spectrona_gateway import policy
result = policy.evaluate_response(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-test",
    client="codex",
    content_bytes=b'{"content":"sk-proj-abc123XYZresponse9999"}',
)
assert result.decision.action == "redact"
assert result.dlp_findings_count == 1
assert b"abc123XYZresponse9999" not in result.content_bytes
assert b"sk-proj-[REDACTED_SECRET]" in result.content_bytes
PY
then
  _pass "gateway response policy hook redacts secret-bearing model output"
else
  _fail "gateway response policy hook failed to redact secret-bearing model output"
fi
rm -f "$RESPONSE_POLICY_TMP"

DRY_RUN_POLICY_TMP="/tmp/spectrona_gateway_dry_run_policy_$$.yaml"
cat > "$DRY_RUN_POLICY_TMP" <<EOF
version: 1
default_action: allow
rules:
  - id: deny-shell-dry-run
    action: deny
    enabled: true
    reason: Dry run shell deny.
    match:
      shell_risk: true
  - id: redact-secret-dry-run
    action: redact
    enabled: true
    reason: Dry run redact.
    match:
      dlp_findings_min: 1
EOF
if SPECTRONA_POLICY_DRY_RUN=true SPECTRONA_POLICY_PATH="$DRY_RUN_POLICY_TMP" PYTHONPATH="$RUNTIME_PYTHONPATH" python3 - <<'PY' >/dev/null 2>&1
from spectrona_gateway import policy

shell = policy.evaluate_request(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-test",
    body_bytes=b'{"messages":[{"content":"pwd"}]}',
    body_str='{"messages":[{"content":"pwd"}]}',
    headers={"x-spectrona-shell-risk": "true"},
    dlp_findings_count=0,
)
assert shell.decision.action == "deny"
assert shell.blocked is False
assert shell.policy_action == "dry_run_deny"
assert shell.audit_action("passthrough") == "would_block_then_passthrough"

raw = '{"messages":[{"content":"sk-proj-abc123XYZdryrun9999"}]}'
redact = policy.evaluate_request(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-test",
    body_bytes=raw.encode("utf-8"),
    body_str=raw,
    headers={},
    dlp_findings_count=1,
)
assert redact.decision.action == "redact"
assert redact.blocked is False
assert "abc123XYZdryrun9999" in redact.body_str
assert redact.policy_action == "dry_run_redact"
assert redact.audit_action("passthrough") == "would_redact_then_passthrough"

response = policy.evaluate_response(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-test",
    client="codex",
    content_bytes=b'{"content":"sk-proj-abc123XYZresponse9999"}',
)
assert response.decision.action == "redact"
assert response.blocked is False
assert b"abc123XYZresponse9999" in response.content_bytes
assert response.policy_action == "dry_run_redact"
PY
then
  _pass "gateway policy dry-run records would-actions without blocking or redacting"
else
  _fail "gateway policy dry-run direct evaluation failed"
fi
rm -f "$DRY_RUN_POLICY_TMP"

if SPECTRONA_CONFIG_PATH="/tmp/spectrona_gateway_no_config_$$.yaml" SPECTRONA_SECRETS_BACKEND=file SPECTRONA_SECRETS_FILE="$STORED_SECRET_FILE" PYTHONPATH="$RUNTIME_PYTHONPATH" python3 - <<'PY' >/dev/null 2>&1
from spectrona_cli.secrets import set_provider_secret
set_provider_secret("openai", "stored-openai-key")
set_provider_secret("anthropic", "stored-anthropic-key")
set_provider_secret("local", "stored-local-key")
from spectrona_gateway import config
assert config.OPENAI_API_KEY == "stored-openai-key"
assert config.ANTHROPIC_API_KEY == "stored-anthropic-key"
assert config.LOCAL_API_KEY == "stored-local-key"
PY
then
  _pass "gateway loads provider API keys from stored secrets"
else
  _fail "gateway failed to load provider API keys from stored secrets"
fi

if SPECTRONA_CONFIG_PATH="/tmp/spectrona_gateway_no_config_$$.yaml" SPECTRONA_OPENAI_API_KEY="env-openai-key" SPECTRONA_SECRETS_BACKEND=file SPECTRONA_SECRETS_FILE="$STORED_SECRET_FILE" PYTHONPATH="$RUNTIME_PYTHONPATH" python3 - <<'PY' >/dev/null 2>&1
from spectrona_cli.secrets import set_provider_secret
set_provider_secret("openai", "stored-openai-key")
from spectrona_gateway import config
assert config.OPENAI_API_KEY == "env-openai-key"
PY
then
  _pass "gateway provider env vars override stored secrets"
else
  _fail "gateway provider env vars did not override stored secrets"
fi

# ── Start gateway ─────────────────────────────────────────────────────────────

echo ""
echo "--- Starting gateway on port $PORT ---"

mkdir -p "$MCP_APPS_HOME/.claude" "$MCP_APPS_HOME/.codex"
mkdir -p "$PROVIDER_ROUTING_HOME"
cat > "$RUNTIME_POLICY_FILE" <<'EOF'
# Spectrona local runtime policy
# This file is evaluated locally by the Spectrona gateway and future MCP proxy.

version: 1
default_action: allow

rules:
  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Redact known secret values before provider forwarding.
    match:
      dlp_findings_min: 1

  - id: deny-shell-risk
    action: deny
    enabled: true
    reason: Block shell-risk actions until explicit MCP approvals exist.
    match:
      shell_risk: true

  - id: deny-filesystem-risk
    action: deny
    enabled: true
    reason: Block filesystem-risk actions until project allowlists exist.
    match:
      filesystem_risk: true

  - id: approval-example-high-dlp
    action: require_approval
    enabled: false
    reason: Example only. Require approval when many DLP findings appear.
    match:
      dlp_findings_min: 3
EOF
cat > "$RUNTIME_CONFIG_FILE" <<EOF
gateway:
  host: 127.0.0.1
  port: $PORT
  auth_token: $AUTH_TOKEN
  mock_mode: true
  policy_dry_run: false
paths:
  log_dir: $RUNTIME_LOG_DIR
  db_path: $TEST_DB
  policy_path: $RUNTIME_POLICY_FILE
  mcp_config_path: $ROOT/mcp-inspector/examples/unsafe-mcp-configs/basic-unrestricted-filesystem.json
  mcp_app_home: $MCP_APPS_HOME
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
cp "$ROOT/mcp-inspector/examples/unsafe-mcp-configs/basic-unrestricted-filesystem.json" "$MCP_APPS_HOME/.claude/mcp.json"
printf 'existing = true\n' > "$CODEX_ROUTING_CONFIG"
printf '{"editor.tabSize": 2}\n' > "$VSCODE_ROUTING_SETTINGS"
cat > "$MCP_APPS_HOME/.codex/mcp.json" <<EOF
{
  "mcpServers": {
    "safe": {
      "command": "spectrona",
      "args": ["mcp", "proxy", "--client", "mcp:safe", "--", "npx", "-y", "safe-server"]
    }
  }
}
EOF

AUDIT_LOG="$RUNTIME_LOG_DIR/audit.jsonl"

# Clear previous test entries for clean assertion
if [ -f "$AUDIT_LOG" ]; then
  LINES_BEFORE=$(wc -l < "$AUDIT_LOG")
else
  LINES_BEFORE=0
fi

PYTHONPATH="$RUNTIME_PYTHONPATH" \
SPECTRONA_MOCK_MODE=true \
SPECTRONA_CONFIG_PATH="$RUNTIME_CONFIG_FILE" \
SPECTRONA_GATEWAY_AUTH_TOKEN="$AUTH_TOKEN" \
SPECTRONA_PORT=$PORT \
SPECTRONA_OPENAI_API_KEY= \
SPECTRONA_ANTHROPIC_API_KEY= \
SPECTRONA_LOCAL_API_KEY= \
SPECTRONA_SECRETS_BACKEND=file \
SPECTRONA_SECRETS_FILE="$RUNTIME_SECRETS_FILE" \
SPECTRONA_DB_PATH="$TEST_DB" \
SPECTRONA_POLICY_PATH="$RUNTIME_POLICY_FILE" \
SPECTRONA_MCP_CONFIG_PATH="$ROOT/mcp-inspector/examples/unsafe-mcp-configs/basic-unrestricted-filesystem.json" \
SPECTRONA_MCP_APP_HOME="$MCP_APPS_HOME" \
SPECTRONA_CLAUDE_ENV_PATH="$CLAUDE_ROUTING_ENV" \
SPECTRONA_CODEX_CONFIG_PATH="$CODEX_ROUTING_CONFIG" \
SPECTRONA_VSCODE_SETTINGS_PATH="$VSCODE_ROUTING_SETTINGS" \
SPECTRONA_REPO_ROOT="$ROOT" \
  python3 -m uvicorn spectrona_gateway.app:app \
  --host 127.0.0.1 --port $PORT \
  --log-level error &
GW_PID=$!

# Poll until ready (max 8 seconds)
for i in $(seq 1 16); do
  sleep 0.5
  if curl -sf "$BASE/health" >/dev/null 2>&1; then
    _pass "gateway started (pid=$GW_PID)"
    break
  fi
  if [ "$i" -eq 16 ]; then
    _fail "gateway did not start within 8 seconds"
    exit 1
  fi
done

# ── Endpoint checks ───────────────────────────────────────────────────────────

echo ""
echo "--- Endpoint: /health ---"
HEALTH=$(curl -sf "$BASE/health" 2>/dev/null)
if echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['status']=='ok'" 2>/dev/null; then
  _pass "GET /health → {status: ok}"
else
  _fail "GET /health — unexpected response: $HEALTH"
fi

POLICY_APPLY_UNAUTH_STATUS=$(command curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/policy/presets/relaxed/apply" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
[ "$POLICY_APPLY_UNAUTH_STATUS" = "401" ] \
  && _pass "POST /policy/presets/{preset}/apply rejects missing bearer token" \
  || _fail "POST /policy/presets/{preset}/apply unauthenticated status=$POLICY_APPLY_UNAUTH_STATUS"

HOST_REBIND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/policy" \
  -H "Host: attacker.example" 2>/dev/null)
[ "$HOST_REBIND_STATUS" = "400" ] \
  && _pass "Gateway rejects disallowed Host header" \
  || _fail "Gateway did not reject disallowed Host header (status=$HOST_REBIND_STATUS)"

ORIGIN_REBIND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/policy" \
  -H "Origin: http://attacker.example" 2>/dev/null)
[ "$ORIGIN_REBIND_STATUS" = "403" ] \
  && _pass "Gateway rejects disallowed Origin header" \
  || _fail "Gateway did not reject disallowed Origin header (status=$ORIGIN_REBIND_STATUS)"

echo ""
echo "--- Endpoint: /ui ---"
UI=$(curl -sf "$BASE/ui?token=$AUTH_TOKEN" 2>/dev/null)
if echo "$UI" | python3 -c "
import sys
html=sys.stdin.read()
assert '<title>Spectrona Dashboard</title>' in html
assert 'data-testid=\"summary-grid\"' in html
assert '/events/recent?limit=25' in html
assert '/events/token-usage' in html
assert 'Token Usage' in html
assert 'usage-summary' in html
assert 'usage-status' in html
assert 'Daily Totals' in html
assert 'usage-bar' in html
assert '/events/blocks?limit=6' in html
assert '/events/dlp?limit=6' in html
assert '/providers/health' in html
assert 'local_runtimes' in html
assert 'Local runtimes' in html
assert 'selected_config' in html
assert 'fallback_config' in html
assert 'fallback' in html
assert '/providers/local-runtimes/\${encodeURIComponent(runtimeId)}/select' in html
assert 'data-runtime-action=\"select\"' in html
assert '/policy' in html
assert '/policy/backups' in html
assert '/policy/presets/\${encodeURIComponent(policyPreset)}/apply' in html
assert '/policy/backups/\${encodeURIComponent(policyBackup)}/restore' in html
assert '/providers/integrations' in html
assert '/providers/integrations/\${encodeURIComponent(routingId)}/\${routingAction}' in html
assert 'memoryQueryPath' in html
assert 'memoryContextPath' in html
assert 'memoryTimelinePath' in html
assert 'memorySessionPath' in html
assert 'memoryCompactPath' in html
assert 'memoryReplayPath' in html
assert '/memory/items?' in html
assert '/memory/context?' in html
assert '/memory/timeline?limit=8' in html
assert '/memory/extract?limit=100&max_summary_chars=1200' in html
assert '/memory/compact?limit=100&max_summary_chars=1200' in html
assert '/memory/replay?limit=100&max_replay_chars=1600' in html
assert 'memory-filter-form' in html
assert 'Fresh Context Package' in html
assert 'Session Extraction' in html
assert 'Memory Compaction' in html
assert 'Session Replay' in html
assert 'memoryFreshness' in html
assert 'renderMemoryTimeline' in html
assert 'renderMemorySession' in html
assert 'renderMemoryCompact' in html
assert 'renderMemoryReplay' in html
assert 'rawStorageBadge' in html
assert 'raw_storage_mode' in html
assert 'data-memory-extract=\"apply\"' in html
assert 'postJson(\"/memory/extract\", { confirm: true' in html
assert 'data-memory-compact=\"apply\"' in html
assert 'postJson(\"/memory/compact\", { confirm: true' in html
assert 'data-memory-replay=\"apply\"' in html
assert 'postJson(\"/memory/replay\", { confirm: true' in html
assert 'data-memory-action=\"pin\"' in html
assert 'data-memory-action=\"delete\"' in html
assert '/memory/items/\${encodeURIComponent(memoryId)}' in html
assert '/memory/items/\${encodeURIComponent(memoryId)}?confirm=true' in html
assert '/mcp/scan' in html
assert '/mcp/apps' in html
assert '/mcp/apps/\${encodeURIComponent(appId)}/\${action}' in html
assert 'drifted' in html
assert 'Runtime Blocks' in html
assert 'DLP Activity' in html
assert 'Policy' in html
assert 'MCP Scan' in html
assert 'Protected Apps' in html
assert 'Provider Routes' in html
assert 'Provider Routing' in html
assert 'Repair' in html
assert 'data-policy-preset' in html
assert 'data-policy-backup' in html
assert 'data-app-action=\"protect\"' in html
assert 'data-app-action=\"unprotect\"' in html
assert 'data-routing-action=\"protect\"' in html
assert 'data-routing-action=\"unprotect\"' in html
" 2>/dev/null; then
  _pass "GET /ui → dashboard shell wired to runtime, DLP, blocks, MCP, protected-app, provider-routing, local-runtime selection/fallback, memory management/extraction/compaction/replay, and policy APIs/actions"
else
  _fail "GET /ui — dashboard shell missing expected content"
fi

echo ""
echo "--- Endpoint: /policy ---"
POLICY_STATUS=$(curl -sf "$BASE/policy" 2>/dev/null)
if echo "$POLICY_STATUS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['path'].endswith('spectrona_gateway_runtime_policy_$$.yaml')
assert d['exists'] is True
assert d['dry_run'] is False
assert d['active_preset_id'] == 'balanced'
assert d['policy']['default_action'] == 'allow'
rule_ids={rule['id'] for rule in d['policy']['rules']}
assert {'redact-known-secrets','deny-shell-risk','deny-filesystem-risk'}.issubset(rule_ids)
assert d['summary']['enabled_rules'] >= 3
assert {'relaxed','balanced','strict'} == {preset['preset_id'] for preset in d['presets']}
" 2>/dev/null; then
  _pass "GET /policy → current policy metadata and presets without raw policy text"
else
  _fail "GET /policy — unexpected response: $POLICY_STATUS"
fi

POLICY_PRESETS=$(curl -sf "$BASE/policy/presets" 2>/dev/null)
STRICT_PRESET=$(curl -sf "$BASE/policy/presets/strict" 2>/dev/null)
if printf '%s\n%s\n' "$POLICY_PRESETS" "$STRICT_PRESET" | python3 -c "
import json,sys
presets=json.loads(sys.stdin.readline())
strict=json.loads(sys.stdin.readline())
assert presets['status'] == 'ok'
assert presets['active_preset_id'] == 'balanced'
items={item['preset_id']: item for item in presets['presets']}
assert {'relaxed','balanced','strict'}.issubset(items)
assert items['relaxed']['enabled_rules'] < items['balanced']['enabled_rules']
assert strict['status'] == 'ok'
assert strict['preset_id'] == 'strict'
assert strict['policy']['default_action'] == 'allow'
assert any(rule['id'] == 'approval-multiple-secrets' for rule in strict['policy']['rules'])
" 2>/dev/null; then
  _pass "GET /policy/presets → relaxed, balanced, and strict preset metadata"
else
  _fail "GET /policy/presets — unexpected responses: $POLICY_PRESETS $STRICT_PRESET"
fi

POLICY_APPLY_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/policy/presets/relaxed/apply" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$POLICY_APPLY_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /policy/presets/{preset}/apply requires explicit confirm=true" \
  || _fail "POST /policy/presets/{preset}/apply did not require confirmation (status=$POLICY_APPLY_NO_CONFIRM_STATUS)"

POLICY_RELAXED=$(curl -sf -X POST "$BASE/policy/presets/relaxed/apply" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
POLICY_REBALANCED=$(curl -sf -X POST "$BASE/policy/presets/balanced/apply" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
POLICY_AFTER_REBALANCE=$(curl -sf "$BASE/policy" 2>/dev/null)
if printf '%s\n%s\n%s\n' "$POLICY_RELAXED" "$POLICY_REBALANCED" "$POLICY_AFTER_REBALANCE" | python3 -c "
import json,sys
relaxed=json.loads(sys.stdin.readline())
balanced=json.loads(sys.stdin.readline())
current=json.loads(sys.stdin.readline())
assert relaxed['status'] == 'ok'
assert relaxed['preset_id'] == 'relaxed'
assert relaxed['changed'] is True
assert relaxed['backup_path'].endswith('.spectrona.bak')
assert relaxed['active_preset_id'] == 'relaxed'
assert any(rule['id'] == 'observe-shell-risk' and rule['enabled'] is False for rule in relaxed['policy']['rules'])
assert balanced['status'] == 'ok'
assert balanced['preset_id'] == 'balanced'
assert balanced['changed'] is True
assert current['active_preset_id'] == 'balanced'
assert any(rule['id'] == 'deny-shell-risk' and rule['enabled'] is True for rule in current['policy']['rules'])
" 2>/dev/null && [ -f "$RUNTIME_POLICY_FILE.spectrona.bak" ]; then
  _pass "POST /policy/presets/{preset}/apply writes policy preset with backup and can restore balanced"
else
  _fail "POST /policy/presets/{preset}/apply failed: $POLICY_RELAXED $POLICY_REBALANCED"
fi

POLICY_BACKUPS=$(curl -sf "$BASE/policy/backups" 2>/dev/null)
if echo "$POLICY_BACKUPS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['path'].endswith('spectrona_gateway_runtime_policy_$$.yaml')
assert d['summary']['total'] >= 2
assert d['summary']['restorable'] >= 2
ids={item['active_preset_id'] for item in d['backups']}
assert {'balanced','relaxed'}.issubset(ids)
assert all(item['backup_id'].startswith('spectrona_gateway_runtime_policy_$$.yaml.spectrona.bak') for item in d['backups'])
" 2>/dev/null; then
  _pass "GET /policy/backups → restorable policy backup metadata"
else
  _fail "GET /policy/backups — unexpected response: $POLICY_BACKUPS"
fi

RELAXED_BACKUP_ID=$(printf '%s\n' "$POLICY_BACKUPS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for item in d['backups']:
    if item.get('active_preset_id') == 'relaxed':
        print(item['backup_id'])
        break
" 2>/dev/null)
POLICY_RESTORE_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/policy/backups/$RELAXED_BACKUP_ID/restore" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$POLICY_RESTORE_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /policy/backups/{backup}/restore requires explicit confirm=true" \
  || _fail "POST /policy/backups/{backup}/restore did not require confirmation (status=$POLICY_RESTORE_NO_CONFIRM_STATUS)"

POLICY_RESTORED=$(curl -sf -X POST "$BASE/policy/backups/$RELAXED_BACKUP_ID/restore" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
POLICY_REBALANCED_AFTER_RESTORE=$(curl -sf -X POST "$BASE/policy/presets/balanced/apply" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
POLICY_AFTER_RESTORE_REBALANCE=$(curl -sf "$BASE/policy" 2>/dev/null)
if printf '%s\n%s\n%s\n' "$POLICY_RESTORED" "$POLICY_REBALANCED_AFTER_RESTORE" "$POLICY_AFTER_RESTORE_REBALANCE" | python3 -c "
import json,sys
restored=json.loads(sys.stdin.readline())
balanced=json.loads(sys.stdin.readline())
current=json.loads(sys.stdin.readline())
assert restored['status'] == 'ok'
assert restored['action'] == 'restore_backup'
assert restored['changed'] is True
assert restored['backup_id'].endswith('.spectrona.bak.1')
assert restored['active_preset_id'] == 'relaxed'
assert restored['current_backup_path'].endswith('.spectrona.bak.2')
assert any(rule['id'] == 'observe-shell-risk' and rule['enabled'] is False for rule in restored['policy']['rules'])
assert balanced['status'] == 'ok'
assert balanced['preset_id'] == 'balanced'
assert current['active_preset_id'] == 'balanced'
" 2>/dev/null; then
  _pass "POST /policy/backups/{backup}/restore restores a policy backup and preserves current policy backup"
else
  _fail "POST /policy/backups/{backup}/restore failed: $POLICY_RESTORED"
fi

echo ""
echo "--- Endpoint: /mcp/scan ---"
MCP_SCAN=$(curl -sf "$BASE/mcp/scan" 2>/dev/null)
if echo "$MCP_SCAN" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'scanned'
assert d['scan_target'].endswith('basic-unrestricted-filesystem.json')
assert d['summary']['critical'] >= 1
assert d['summary']['high'] >= 2
ids={f['id'] for f in d['findings']}
assert {'SECRET_KNOWN_PREFIX','MCP_FS_OUTSIDE_REPO','MCP_SHELL_UNRESTRICTED','MCP_UNPINNED_PACKAGE'}.issubset(ids)
assert any(f.get('server_name') == 'shell-runner' for f in d['findings'])
" 2>/dev/null; then
  _pass "GET /mcp/scan → MCP findings API returns redacted scanner results"
else
  _fail "GET /mcp/scan — unexpected response: $MCP_SCAN"
fi

if echo "$MCP_SCAN" | grep -q "abc123XYZsecretToken"; then
  _fail "CRITICAL: raw secret value found in MCP scan API"
else
  _pass "MCP scan API does not contain raw secret value"
fi

echo ""
echo "--- Endpoint: /mcp/apps ---"
MCP_APPS=$(curl -sf "$BASE/mcp/apps" 2>/dev/null)
if echo "$MCP_APPS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['home'].endswith('spectrona_gateway_mcp_apps_home_$$')
assert d['summary']['total'] >= 7
assert d['summary']['protected'] >= 1
assert d['summary']['unprotected'] >= 1
assert d['summary']['drifted'] >= 0
apps={item['app_id']: item for item in d['apps']}
assert apps['claude-code']['status'] == 'unprotected'
assert apps['claude-code']['unwrapped_servers'] >= 1
assert apps['claude-code']['drift_detected'] is False
assert apps['claude-code']['recommended_action'] == 'protect'
assert apps['claude-code']['repair_available'] is True
assert apps['codex']['status'] == 'protected'
assert apps['codex']['wrapped_servers'] == 1
assert apps['codex']['recommended_action'] == 'none'
assert apps['workspace-mcp']['status'] == 'missing'
assert apps['workspace-mcp']['recommended_action'] == 'none'
" 2>/dev/null; then
  _pass "GET /mcp/apps → protected app status API reports detected MCP app states"
else
  _fail "GET /mcp/apps — unexpected response: $MCP_APPS"
fi

if echo "$MCP_APPS" | grep -q "abc123XYZsecretToken"; then
  _fail "CRITICAL: raw secret value found in MCP app status API"
else
  _pass "MCP app status API does not contain raw secret value"
fi

echo ""
echo "--- Endpoint: /mcp/apps actions ---"
MCP_PROTECT_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/mcp/apps/claude-code/protect" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$MCP_PROTECT_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /mcp/apps/{app}/protect requires explicit confirm=true" \
  || _fail "POST /mcp/apps/{app}/protect did not require confirmation (status=$MCP_PROTECT_NO_CONFIRM_STATUS)"

MCP_PROTECT=$(curl -sf -X POST "$BASE/mcp/apps/claude-code/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$MCP_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'protect'
result=d['result']
assert result['app_id'] == 'claude-code'
assert result['changed'] is True
assert result['before_status'] == 'unprotected'
assert result['after_status'] == 'protected'
assert result['wrapped_servers'] >= 1
assert result['backup_path'].endswith('.spectrona.bak')
" 2>/dev/null && python3 - "$MCP_APPS_HOME/.claude/mcp.json" <<'PY' >/dev/null 2>&1
import json,sys
data=json.load(open(sys.argv[1]))
server=data["mcpServers"]["filesystem"]
assert server["command"] == "spectrona"
assert "--policy" in server["args"]
assert "--audit-log" in server["args"]
PY
then
  _pass "POST /mcp/apps/{app}/protect wraps config with gateway policy/audit settings"
else
  _fail "POST /mcp/apps/{app}/protect failed: $MCP_PROTECT"
fi

if echo "$MCP_PROTECT" | grep -q "abc123XYZsecretToken"; then
  _fail "CRITICAL: raw secret value found in MCP app protect API"
else
  _pass "MCP app protect API does not contain raw secret value"
fi

MCP_AFTER_PROTECT=$(curl -sf "$BASE/mcp/apps" 2>/dev/null)
if echo "$MCP_AFTER_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
apps={item['app_id']: item for item in d['apps']}
assert apps['claude-code']['status'] == 'protected'
assert apps['claude-code']['backup_exists'] is True
assert apps['claude-code']['drift_detected'] is False
assert apps['claude-code']['recommended_action'] == 'none'
" 2>/dev/null; then
  _pass "GET /mcp/apps reflects protected state after app protect action"
else
  _fail "GET /mcp/apps did not reflect protected state after protect"
fi

python3 - "$MCP_APPS_HOME/.claude/mcp.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["mcpServers"]["rogue"] = {"command": "npx", "args": ["-y", "rogue-server"]}
path.write_text(json.dumps(data, indent=2) + "\n")
PY

MCP_DRIFT=$(curl -sf "$BASE/mcp/apps" 2>/dev/null)
if echo "$MCP_DRIFT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['summary']['drifted'] >= 1
apps={item['app_id']: item for item in d['apps']}
claude=apps['claude-code']
assert claude['status'] == 'partial'
assert claude['drift_detected'] is True
assert claude['recommended_action'] == 'repair'
assert claude['repair_available'] is True
" 2>/dev/null; then
  _pass "GET /mcp/apps detects drift after protected config changes"
else
  _fail "GET /mcp/apps did not detect protected config drift: $MCP_DRIFT"
fi

MCP_REPAIR=$(curl -sf -X POST "$BASE/mcp/apps/claude-code/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$MCP_REPAIR" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'protect'
result=d['result']
assert result['app_id'] == 'claude-code'
assert result['changed'] is True
assert result['before_status'] == 'partial'
assert result['after_status'] == 'protected'
assert result['wrapped_servers'] >= 1
assert result['already_wrapped_servers'] >= 1
" 2>/dev/null; then
  _pass "POST /mcp/apps/{app}/protect repairs drifted config"
else
  _fail "POST /mcp/apps/{app}/protect did not repair drifted config: $MCP_REPAIR"
fi

MCP_UNPROTECT=$(curl -sf -X POST "$BASE/mcp/apps/claude-code/unprotect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$MCP_UNPROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'unprotect'
result=d['result']
assert result['app_id'] == 'claude-code'
assert result['changed'] is True
assert result['before_status'] == 'protected'
assert result['after_status'] == 'unprotected'
" 2>/dev/null && grep -q '"command": "npx"' "$MCP_APPS_HOME/.claude/mcp.json"; then
  _pass "POST /mcp/apps/{app}/unprotect restores backup"
else
  _fail "POST /mcp/apps/{app}/unprotect failed: $MCP_UNPROTECT"
fi

if echo "$MCP_UNPROTECT" | grep -q "abc123XYZsecretToken"; then
  _fail "CRITICAL: raw secret value found in MCP app unprotect API"
else
  _pass "MCP app unprotect API does not contain raw secret value"
fi

echo ""
echo "--- Endpoint: /openai/v1/chat/completions ---"
OAI=$(curl -sf -X POST "$BASE/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"hello"}]}' 2>/dev/null)
if echo "$OAI" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['object'] == 'chat.completion'
assert d['choices'][0]['message']['role'] == 'assistant'
" 2>/dev/null; then
  _pass "POST /openai/v1/chat/completions → valid OpenAI-compat response"
else
  _fail "POST /openai/v1/chat/completions — unexpected response: $OAI"
fi

echo ""
echo "--- Endpoint: /anthropic/v1/messages ---"
ANT=$(curl -sf -X POST "$BASE/anthropic/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":[{"type":"text","text":"hello"}]}]}' 2>/dev/null)
if echo "$ANT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['type'] == 'message'
assert d['role'] == 'assistant'
assert d['content'][0]['type'] == 'text'
" 2>/dev/null; then
  _pass "POST /anthropic/v1/messages → valid Anthropic-compat response"
else
  _fail "POST /anthropic/v1/messages — unexpected response: $ANT"
fi

echo ""
echo "--- Endpoint: /local/v1/chat/completions ---"
LOCAL=$(curl -sf -X POST "$BASE/local/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","messages":[{"role":"user","content":"hello"}]}' 2>/dev/null)
if echo "$LOCAL" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['object'] == 'chat.completion'
assert d['model'] == 'local-model'
assert d['choices'][0]['message']['role'] == 'assistant'
" 2>/dev/null; then
  _pass "POST /local/v1/chat/completions → valid OpenAI-compat local response"
else
  _fail "POST /local/v1/chat/completions — unexpected response: $LOCAL"
fi

echo ""
echo "--- Endpoint: /providers/health ---"
PROVIDERS=$(curl -sf "$BASE/providers/health" 2>/dev/null)
if echo "$PROVIDERS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['live_checked'] is False
assert 'openai' in d['providers']
assert 'anthropic' in d['providers']
assert 'local' in d['providers']
assert d['providers']['openai']['api_key_configured'] is False
assert d['providers']['anthropic']['api_key_configured'] is False
assert d['providers']['local']['api_key_required'] is False
assert d['providers']['local']['status'] == 'configured'
runtimes={item['runtime_id']: item for item in d['local_runtimes']['runtimes']}
assert set(runtimes) == {'ollama','lm-studio','llama-cpp','vllm'}
assert d['local_runtimes']['summary']['total'] == 4
assert d['local_runtimes']['summary']['configured'] == 1
assert d['local_runtimes']['summary']['fallback'] == 0
assert d['local_runtimes']['summary']['live_checked'] is False
assert runtimes['ollama']['selected_config'] is True
assert runtimes['ollama']['status'] == 'configured'
assert all(item['api_key_required'] is False for item in runtimes.values())
assert all(item['fallback_config'] is False for item in runtimes.values())
" 2>/dev/null; then
  _pass "GET /providers/health → provider and local runtime config status without live check"
else
  _fail "GET /providers/health — unexpected response: $PROVIDERS"
fi

echo ""
echo "--- Endpoint: /providers/integrations ---"
ROUTING=$(curl -sf "$BASE/providers/integrations" 2>/dev/null)
if echo "$ROUTING" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['gateway_base_url'] == 'http://127.0.0.1:$PORT'
assert d['summary']['total'] == 3
assert d['summary']['missing'] == 1
assert d['summary']['unprotected'] == 2
assert d['summary']['actionable'] == 3
items={item['integration_id']: item for item in d['integrations']}
assert items['claude']['status'] == 'missing'
assert items['claude']['recommended_action'] == 'setup'
assert items['claude']['repair_available'] is True
assert items['codex']['status'] == 'unprotected'
assert items['codex']['recommended_action'] == 'setup'
assert items['codex']['repair_available'] is True
assert items['vscode']['status'] == 'unprotected'
assert items['vscode']['recommended_action'] == 'setup'
assert items['vscode']['repair_available'] is True
" 2>/dev/null; then
  _pass "GET /providers/integrations → provider routing setup status"
else
  _fail "GET /providers/integrations — unexpected response: $ROUTING"
fi

if echo "$ROUTING" | grep -q "spectrona-local-token"; then
  _fail "CRITICAL: local routing token found in provider integration status API"
else
  _pass "Provider integration status API does not contain routing token"
fi

echo ""
echo "--- Endpoint: /integrations ---"
INTEGRATIONS=$(curl -sf "$BASE/integrations" 2>/dev/null)
if echo "$INTEGRATIONS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['gateway_base_url'] == 'http://127.0.0.1:$PORT'
assert d['repo_root'] == '$ROOT'
assert d['home'].endswith('spectrona_gateway_mcp_apps_home_$$')
assert d['summary']['provider_total'] == 3
assert d['summary']['mcp_total'] >= 7
assert d['summary']['local_llm_total'] == 4
assert d['summary']['local_llm_configured'] == 1
assert d['summary']['local_llm_fallback'] == 0
assert d['summary']['provider_actionable'] == 3
assert d['summary']['mcp_actionable'] >= 1
providers={item['integration_id']: item for item in d['provider_routing']}
apps={item['app_id']: item for item in d['mcp_apps']}
local={item['runtime_id']: item for item in d['local_llms']}
assert providers['claude']['status'] == 'missing'
assert providers['codex']['status'] == 'unprotected'
assert providers['vscode']['status'] == 'unprotected'
assert apps['claude-code']['status'] == 'unprotected'
assert apps['claude-code']['recommended_action'] == 'protect'
assert set(local) == {'ollama','lm-studio','llama-cpp','vllm'}
assert local['ollama']['selected_config'] is True
assert d['local_llm_summary']['total'] == 4
" 2>/dev/null; then
  _pass "GET /integrations → aggregate provider, MCP, and local runtime integration status"
else
  _fail "GET /integrations — unexpected response: $INTEGRATIONS"
fi

if echo "$INTEGRATIONS" | grep -q "abc123XYZsecretToken\|spectrona-local-token"; then
  _fail "CRITICAL: raw secret or routing token found in aggregate integration status API"
else
  _pass "Aggregate integration status API does not contain raw secrets or routing token"
fi

INTEGRATIONS_REPAIR_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/integrations/repair" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$INTEGRATIONS_REPAIR_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /integrations/repair requires explicit confirm=true" \
  || _fail "POST /integrations/repair did not require confirmation (status=$INTEGRATIONS_REPAIR_NO_CONFIRM_STATUS)"

ROUTING_PROTECT_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/providers/integrations/codex/protect" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$ROUTING_PROTECT_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /providers/integrations/{id}/protect requires explicit confirm=true" \
  || _fail "POST /providers/integrations/{id}/protect did not require confirmation (status=$ROUTING_PROTECT_NO_CONFIRM_STATUS)"

CLAUDE_ROUTING_PROTECT=$(curl -sf -X POST "$BASE/providers/integrations/claude/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$CLAUDE_ROUTING_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'protect'
result=d['result']
assert result['integration_id'] == 'claude'
assert result['changed'] is True
assert result['before_status'] == 'missing'
assert result['after_status'] == 'protected'
" 2>/dev/null && grep -q "ANTHROPIC_BASE_URL=http://127.0.0.1:$PORT/anthropic" "$CLAUDE_ROUTING_ENV"; then
  _pass "POST /providers/integrations/{id}/protect creates Claude routing env"
else
  _fail "POST /providers/integrations/{id}/protect failed for Claude: $CLAUDE_ROUTING_PROTECT"
fi

CODEX_ROUTING_PROTECT=$(curl -sf -X POST "$BASE/providers/integrations/codex/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$CODEX_ROUTING_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'protect'
result=d['result']
assert result['integration_id'] == 'codex'
assert result['changed'] is True
assert result['before_status'] == 'unprotected'
assert result['after_status'] == 'protected'
assert result['backup_path'].endswith('.spectrona.bak')
" 2>/dev/null && grep -q 'model_providers.spectrona' "$CODEX_ROUTING_CONFIG" && [ -f "$CODEX_ROUTING_CONFIG.spectrona.bak" ]; then
  _pass "POST /providers/integrations/{id}/protect patches Codex routing config with backup"
else
  _fail "POST /providers/integrations/{id}/protect failed for Codex: $CODEX_ROUTING_PROTECT"
fi

VSCODE_ROUTING_PROTECT=$(curl -sf -X POST "$BASE/providers/integrations/vscode/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$VSCODE_ROUTING_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'protect'
result=d['result']
assert result['integration_id'] == 'vscode'
assert result['changed'] is True
assert result['before_status'] == 'unprotected'
assert result['after_status'] == 'protected'
assert result['backup_path'].endswith('.spectrona.bak')
" 2>/dev/null && python3 - "$VSCODE_ROUTING_SETTINGS" "$PORT" <<'PY' >/dev/null 2>&1
import json, sys
settings=json.load(open(sys.argv[1]))
port=sys.argv[2]
assert settings["editor.tabSize"] == 2
assert settings["spectrona.providerRouting"]["openaiBaseUrl"] == f"http://127.0.0.1:{port}/openai/v1"
assert settings["terminal.integrated.env.osx"]["OPENAI_BASE_URL"] == f"http://127.0.0.1:{port}/openai/v1"
assert settings["terminal.integrated.env.osx"]["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{port}/anthropic"
PY
then
  _pass "POST /providers/integrations/{id}/protect patches VS Code settings with backup"
else
  _fail "POST /providers/integrations/{id}/protect failed for VS Code: $VSCODE_ROUTING_PROTECT"
fi

if echo "$CLAUDE_ROUTING_PROTECT $CODEX_ROUTING_PROTECT $VSCODE_ROUTING_PROTECT" | grep -q "spectrona-local-token"; then
  _fail "CRITICAL: local routing token found in provider integration protect API"
else
  _pass "Provider integration protect API does not contain routing token"
fi

ROUTING_AFTER_PROTECT=$(curl -sf "$BASE/providers/integrations" 2>/dev/null)
if echo "$ROUTING_AFTER_PROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['summary']['protected'] == 3
assert d['summary']['actionable'] == 0
items={item['integration_id']: item for item in d['integrations']}
assert items['claude']['status'] == 'protected'
assert items['claude']['api_key_configured'] is True
assert items['codex']['status'] == 'protected'
assert items['codex']['backup_exists'] is True
assert items['vscode']['status'] == 'protected'
assert items['vscode']['backup_exists'] is True
assert items['vscode']['api_key_configured'] is True
" 2>/dev/null; then
  _pass "GET /providers/integrations reflects protected provider routing"
else
  _fail "GET /providers/integrations did not reflect protected routing: $ROUTING_AFTER_PROTECT"
fi

python3 - "$CODEX_ROUTING_CONFIG" "$PORT" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
port = sys.argv[2]
text = path.read_text().replace(
    f"http://127.0.0.1:{port}/openai/v1",
    "http://127.0.0.1:19999/openai/v1",
)
path.write_text(text)
PY

ROUTING_DRIFT=$(curl -sf "$BASE/providers/integrations" 2>/dev/null)
if echo "$ROUTING_DRIFT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['summary']['drifted'] == 1
items={item['integration_id']: item for item in d['integrations']}
codex=items['codex']
assert codex['status'] == 'partial'
assert codex['drift_detected'] is True
assert codex['recommended_action'] == 'repair'
assert codex['repair_available'] is True
" 2>/dev/null; then
  _pass "GET /providers/integrations detects provider routing drift"
else
  _fail "GET /providers/integrations did not detect routing drift: $ROUTING_DRIFT"
fi

CODEX_ROUTING_REPAIR=$(curl -sf -X POST "$BASE/providers/integrations/codex/protect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$CODEX_ROUTING_REPAIR" | python3 -c "
import json,sys
d=json.load(sys.stdin)
result=d['result']
assert result['integration_id'] == 'codex'
assert result['changed'] is True
assert result['before_status'] == 'partial'
assert result['after_status'] == 'protected'
" 2>/dev/null && grep -q "base_url = \"http://127.0.0.1:$PORT/openai/v1\"" "$CODEX_ROUTING_CONFIG"; then
  _pass "POST /providers/integrations/{id}/protect repairs provider routing drift"
else
  _fail "POST /providers/integrations/{id}/protect did not repair routing drift: $CODEX_ROUTING_REPAIR"
fi

CODEX_ROUTING_UNPROTECT=$(curl -sf -X POST "$BASE/providers/integrations/codex/unprotect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$CODEX_ROUTING_UNPROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'unprotect'
result=d['result']
assert result['integration_id'] == 'codex'
assert result['changed'] is True
assert result['before_status'] == 'protected'
assert result['after_status'] == 'unprotected'
" 2>/dev/null && grep -q 'existing = true' "$CODEX_ROUTING_CONFIG" && ! grep -q 'model_providers.spectrona' "$CODEX_ROUTING_CONFIG"; then
  _pass "POST /providers/integrations/{id}/unprotect removes Codex routing block"
else
  _fail "POST /providers/integrations/{id}/unprotect failed for Codex: $CODEX_ROUTING_UNPROTECT"
fi

VSCODE_ROUTING_UNPROTECT=$(curl -sf -X POST "$BASE/providers/integrations/vscode/unprotect" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$VSCODE_ROUTING_UNPROTECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'unprotect'
result=d['result']
assert result['integration_id'] == 'vscode'
assert result['changed'] is True
assert result['before_status'] == 'protected'
assert result['after_status'] == 'unprotected'
" 2>/dev/null && python3 - "$VSCODE_ROUTING_SETTINGS" <<'PY' >/dev/null 2>&1
import json, sys
settings=json.load(open(sys.argv[1]))
assert settings["editor.tabSize"] == 2
assert "spectrona.providerRouting" not in settings
assert "OPENAI_BASE_URL" not in settings.get("terminal.integrated.env.osx", {})
PY
then
  _pass "POST /providers/integrations/{id}/unprotect removes VS Code routing settings"
else
  _fail "POST /providers/integrations/{id}/unprotect failed for VS Code: $VSCODE_ROUTING_UNPROTECT"
fi

if echo "$CODEX_ROUTING_REPAIR $CODEX_ROUTING_UNPROTECT $VSCODE_ROUTING_UNPROTECT" | grep -q "spectrona-local-token"; then
  _fail "CRITICAL: local routing token found in provider integration mutation API"
else
  _pass "Provider integration mutation APIs do not contain routing token"
fi

INTEGRATIONS_REPAIR=$(curl -sf -X POST "$BASE/integrations/repair" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$INTEGRATIONS_REPAIR" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'repair'
assert d['summary']['provider_attempted'] >= 1
assert d['summary']['mcp_attempted'] >= 1
assert d['summary']['errors'] == 0
assert d['summary']['after']['provider_actionable'] == 0
assert d['summary']['after']['mcp_actionable'] == 0
provider_ids={item['integration_id'] for item in d['provider_results']}
mcp_ids={item['app_id'] for item in d['mcp_results']}
assert 'codex' in provider_ids
assert 'vscode' in provider_ids
assert 'claude-code' in mcp_ids
" 2>/dev/null && grep -q 'model_providers.spectrona' "$CODEX_ROUTING_CONFIG" && grep -q 'spectrona.providerRouting' "$VSCODE_ROUTING_SETTINGS" && grep -q '"command": "spectrona"' "$MCP_APPS_HOME/.claude/mcp.json"; then
  _pass "POST /integrations/repair repairs aggregate actionable integrations"
else
  _fail "POST /integrations/repair failed: $INTEGRATIONS_REPAIR"
fi

if echo "$INTEGRATIONS_REPAIR" | grep -q "abc123XYZsecretToken\|spectrona-local-token"; then
  _fail "CRITICAL: raw secret or routing token found in aggregate integration repair API"
else
  _pass "Aggregate integration repair API does not contain raw secrets or routing token"
fi

LOCAL_RUNTIME_SELECT_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/providers/local-runtimes/lm-studio/select" \
  -H "Content-Type: application/json" \
  -d '{}' 2>/dev/null)
[ "$LOCAL_RUNTIME_SELECT_NO_CONFIRM_STATUS" = "400" ] \
  && _pass "POST /providers/local-runtimes/{id}/select requires explicit confirm=true" \
  || _fail "POST /providers/local-runtimes/{id}/select did not require confirmation (status=$LOCAL_RUNTIME_SELECT_NO_CONFIRM_STATUS)"

LOCAL_RUNTIME_SELECT=$(curl -sf -X POST "$BASE/providers/local-runtimes/lm-studio/select" \
  -H "Content-Type: application/json" \
  -d '{"confirm":true}' 2>/dev/null)
if echo "$LOCAL_RUNTIME_SELECT" | python3 -c "
import json,pathlib,sys
d=json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['action'] == 'select_local_runtime'
result=d['result']
assert result['runtime_id'] == 'lm-studio'
assert result['changed'] is True
assert result['before_base_url'] == 'http://127.0.0.1:11434/v1'
assert result['after_base_url'] == 'http://127.0.0.1:1234/v1'
assert result['after_health_path'] == '/models'
config=pathlib.Path(result['config_path'])
backup=pathlib.Path(result['backup_path'])
assert config == pathlib.Path('$RUNTIME_CONFIG_FILE')
assert backup.exists()
assert 'http://127.0.0.1:1234/v1' in config.read_text()
assert 'http://127.0.0.1:11434/v1' in backup.read_text()
" 2>/dev/null; then
  _pass "POST /providers/local-runtimes/{id}/select updates Spectrona config with backup"
else
  _fail "POST /providers/local-runtimes/{id}/select failed: $LOCAL_RUNTIME_SELECT"
fi

PROVIDERS_AFTER_LOCAL_SELECT=$(curl -sf "$BASE/providers/health" 2>/dev/null)
if echo "$PROVIDERS_AFTER_LOCAL_SELECT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['providers']['local']['base_url'] == 'http://127.0.0.1:1234/v1'
runtimes={item['runtime_id']: item for item in d['local_runtimes']['runtimes']}
assert runtimes['lm-studio']['selected_config'] is True
assert runtimes['lm-studio']['status'] == 'configured'
assert runtimes['ollama']['selected_config'] is False
" 2>/dev/null; then
  _pass "GET /providers/health reflects selected local runtime without gateway restart"
else
  _fail "GET /providers/health did not reflect selected local runtime: $PROVIDERS_AFTER_LOCAL_SELECT"
fi

# ── DLP checks ────────────────────────────────────────────────────────────────

echo ""
echo "--- DLP: secret in request ---"
curl -sf -X POST "$BASE/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"key is sk-proj-abc123XYZsecrettoken9999"}]}' \
  >/dev/null 2>/dev/null || true

curl -sf -X POST "$BASE/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-spectrona-shell-risk: true" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"run shell command"}]}' \
  >/dev/null 2>/dev/null || true

sleep 0.3  # let audit write flush

if [ -f "$AUDIT_LOG" ]; then
  LINES_AFTER=$(wc -l < "$AUDIT_LOG")
else
  LINES_AFTER=0
fi
NEW_LINES=$((LINES_AFTER - LINES_BEFORE))

if [ "$NEW_LINES" -ge 5 ]; then
  _pass "audit log received >= 5 new events (new lines=$NEW_LINES)"
else
  _fail "audit log has too few new events (new lines=$NEW_LINES)"
fi

# Check that DLP request recorded dlp_findings_count >= 1
DLP_HIT=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines = [json.loads(l) for l in sys.stdin if l.strip()]
hits = [e for e in lines if e.get('dlp_findings_count', 0) >= 1]
print(len(hits))
" 2>/dev/null || echo 0)

if [ "$DLP_HIT" -ge 1 ]; then
  _pass "audit log records dlp_findings_count >= 1 for request containing secret"
else
  _fail "DLP hit not recorded in audit log"
fi

# Check audit log does NOT contain the raw secret value
if tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null | grep -q "abc123XYZsecrettoken"; then
  _fail "CRITICAL: raw secret value found in audit log"
else
  _pass "audit log does not contain raw secret value"
fi

echo ""
echo "--- Runtime events and token usage ---"
EVENTS=$(curl -sf "$BASE/events/recent?limit=10" 2>/dev/null)
if echo "$EVENTS" | python3 -c "
import json,sys
events=json.load(sys.stdin)
assert len(events) >= 4
assert all(e.get('event_type') == 'model_call' for e in events)
assert {'openai','anthropic','local'}.issubset({e.get('provider_type') for e in events})
assert any(e.get('policy_action') == 'redact' for e in events)
assert any(e.get('action') == 'redacted_then_mock_response' for e in events)
assert any(e.get('action') == 'blocked' for e in events)
" 2>/dev/null; then
  _pass "GET /events/recent → model call events with policy metadata"
else
  _fail "GET /events/recent — unexpected response: $EVENTS"
fi

if echo "$EVENTS" | grep -q "abc123XYZsecrettoken"; then
  _fail "CRITICAL: raw secret value found in runtime events"
else
  _pass "runtime events do not contain raw secret value"
fi

BLOCKS=$(curl -sf "$BASE/events/blocks?limit=10" 2>/dev/null)
if echo "$BLOCKS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['events'] >= 1
assert d['blocked'] >= 1
assert d['approval_required'] >= 0
assert any(item['key'] == 'deny-shell-risk' for item in d['by_rule'])
assert any(event['policy_action'] == 'deny' for event in d['recent'])
" 2>/dev/null; then
  _pass "GET /events/blocks → aggregates blocked and approval-required runtime events"
else
  _fail "GET /events/blocks — unexpected response: $BLOCKS"
fi

DLP_SUMMARY=$(curl -sf "$BASE/events/dlp?limit=10" 2>/dev/null)
if echo "$DLP_SUMMARY" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['events'] >= 1
assert d['findings'] >= 1
assert d['redacted_events'] >= 1
assert any(item['key'] == 'openai' for item in d['by_provider'])
assert any(event['policy_action'] == 'redact' for event in d['recent'])
" 2>/dev/null; then
  _pass "GET /events/dlp → aggregates DLP findings without payload content"
else
  _fail "GET /events/dlp — unexpected response: $DLP_SUMMARY"
fi

if echo "$DLP_SUMMARY" | grep -q "abc123XYZsecrettoken"; then
  _fail "CRITICAL: raw secret value found in DLP summary API"
else
  _pass "DLP summary API does not contain raw secret value"
fi

USAGE=$(curl -sf "$BASE/events/token-usage" 2>/dev/null)
if echo "$USAGE" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d['events'] >= 4
assert d['request_tokens'] >= 40
assert d['response_tokens'] >= 40
assert d['total_tokens'] >= 80
assert d['today']['events'] >= 4
assert d['today']['total_tokens'] >= 80
providers={item['key']: item for item in d['by_provider']}
assert {'openai','anthropic','local'}.issubset(providers)
models={item['key']: item for item in d['by_model']}
assert {'gpt-4','claude-sonnet-4-6','local-model'}.issubset(models)
routes={item['key']: item for item in d['by_route']}
assert {'/openai/v1/chat/completions','/anthropic/v1/messages','/local/v1/chat/completions'}.issubset(routes)
assert d['by_client'] and d['by_client'][0]['total_tokens'] > 0
assert d['by_day'] and d['by_day'][0]['events'] >= 4
" 2>/dev/null; then
  _pass "GET /events/token-usage → aggregates day/route/provider/model/client token usage"
else
  _fail "GET /events/token-usage — unexpected response: $USAGE"
fi

if echo "$USAGE" | grep -q "abc123XYZsecrettoken"; then
  _fail "CRITICAL: raw secret value found in token usage API"
else
  _pass "Token usage API does not contain raw secret value"
fi

echo ""
echo "--- Runtime policy: gateway enforcement ---"
if python3 "$ROOT/spectrona-gateway/validation/policy_gateway_validate.py" >/dev/null 2>&1; then
  _pass "Gateway policy enforcement handles allow, deny, redact, and require_approval"
else
  _fail "Gateway policy enforcement validation failed"
fi

if python3 "$ROOT/spectrona-gateway/validation/policy_dry_run_validate.py" >/dev/null 2>&1; then
  _pass "Gateway policy dry-run records would-block/redact/approval without enforcing"
else
  _fail "Gateway policy dry-run validation failed"
fi

if PYTHONPATH="$RUNTIME_PYTHONPATH" python3 "$ROOT/spectrona-gateway/validation/local_llm_discovery_validate.py" >/dev/null 2>&1; then
  _pass "Local LLM discovery detects Ollama, LM Studio, llama.cpp, and vLLM fake upstreams"
else
  _fail "Local LLM discovery validation failed"
fi

if PYTHONPATH="$RUNTIME_PYTHONPATH" python3 "$ROOT/spectrona-gateway/validation/local_fallback_validate.py" >/dev/null 2>&1; then
  _pass "Local LLM fallback routing retries selected runtime failures through configured local fallback"
else
  _fail "Local LLM fallback routing validation failed"
fi

echo ""
echo "--- Live passthrough: fake upstream ---"
if python3 "$ROOT/spectrona-gateway/validation/passthrough_fake_upstream.py" >/dev/null 2>&1; then
  _pass "OpenAI, Anthropic, and local passthrough/live health checks forward to configured upstreams with response-side DLP"
else
  _fail "OpenAI/Anthropic/local passthrough/live health/response-DLP validation failed"
fi

echo ""
echo "=== Phase 2 Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
