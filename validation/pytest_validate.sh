#!/usr/bin/env bash
# Pytest validation — remediation regression suite.

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHONPATH_VALUE="$ROOT/spectrona-detection/src:$ROOT/mcp-inspector/src:$ROOT/policy-engine/src:$ROOT/runtime-guard/src:$ROOT/spectrona-gateway/src:$ROOT/spectrona-cli/src"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo ""
echo "=== Pytest Validation: regression suite ==="
echo ""

if PYTHONPATH="$PYTHONPATH_VALUE" python3 -m pytest --version >/dev/null 2>&1; then
  _pass "pytest is installed"
else
  _fail "pytest is not installed; install pytest before running the regression suite"
fi

if [ "$FAIL" -eq 0 ] && PYTHONPATH="$PYTHONPATH_VALUE" python3 -m pytest -q; then
  _pass "pytest regression suite passes"
else
  _fail "pytest regression suite failed"
fi

echo ""
echo "=== Pytest Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
