#!/usr/bin/env bash
# Phase 2 validation — runtime-guard

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_SRC="$ROOT/runtime-guard/src"
POLICY_SRC="$ROOT/policy-engine/src"
DETECTION_SRC="$ROOT/spectrona-detection/src"
PYTHONPATH_VALUE="$DETECTION_SRC:$RUNTIME_SRC:$POLICY_SRC"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

check() {
  [ -e "$2" ] && _pass "$1" || _fail "$1 — missing: $2"
}

echo ""
echo "=== Phase 2 Validation: runtime-guard ==="
echo ""

echo "--- Scaffold ---"
check "pyproject.toml" "$ROOT/runtime-guard/pyproject.toml"
check "runtime_guard package" "$ROOT/runtime-guard/src/runtime_guard/__init__.py"
check "mcp_proxy.py" "$ROOT/runtime-guard/src/runtime_guard/mcp_proxy.py"
check "mcp_config.py" "$ROOT/runtime-guard/src/runtime_guard/mcp_config.py"
check "mcp_apps.py" "$ROOT/runtime-guard/src/runtime_guard/mcp_apps.py"
check "redaction.py" "$ROOT/runtime-guard/src/runtime_guard/redaction.py"
check "mcp proxy validator" "$ROOT/runtime-guard/validation/mcp_proxy_validate.py"
check "mcp config wrap validator" "$ROOT/runtime-guard/validation/mcp_config_wrap_validate.py"
check "mcp app discovery validator" "$ROOT/runtime-guard/validation/mcp_apps_validate.py"
check "mcp app protect validator" "$ROOT/runtime-guard/validation/mcp_apps_protect_validate.py"

echo ""
echo "--- Imports and static compile ---"
if PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache_runtime_guard PYTHONPATH="$PYTHONPATH_VALUE" \
  python3 -m py_compile \
    "$ROOT/runtime-guard/src/runtime_guard/mcp_proxy.py" \
    "$ROOT/runtime-guard/src/runtime_guard/mcp_config.py" \
    "$ROOT/runtime-guard/src/runtime_guard/mcp_apps.py" \
    "$ROOT/runtime-guard/src/runtime_guard/redaction.py" \
    "$ROOT/runtime-guard/validation/mcp_proxy_validate.py" \
    "$ROOT/runtime-guard/validation/mcp_config_wrap_validate.py" \
    "$ROOT/runtime-guard/validation/mcp_apps_validate.py" \
    "$ROOT/runtime-guard/validation/mcp_apps_protect_validate.py" 2>/dev/null; then
  _pass "runtime-guard modules compile"
else
  _fail "runtime-guard modules failed to compile"
fi

if PYTHONPATH="$PYTHONPATH_VALUE" python3 -c "import runtime_guard.mcp_proxy, policy_engine" 2>/dev/null; then
  _pass "runtime_guard.mcp_proxy and policy_engine importable"
else
  _fail "runtime_guard.mcp_proxy or policy_engine not importable"
fi

echo ""
echo "--- MCP proxy behavior ---"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/runtime-guard/validation/mcp_proxy_validate.py" >/dev/null 2>&1; then
  _pass "MCP proxy defaults to dry-run, explicit enforcement blocks/redacts/requires approval, and audits metadata"
else
  _fail "MCP proxy behavior validation failed"
fi

echo ""
echo "--- MCP config wrapping ---"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/runtime-guard/validation/mcp_config_wrap_validate.py" >/dev/null 2>&1; then
  _pass "MCP config wrapper rewrites servers, avoids double wrapping, applies backups, and restores undo state"
else
  _fail "MCP config wrapping validation failed"
fi

echo ""
echo "--- MCP app discovery ---"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/runtime-guard/validation/mcp_apps_validate.py" >/dev/null 2>&1; then
  _pass "MCP app discovery reports missing, invalid, unprotected, protected, and partial states without raw secrets"
else
  _fail "MCP app discovery validation failed"
fi

echo ""
echo "--- MCP app protect/unprotect ---"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/runtime-guard/validation/mcp_apps_protect_validate.py" >/dev/null 2>&1; then
  _pass "MCP app protect/unprotect wraps detected configs, repairs partial configs, restores backups, and reports metadata only"
else
  _fail "MCP app protect/unprotect validation failed"
fi

echo ""
echo "--- MCP proxy CLI module ---"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 -m runtime_guard.mcp_proxy --help 2>/dev/null | grep -q "Spectrona MCP stdio proxy"; then
  _pass "python -m runtime_guard.mcp_proxy --help works"
else
  _fail "runtime_guard.mcp_proxy module help failed"
fi

echo ""
echo "=== Phase 2 Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
