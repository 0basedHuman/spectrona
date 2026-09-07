#!/usr/bin/env bash
# Master validation gate — Spectrona
# Runs all phase validation scripts in sequence.
# Exit code 0 = all active phases pass.
# Exit code 1 = one or more active phases fail.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OVERALL_FAIL=0

run_phase() {
  local label="$1"
  local script="$2"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Running: $label"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if bash "$ROOT/$script"; then
    echo ""
    echo "  → $label: OK"
  else
    echo ""
    echo "  → $label: FAILED"
    OVERALL_FAIL=1
  fi
}

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Spectrona — validate_all.sh        ║"
echo "╚════════════════════════════════════════╝"

run_phase "Pytest: regression suite"      "validation/pytest_validate.sh"
run_phase "Corpus: precision benchmark"   "validation/corpus_validate.sh"
run_phase "Phase 1: mcp-inspector"        "mcp-inspector/validation/phase1_validate.sh"
run_phase "Policy Engine"                 "policy-engine/validation/policy_validate.sh"
run_phase "Phase 2: spectrona-gateway"    "spectrona-gateway/validation/phase2_gateway_validate.sh"
run_phase "Dashboard: browser render"      "spectrona-gateway/validation/dashboard_browser_validate.sh"
run_phase "Phase 2C: spectrona-cli"       "spectrona-cli/validation/phase2_cli_validate.sh"
run_phase "Packaging: Homebrew layout"    "packaging/validate_packaging.sh"
run_phase "Phase 3A: memory routes"       "spectrona-gateway/validation/phase3_memory_routes_validate.sh"
run_phase "Runtime Guard: MCP proxy"       "runtime-guard/validation/phase2_validate.sh"
run_phase "Phase 3: ClaudeDB"             "claudedb/validation/phase3_validate.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$OVERALL_FAIL" -eq 0 ]; then
  echo "  OVERALL RESULT: PASS"
else
  echo "  OVERALL RESULT: FAIL"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit $OVERALL_FAIL
