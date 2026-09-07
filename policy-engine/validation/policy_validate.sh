#!/usr/bin/env bash
# Policy engine validation — parser, matcher, decisions, fixtures.

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
POLICY_SRC="$ROOT/policy-engine/src"
POLICIES="$ROOT/policy-engine/examples/policies"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

check() {
  [ -e "$2" ] && _pass "$1" || _fail "$1 — missing: $2"
}

echo ""
echo "=== Policy Engine Validation ==="
echo ""

echo "--- Scaffold ---"
check "pyproject.toml" "$ROOT/policy-engine/pyproject.toml"
check "policy_engine package" "$POLICY_SRC/policy_engine"
check "models.py" "$POLICY_SRC/policy_engine/models.py"
check "loader.py" "$POLICY_SRC/policy_engine/loader.py"
check "engine.py" "$POLICY_SRC/policy_engine/engine.py"
check "defaults.py" "$POLICY_SRC/policy_engine/defaults.py"
check "presets.py" "$POLICY_SRC/policy_engine/presets.py"
check "default policy fixture" "$POLICIES/default-policy.yaml"
check "deny policy fixture" "$POLICIES/deny-client-policy.yaml"
check "redact policy fixture" "$POLICIES/redact-openai-policy.yaml"
check "approval policy fixture" "$POLICIES/approval-shell-policy.yaml"

echo ""
echo "--- Static compile ---"
if PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache python3 -m py_compile \
  "$POLICY_SRC/policy_engine/__init__.py" \
  "$POLICY_SRC/policy_engine/models.py" \
  "$POLICY_SRC/policy_engine/loader.py" \
  "$POLICY_SRC/policy_engine/engine.py" \
  "$POLICY_SRC/policy_engine/defaults.py" \
  "$POLICY_SRC/policy_engine/presets.py" 2>/dev/null; then
  _pass "policy engine modules compile"
else
  _fail "policy engine modules failed to compile"
fi

echo ""
echo "--- Behavior ---"
if PYTHONPATH="$POLICY_SRC" python3 - <<PY
from pathlib import Path
from policy_engine import PolicyContext, PolicyEngine, list_policy_presets, load_policy, load_policy_text

policies = Path("$POLICIES")

default_engine = PolicyEngine(load_policy(policies / "default-policy.yaml"))
assert default_engine.evaluate(PolicyContext(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-4",
    client="codex",
)).action == "allow"
assert default_engine.evaluate(PolicyContext(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-4",
    client="codex",
    dlp_findings_count=1,
)).action == "redact"
assert default_engine.evaluate(PolicyContext(
    route="/mcp/tools/call",
    provider_type="mcp",
    client="claude",
    shell_risk=True,
)).action == "deny"
assert default_engine.evaluate(PolicyContext(
    route="/mcp/tools/call",
    provider_type="mcp",
    client="claude",
    filesystem_risk=True,
)).action == "deny"

deny_engine = PolicyEngine(load_policy(policies / "deny-client-policy.yaml"))
deny = deny_engine.evaluate(PolicyContext(
    route="/anthropic/v1/messages",
    provider_type="anthropic",
    model="claude-sonnet-4-6",
    client="blocked-client",
))
assert deny.action == "deny"
assert deny.rule_id == "deny-blocked-client"

redact_engine = PolicyEngine(load_policy(policies / "redact-openai-policy.yaml"))
assert redact_engine.evaluate(PolicyContext(
    route="/openai/v1/chat/completions",
    provider_type="openai",
    model="gpt-4",
    client="codex",
    dlp_findings_count=1,
)).action == "redact"
assert redact_engine.evaluate(PolicyContext(
    route="/anthropic/v1/messages",
    provider_type="anthropic",
    model="claude",
    client="claude",
    dlp_findings_count=1,
)).action == "allow"

approval_engine = PolicyEngine(load_policy(policies / "approval-shell-policy.yaml"))
approval = approval_engine.evaluate(PolicyContext(
    route="/mcp/tools/call",
    provider_type="mcp",
    client="vscode",
    shell_risk=True,
))
assert approval.action == "require_approval"
assert approval.rule_id == "require-shell-approval"

presets = {preset.id: preset for preset in list_policy_presets()}
assert set(presets) == {"relaxed", "balanced", "strict"}
for preset in presets.values():
    policy = load_policy_text(preset.text)
    decision = PolicyEngine(policy).evaluate(PolicyContext(
        route="/openai/v1/chat/completions",
        provider_type="openai",
        model="gpt-4",
        client="codex",
    ))
    assert decision.action in {"allow", "deny", "redact", "require_approval"}
PY
then
  _pass "allow, deny, redact, require_approval, and policy presets work"
else
  _fail "policy decision behavior failed"
fi

if PYTHONPATH="$POLICY_SRC" python3 - <<'PY'
from policy_engine import load_policy_text

bad_policies = [
    (
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: empty-match\n"
        "    action: deny\n",
        "non-empty match",
    ),
    (
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: typo-key\n"
        "    action: deny\n"
        "    match:\n"
        "      shel_risk: true\n",
        "Unknown match key",
    ),
    (
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: string-bool\n"
        "    action: deny\n"
        "    match:\n"
        "      shell_risk: yes\n",
        "true or false",
    ),
]

for text, expected in bad_policies:
    try:
        load_policy_text(text)
    except ValueError as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("invalid policy loaded successfully")
PY
then
  _pass "invalid policies fail at load time"
else
  _fail "invalid policy schema validation failed"
fi

echo ""
echo "=== Policy Engine Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
