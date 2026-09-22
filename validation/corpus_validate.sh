#!/usr/bin/env bash
# Corpus benchmark validation — R8 precision gate.

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHONPATH_VALUE="$ROOT/spectrona-detection/src:$ROOT/mcp-inspector/src"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo ""
echo "=== Corpus Benchmark Validation ==="
echo ""

[ -f "$ROOT/validation/corpus_benchmark.py" ] \
  && _pass "corpus benchmark exists" \
  || _fail "corpus benchmark missing"

[ -f "$ROOT/validation/corpus/mcp_configs_seed.jsonl" ] \
  && _pass "redacted seed corpus exists" \
  || _fail "redacted seed corpus missing"

[ -f "$ROOT/validation/harvest_mcp_corpus.py" ] \
  && _pass "GitHub harvest helper exists" \
  || _fail "GitHub harvest helper missing"

[ -f "$ROOT/validation/corpus_label_queue.py" ] \
  && _pass "labeling queue helper exists" \
  || _fail "labeling queue helper missing"

[ -f "$ROOT/validation/corpus_promote_labeled.py" ] \
  && _pass "labeled corpus promotion helper exists" \
  || _fail "labeled corpus promotion helper missing"

if PYTHONPATH="$PYTHONPATH_VALUE" python3 -m py_compile \
  "$ROOT/validation/corpus_benchmark.py" \
  "$ROOT/validation/harvest_mcp_corpus.py" \
  "$ROOT/validation/corpus_label_queue.py" \
  "$ROOT/validation/corpus_promote_labeled.py" >/dev/null 2>&1; then
  _pass "corpus scripts compile"
else
  _fail "corpus scripts failed to compile"
fi

if PYTHONPATH="$PYTHONPATH_VALUE" python3 -c "
import sys
sys.path.insert(0, '$ROOT/validation')
import harvest_mcp_corpus
queries = harvest_mcp_corpus._queries(None)
assert len(queries) >= 5
assert any('@modelcontextprotocol' in query for query in queries)
assert any('uvx' in query for query in queries)
assert any('npx' in query for query in queries)
" >/dev/null 2>&1; then
  _pass "harvester defaults fan out across common MCP query shapes"
else
  _fail "harvester default query coverage failed"
fi

if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/validation/corpus_benchmark.py" --min-size 374 >/dev/null 2>&1; then
  _pass "reviewed corpus precision benchmark passes 95% gate"
else
  _fail "reviewed corpus precision benchmark failed"
fi

if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/validation/corpus_benchmark.py" --json --min-size 374 | python3 -c "
import json, sys
data=json.load(sys.stdin)
assert data['corpus_cases'] >= 374
assert not data['failed_rules']
for rule in data['rules'].values():
    if rule['precision'] is not None:
        assert rule['precision'] >= 0.95
" >/dev/null 2>&1; then
  _pass "benchmark JSON reports per-rule precision above threshold"
else
  _fail "benchmark JSON contract failed"
fi

QUEUE_TMP="$(mktemp "${TMPDIR:-/tmp}/spectrona_label_queue.XXXXXX.jsonl")"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/validation/corpus_label_queue.py" \
  --input "$ROOT/validation/corpus/mcp_configs_seed.jsonl" \
  --output "$QUEUE_TMP" \
  --sample-size 6 \
  --json | python3 -c "
import json, sys
data=json.load(sys.stdin)
assert data['input_records'] >= 10
assert 1 <= data['queued_records'] <= 6
assert data['strata']
" >/dev/null 2>&1 \
  && python3 -c "
import json, sys
path=sys.argv[1]
rows=[json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
assert rows
for row in rows:
    assert 'predicted_finding_ids' in row
    assert 'scanner_findings' in row
    assert row.get('label_notes', '').startswith('UNLABELED')
" "$QUEUE_TMP" >/dev/null 2>&1; then
  _pass "labeling queue helper writes redacted review records"
else
  _fail "labeling queue helper contract failed"
fi
rm -f "$QUEUE_TMP"

PROMOTE_TMP="$(mktemp "${TMPDIR:-/tmp}/spectrona_promote_queue.XXXXXX.jsonl")"
PROMOTED_TMP="$(mktemp "${TMPDIR:-/tmp}/spectrona_promoted.XXXXXX.jsonl")"
if PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/validation/corpus_label_queue.py" \
  --input "$ROOT/validation/corpus/mcp_configs_seed.jsonl" \
  --output "$PROMOTE_TMP" \
  --sample-size 3 >/dev/null 2>&1 \
  && ! PYTHONPATH="$PYTHONPATH_VALUE" python3 "$ROOT/validation/corpus_promote_labeled.py" \
  --input "$PROMOTE_TMP" \
  --output "$PROMOTED_TMP" >/dev/null 2>&1; then
  _pass "promotion helper rejects unlabeled queue records"
else
  _fail "promotion helper accepted unlabeled queue records"
fi
rm -f "$PROMOTE_TMP" "$PROMOTED_TMP"

if grep -R -q "REALSECRETVALUE123456\|SuperSecret123\|sk_live_51H8xYzAbCdEfGhIjKlMnOp" "$ROOT/validation/corpus"; then
  _fail "corpus contains raw review secret samples"
else
  _pass "corpus excludes raw review secret samples"
fi

echo ""
echo "=== Corpus Benchmark Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
