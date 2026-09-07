#!/usr/bin/env bash
# Phase 3 validation — memory HTTP routes
# Starts gateway, tests POST/GET /memory/items, verifies DLP safety.

set -euo pipefail

PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GATEWAY_SRC="$ROOT/spectrona-gateway/src"
POLICY_SRC="$ROOT/policy-engine/src"
DETECTION_SRC="$ROOT/spectrona-detection/src"
RUNTIME_PYTHONPATH="$DETECTION_SRC:$GATEWAY_SRC:$POLICY_SRC"
PORT=19002
BASE="http://127.0.0.1:$PORT"
AUTH_TOKEN="phase3-memory-auth-token"
GW_PID=""
TEST_DB="/tmp/spectrona_mem_validate_$$.db"
TEST_KEY="/tmp/spectrona_mem_validate_$$.key"

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
curl() { command curl -H "Authorization: Bearer $AUTH_TOKEN" "$@"; }

_cleanup() {
  [ -n "$GW_PID" ] && kill "$GW_PID" 2>/dev/null && wait "$GW_PID" 2>/dev/null || true
  rm -f "$TEST_DB" "$TEST_KEY"
}
trap _cleanup EXIT

echo ""
echo "=== Phase 3 Validation: memory HTTP routes ==="
echo ""

# ── Scaffold check ────────────────────────────────────────────────────────────

echo "--- Scaffold ---"
[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/routes/memory.py" ] \
  && _pass "routes/memory.py exists" \
  || { _fail "routes/memory.py missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/validation/memory_runtime_validate.py" ] \
  && _pass "memory_runtime_validate.py exists" \
  || { _fail "memory_runtime_validate.py missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/staleness.py" ] \
  && _pass "memory staleness helper exists" \
  || { _fail "memory staleness helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/context.py" ] \
  && _pass "memory context package helper exists" \
  || { _fail "memory context package helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/timeline.py" ] \
  && _pass "memory timeline helper exists" \
  || { _fail "memory timeline helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/compact.py" ] \
  && _pass "memory compaction helper exists" \
  || { _fail "memory compaction helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/sessions.py" ] \
  && _pass "memory session extraction helper exists" \
  || { _fail "memory session extraction helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/replay.py" ] \
  && _pass "memory session replay helper exists" \
  || { _fail "memory session replay helper missing"; exit 1; }

[ -f "$ROOT/spectrona-gateway/src/spectrona_gateway/memory/protection.py" ] \
  && _pass "memory storage protection helper exists" \
  || { _fail "memory storage protection helper missing"; exit 1; }

# ── Start gateway ─────────────────────────────────────────────────────────────

echo ""
echo "--- Starting gateway (port $PORT, isolated DB) ---"

AUDIT_LOG=$(python3 -c "
import os; from pathlib import Path
print(Path(os.getenv('SPECTRONA_LOG_DIR', str(Path.home() / '.spectrona' / 'logs'))) / 'audit.jsonl')
")
LINES_BEFORE=$(wc -l < "$AUDIT_LOG" 2>/dev/null || echo 0)

PYTHONPATH="$RUNTIME_PYTHONPATH" \
SPECTRONA_MOCK_MODE=true \
SPECTRONA_PORT=$PORT \
SPECTRONA_GATEWAY_AUTH_TOKEN="$AUTH_TOKEN" \
SPECTRONA_DB_PATH="$TEST_DB" \
SPECTRONA_MEMORY_ENCRYPTION_KEY_PATH="$TEST_KEY" \
  python3 -m uvicorn spectrona_gateway.app:app \
  --host 127.0.0.1 --port $PORT --log-level error &
GW_PID=$!

for i in $(seq 1 16); do
  sleep 0.5
  curl -sf "$BASE/health" >/dev/null 2>&1 && break
  [ "$i" -eq 16 ] && { _fail "gateway did not start within 8s"; exit 1; }
done
_pass "gateway started"

# ── POST normal item ──────────────────────────────────────────────────────────

echo ""
echo "--- POST /memory/items (normal content) ---"
RESP=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","source_tool":"codex","memory_type":"project_decision","content":"decided to use Python for Phase 1","importance_score":0.8,"tags":["phase1","python"]}')

ITEM_ID=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
DLP_COUNT=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['dlp_findings_count'])" 2>/dev/null || echo "99")

[ -n "$ITEM_ID" ] && _pass "POST returns item id" || _fail "POST did not return item id"
[ "$DLP_COUNT" -eq 0 ] && _pass "POST dlp_findings_count=0 for clean content" \
  || _fail "POST unexpected dlp_findings_count=$DLP_COUNT"

if RESP="$RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["RESP"])
assert d["raw_storage_mode"] == "redacted"
assert d["raw_storage_reason"] == "redacted_by_default"
assert d["raw_content_stored"] is False
assert d["encrypted_content_stored"] is False
PY
then
  _pass "POST defaults to redacted raw memory storage"
else
  _fail "POST raw memory storage defaults invalid"
fi

# ── GET — confirm item returned ───────────────────────────────────────────────

echo ""
echo "--- GET /memory/items ---"
GET_RESP=$(curl -sf "$BASE/memory/items?project_path=/validate/project" 2>/dev/null)
RETURNED_COUNT=$(echo "$GET_RESP" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
[ "$RETURNED_COUNT" -ge 1 ] && _pass "GET returns >= 1 item" \
  || _fail "GET returned no items (count=$RETURNED_COUNT)"

if ITEM_ID="$ITEM_ID" GET_RESP="$GET_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["GET_RESP"])
item=next(item for item in items if item["id"] == os.environ["ITEM_ID"])
assert item["source_tool"] == "codex"
assert set(item["tags"]) == {"phase1", "python"}
assert item["pinned"] is False
assert item["redacted"] is False
assert item["raw_storage_mode"] == "redacted"
assert item["raw_content_stored"] is False
assert item["encrypted_content_stored"] is False
PY
then
  _pass "GET returns memory metadata, tags, pinned, redacted state, and storage mode"
else
  _fail "GET memory metadata fields invalid"
fi

EVENTS_RESP=$(curl -sf "$BASE/memory/events?item_id=$ITEM_ID&limit=20" 2>/dev/null)
if ITEM_ID="$ITEM_ID" EVENTS_RESP="$EVENTS_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
events=json.loads(os.environ["EVENTS_RESP"])
assert any(event["item_id"] == os.environ["ITEM_ID"] and event["event_type"] == "created" for event in events)
assert all(isinstance(event["details"], dict) for event in events)
PY
then
  _pass "GET /memory/events returns created item event metadata"
else
  _fail "GET /memory/events item event metadata invalid"
fi

SEARCH_RESP=$(curl -sf "$BASE/memory/items?project_path=/validate/project&q=python&tag=phase1&source_tool=codex" 2>/dev/null)
SEARCH_COUNT=$(echo "$SEARCH_RESP" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
[ "$SEARCH_COUNT" -ge 1 ] && _pass "GET /memory/items search filters by redacted content, tag, and source tool" \
  || _fail "GET /memory/items search/filter returned no items"

# ── Stale context detection ──────────────────────────────────────────────────

echo ""
echo "--- GET /memory/items — stale context metadata ---"
STALE_CREATE=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","source_tool":"codex","memory_type":"user_preference","content":"legacy stale validation preference","importance_score":0.6,"tags":["runtime"]}')
STALE_ID=$(echo "$STALE_CREATE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
if TEST_DB="$TEST_DB" STALE_ID="$STALE_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
from datetime import datetime, timedelta, timezone
old=(datetime.now(timezone.utc)-timedelta(days=45)).isoformat()
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    conn.execute("UPDATE memory_items SET updated_at=? WHERE id=?", (old, os.environ["STALE_ID"]))
PY
then
  STALE_GET=$(curl -sf "$BASE/memory/items?project_path=/validate/project&q=legacy&limit=10" 2>/dev/null)
else
  STALE_GET="[]"
fi
if STALE_ID="$STALE_ID" STALE_GET="$STALE_GET" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["STALE_GET"])
item=next(item for item in items if item["id"] == os.environ["STALE_ID"])
assert item["stale"] is True
assert item["stale_reason"] == "older_than_30_days"
assert item["age_days"] >= 40
assert item["stale_after_days"] == 30
assert item["last_attached_at"] is None
PY
then
  _pass "GET /memory/items exposes stale context detection metadata"
else
  _fail "GET /memory/items stale context metadata invalid"
fi

# ── POST item with secret ─────────────────────────────────────────────────────

echo ""
echo "--- POST /memory/items (content contains secret) ---"
SECRET_RESP=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","memory_type":"risk_finding","content":"found sk-proj-abc123XYZsecrettoken9999 in config"}')

SEC_DLP=$(echo "$SECRET_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['dlp_findings_count'])" 2>/dev/null || echo 0)
SECRET_ID=$(echo "$SECRET_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
[ "$SEC_DLP" -ge 1 ] && _pass "POST dlp_findings_count >= 1 for secret content" \
  || _fail "POST did not detect secret (dlp_findings_count=$SEC_DLP)"

if SECRET_RESP="$SECRET_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["SECRET_RESP"])
assert d["raw_storage_mode"] == "redacted"
assert d["raw_storage_reason"] == "redacted_by_default"
assert d["raw_content_stored"] is False
assert d["encrypted_content_stored"] is False
PY
then
  _pass "POST secret memory defaults to redacted storage"
else
  _fail "POST secret memory storage metadata invalid"
fi

if TEST_DB="$TEST_DB" SECRET_ID="$SECRET_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    row=conn.execute(
        "SELECT content, redacted_content, encrypted_content, raw_storage_mode, raw_storage_reason FROM memory_items WHERE id=?",
        (os.environ["SECRET_ID"],),
    ).fetchone()
assert row is not None
content, redacted, encrypted, mode, reason = row
assert "abc123XYZsecrettoken" not in (content or "")
assert "abc123XYZsecrettoken" not in (redacted or "")
assert "abc123XYZsecrettoken" not in (encrypted or "")
assert "REDACTED_SECRET" in (content or "")
assert mode == "redacted"
assert reason == "redacted_by_default"
assert encrypted in (None, "")
PY
then
  _pass "SQLite memory content does not store raw secret by default"
else
  _fail "SQLite memory content stored raw secret by default"
fi

ENC_RESP=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","memory_type":"risk_finding","content":"encrypt sk-proj-abc123XYZencryptedtoken9999 in local memory","raw_storage_mode":"encrypted"}')
ENC_ID=$(echo "$ENC_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")

if ENC_RESP="$ENC_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["ENC_RESP"])
assert d["raw_storage_mode"] == "encrypted"
assert d["raw_storage_reason"] == "encrypted_raw_content"
assert d["raw_content_stored"] is False
assert d["encrypted_content_stored"] is True
assert d["dlp_findings_count"] >= 1
PY
then
  _pass "POST encrypted raw memory stores encrypted metadata"
else
  _fail "POST encrypted raw memory metadata invalid"
fi

if TEST_DB="$TEST_DB" ENC_ID="$ENC_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    row=conn.execute(
        "SELECT content, redacted_content, encrypted_content, raw_storage_mode FROM memory_items WHERE id=?",
        (os.environ["ENC_ID"],),
    ).fetchone()
assert row is not None
content, redacted, encrypted, mode = row
assert mode == "encrypted"
assert encrypted and encrypted.startswith("spectrona:v1:")
for value in (content, redacted, encrypted):
    assert "abc123XYZencryptedtoken" not in (value or "")
assert "REDACTED_SECRET" in (content or "")
PY
then
  _pass "SQLite encrypted memory keeps raw secret out of plaintext columns"
else
  _fail "SQLite encrypted memory leaked raw secret"
fi

if PYTHONPATH="$RUNTIME_PYTHONPATH" TEST_DB="$TEST_DB" ENC_ID="$ENC_ID" SPECTRONA_MEMORY_ENCRYPTION_KEY_PATH="$TEST_KEY" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
from spectrona_gateway.memory.protection import decrypt_text
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    encrypted=conn.execute(
        "SELECT encrypted_content FROM memory_items WHERE id=?",
        (os.environ["ENC_ID"],),
    ).fetchone()[0]
plaintext=decrypt_text(encrypted)
assert "encrypt sk-proj-abc123XYZencryptedtoken9999 in local memory" == plaintext
PY
then
  _pass "Encrypted memory content decrypts with local memory key"
else
  _fail "Encrypted memory content failed local decrypt round-trip"
fi

PLAIN_RESP=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","memory_type":"risk_finding","content":"try plaintext sk-proj-abc123XYZplaintexttoken9999 in local memory","raw_storage_mode":"plaintext"}')
PLAIN_ID=$(echo "$PLAIN_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")

if PLAIN_RESP="$PLAIN_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["PLAIN_RESP"])
assert d["raw_storage_mode"] == "redacted"
assert d["raw_storage_reason"] == "plaintext_requires_explicit_policy"
assert d["raw_content_stored"] is False
assert d["encrypted_content_stored"] is False
assert d["dlp_findings_count"] >= 1
PY
then
  _pass "POST plaintext raw memory is downgraded by policy gate"
else
  _fail "POST plaintext raw memory policy gate invalid"
fi

if TEST_DB="$TEST_DB" PLAIN_ID="$PLAIN_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    row=conn.execute(
        "SELECT content, redacted_content, encrypted_content, raw_storage_mode, raw_storage_reason FROM memory_items WHERE id=?",
        (os.environ["PLAIN_ID"],),
    ).fetchone()
assert row is not None
content, redacted, encrypted, mode, reason = row
for value in (content, redacted, encrypted):
    assert "abc123XYZplaintexttoken" not in (value or "")
assert mode == "redacted"
assert reason == "plaintext_requires_explicit_policy"
assert encrypted in (None, "")
PY
then
  _pass "SQLite plaintext-gated memory stores only redacted content"
else
  _fail "SQLite plaintext-gated memory leaked raw secret"
fi

RAW_SECRET_SEARCH=$(curl -sf "$BASE/memory/items?project_path=/validate/project&q=abc123XYZsecrettoken&limit=10" 2>/dev/null)
RAW_SECRET_SEARCH_COUNT=$(echo "$RAW_SECRET_SEARCH" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 99)
[ "$RAW_SECRET_SEARCH_COUNT" -eq 0 ] && _pass "GET /memory/items search does not match hidden raw secret content" \
  || _fail "GET /memory/items raw secret search matched hidden content"

# ── GET — confirm secret is redacted in response ──────────────────────────────

echo ""
echo "--- GET /memory/items — secret must be redacted ---"
GET2=$(curl -sf "$BASE/memory/items?project_path=/validate/project&limit=10" 2>/dev/null)

if echo "$GET2" | grep -Eq "abc123XYZsecrettoken|abc123XYZencryptedtoken|abc123XYZplaintexttoken"; then
  _fail "CRITICAL: raw secret value exposed in GET /memory/items response"
else
  _pass "GET response does not contain raw secret value"
fi

if echo "$GET2" | grep -q "REDACTED_SECRET"; then
  _pass "GET response contains [REDACTED_SECRET] placeholder"
else
  _fail "GET response missing [REDACTED_SECRET] placeholder"
fi

# ── Memory audit timeline ────────────────────────────────────────────────────

echo ""
echo "--- GET /memory/timeline ---"
TIMELINE_RESP=$(curl -sf "$BASE/memory/timeline?project_path=/validate/project&limit=30" 2>/dev/null)
if TIMELINE_RESP="$TIMELINE_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["TIMELINE_RESP"])
raw=json.dumps(d)
assert d["event_count"] >= 3
assert d["by_event_type"]["created"] >= 3
assert any(event["event_type"] == "created" and event["item"] and event["item"]["project_path"] == "/validate/project" for event in d["events"])
assert any("REDACTED_SECRET" in event["summary"] for event in d["events"])
assert "abc123XYZsecrettoken" not in raw
assert "abc123XYZencryptedtoken" not in raw
assert "abc123XYZplaintexttoken" not in raw
assert all(isinstance(event["details"], dict) for event in d["events"])
PY
then
  _pass "GET /memory/timeline returns redacted memory audit timeline metadata"
else
  _fail "GET /memory/timeline metadata invalid"
fi

# ── Fresh context package ────────────────────────────────────────────────────

echo ""
echo "--- GET /memory/context ---"
CONTEXT_RESP=$(curl -sf "$BASE/memory/context?project_path=/validate/project&limit=20" 2>/dev/null)
if CONTEXT_RESP="$CONTEXT_RESP" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["CONTEXT_RESP"])
text=d["package_text"]
assert d["project_path"] == "/validate/project"
assert d["item_count"] >= 2
assert d["source_item_count"] >= d["item_count"]
assert d["stale_excluded_count"] >= 1
assert d["dlp_findings_count"] == 0
assert text.startswith("Spectrona Fresh Context")
assert "decided to use Python for Phase 1" in text
assert "legacy stale validation preference" not in text
raw=json.dumps(d)
assert "abc123XYZsecrettoken" not in raw
assert "abc123XYZencryptedtoken" not in raw
assert "abc123XYZplaintexttoken" not in raw
assert "REDACTED_SECRET" in text
assert any(section["memory_type"] == "project_decision" for section in d["sections"])
assert all(item["stale"] is False for section in d["sections"] for item in section["items"])
PY
then
  _pass "GET /memory/context returns redacted fresh context package excluding stale memory"
else
  _fail "GET /memory/context package invalid"
fi

# ── Runtime session extraction ───────────────────────────────────────────────

echo ""
echo "--- GET/POST /memory/extract ---"
curl -sf -X POST "$BASE/openai/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-spectrona-client: codex" \
  -H "x-spectrona-project-path: /validate/project" \
  -d '{"model":"gpt-session-extract","messages":[{"role":"user","content":"summarize validation runtime session"}]}' >/dev/null
curl -sf -X POST "$BASE/local/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-spectrona-client: codex" \
  -H "x-spectrona-project-path: /validate/project" \
  -d '{"model":"local-session-extract","messages":[{"role":"user","content":"check sk-proj-abc123XYZsessionsecret9999 routing"}]}' >/dev/null
_pass "runtime session extraction fixtures created"

EXTRACT_PREVIEW=$(curl -sf "$BASE/memory/extract?project_path=/validate/project&client=codex&limit=20&max_summary_chars=2000" 2>/dev/null)
if EXTRACT_PREVIEW="$EXTRACT_PREVIEW" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["EXTRACT_PREVIEW"])
raw=json.dumps(d)
text=d["summary_text"]
assert d["status"] == "planned"
assert d["dry_run"] is True
assert d["source"] == "runtime_events"
assert d["project_path"] == "/validate/project"
assert d["client"] == "codex"
assert d["event_count"] >= 2
assert d["success_count"] >= 2
assert d["runtime_dlp_findings_count"] >= 1
assert d["total_tokens"] > 0
assert d["by_client"]["codex"] >= 2
assert d["by_project_path"]["/validate/project"] >= 2
assert d["by_provider"]["openai"] >= 1
assert d["by_provider"]["local"] >= 1
assert "/openai/v1/chat/completions" in d["by_route"]
assert "/local/v1/chat/completions" in d["by_route"]
assert "Spectrona Session Extraction" in text
assert "runtime_events metadata" in text
assert "abc123XYZsessionsecret" not in raw
assert all(event["project_path"] == "/validate/project" for event in d["events"])
PY
then
  _pass "GET /memory/extract previews redacted runtime session metadata"
else
  _fail "GET /memory/extract preview invalid"
fi

EXTRACT_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/memory/extract" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","client":"codex"}')
[ "$EXTRACT_NO_CONFIRM_STATUS" = "400" ] && _pass "POST /memory/extract requires confirm=true" \
  || _fail "POST /memory/extract did not require confirm=true (status=$EXTRACT_NO_CONFIRM_STATUS)"

EXTRACT_APPLY=$(curl -sf -X POST "$BASE/memory/extract" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","client":"codex","confirm":true,"limit":20,"max_summary_chars":2000}')
EXTRACT_ID=$(echo "$EXTRACT_APPLY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('summary_item_id') or '')" 2>/dev/null || echo "")
if EXTRACT_ID="$EXTRACT_ID" EXTRACT_APPLY="$EXTRACT_APPLY" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["EXTRACT_APPLY"])
raw=json.dumps(d)
assert d["status"] == "applied"
assert d["dry_run"] is False
assert d["summary_item_id"] == os.environ["EXTRACT_ID"]
assert d["event_count"] >= 2
assert d["runtime_dlp_findings_count"] >= 1
assert "Spectrona Session Extraction" in d["summary_text"]
assert "abc123XYZsessionsecret" not in raw
PY
then
  _pass "POST /memory/extract applies confirmed session extraction safely"
else
  _fail "POST /memory/extract apply invalid"
fi

EXTRACT_ITEMS=$(curl -sf "$BASE/memory/items?project_path=/validate/project&source_tool=spectrona_session_extractor&limit=20" 2>/dev/null)
if EXTRACT_ID="$EXTRACT_ID" EXTRACT_ITEMS="$EXTRACT_ITEMS" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["EXTRACT_ITEMS"])
item=next(item for item in items if item["id"] == os.environ["EXTRACT_ID"])
assert item["memory_type"] == "session_summary"
assert item["source_tool"] == "spectrona_session_extractor"
assert item["pinned"] is True
assert {"session_extraction", "runtime", "summary", "client:codex", "dlp"}.issubset(set(item["tags"]))
assert "Spectrona Session Extraction" in item["content"]
assert "abc123XYZsessionsecret" not in json.dumps(items)
PY
then
  _pass "GET /memory/items shows extracted redacted session summary"
else
  _fail "GET /memory/items extracted session summary invalid"
fi

# ── Runtime session replay ───────────────────────────────────────────────────

echo ""
echo "--- GET/POST /memory/replay ---"
REPLAY_PREVIEW=$(curl -sf "$BASE/memory/replay?project_path=/validate/project&client=codex&limit=30&max_replay_chars=3000" 2>/dev/null)
if REPLAY_PREVIEW="$REPLAY_PREVIEW" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["REPLAY_PREVIEW"])
raw=json.dumps(d)
text=d["replay_text"]
step_types={step["step_type"] for step in d["steps"]}
assert d["status"] == "planned"
assert d["dry_run"] is True
assert d["source"] == "runtime_events+memory_summaries"
assert d["project_path"] == "/validate/project"
assert d["client"] == "codex"
assert d["event_count"] >= 2
assert d["memory_summary_count"] >= 1
assert d["step_count"] >= 3
assert d["runtime_dlp_findings_count"] >= 1
assert d["by_client"]["codex"] >= 2
assert d["by_summary_source"]["spectrona_session_extractor"] >= 1
assert "runtime_event" in step_types
assert "memory_summary" in step_types
assert "Spectrona Session Replay" in text
assert "metadata-only" in text
assert "raw prompts and provider responses are not replayed" in text
assert "Memory Summary" in text
assert "abc123XYZsessionsecret" not in raw
PY
then
  _pass "GET /memory/replay previews redacted metadata-only session replay"
else
  _fail "GET /memory/replay preview invalid"
fi

REPLAY_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/memory/replay" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","client":"codex"}')
[ "$REPLAY_NO_CONFIRM_STATUS" = "400" ] && _pass "POST /memory/replay requires confirm=true" \
  || _fail "POST /memory/replay did not require confirm=true (status=$REPLAY_NO_CONFIRM_STATUS)"

REPLAY_APPLY=$(curl -sf -X POST "$BASE/memory/replay" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","client":"codex","confirm":true,"limit":30,"max_replay_chars":3000}')
REPLAY_ID=$(echo "$REPLAY_APPLY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('replay_item_id') or '')" 2>/dev/null || echo "")
if REPLAY_ID="$REPLAY_ID" REPLAY_APPLY="$REPLAY_APPLY" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["REPLAY_APPLY"])
raw=json.dumps(d)
assert d["status"] == "applied"
assert d["dry_run"] is False
assert d["replay_item_id"] == os.environ["REPLAY_ID"]
assert d["event_count"] >= 2
assert d["memory_summary_count"] >= 1
assert "Spectrona Session Replay" in d["replay_text"]
assert "metadata-only" in d["replay_text"]
assert "abc123XYZsessionsecret" not in raw
PY
then
  _pass "POST /memory/replay applies confirmed metadata-only replay safely"
else
  _fail "POST /memory/replay apply invalid"
fi

REPLAY_ITEMS=$(curl -sf "$BASE/memory/items?project_path=/validate/project&source_tool=spectrona_session_replay&limit=20" 2>/dev/null)
if REPLAY_ID="$REPLAY_ID" REPLAY_ITEMS="$REPLAY_ITEMS" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["REPLAY_ITEMS"])
item=next(item for item in items if item["id"] == os.environ["REPLAY_ID"])
assert item["memory_type"] == "session_summary"
assert item["source_tool"] == "spectrona_session_replay"
assert item["pinned"] is True
assert {"session_replay", "runtime", "summary", "client:codex", "dlp"}.issubset(set(item["tags"]))
assert "Spectrona Session Replay" in item["content"]
assert "metadata-only" in item["content"]
assert "abc123XYZsessionsecret" not in json.dumps(items)
PY
then
  _pass "GET /memory/items shows replay session summary without raw secrets"
else
  _fail "GET /memory/items replay session summary invalid"
fi

# ── Memory compaction ────────────────────────────────────────────────────────

echo ""
echo "--- GET/POST /memory/compact ---"
DUP_RESP=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","source_tool":"codex","memory_type":"project_decision","content":"decided to use Python for Phase 1","importance_score":0.4,"tags":["phase1","duplicate"]}')
DUP_ID=$(echo "$DUP_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
LOW_STALE_CREATE=$(curl -sf -X POST "$BASE/memory/items" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","source_tool":"codex","memory_type":"command_history","content":"old low value validation command note","importance_score":0.2,"tags":["runtime"]}')
LOW_STALE_ID=$(echo "$LOW_STALE_CREATE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null || echo "")
if TEST_DB="$TEST_DB" LOW_STALE_ID="$LOW_STALE_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
from datetime import datetime, timedelta, timezone
old=(datetime.now(timezone.utc)-timedelta(days=60)).isoformat()
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    conn.execute("UPDATE memory_items SET updated_at=? WHERE id=?", (old, os.environ["LOW_STALE_ID"]))
PY
then
  [ -n "$DUP_ID" ] && [ -n "$LOW_STALE_ID" ] \
    && _pass "memory compaction fixtures created" \
    || _fail "memory compaction fixture ids missing"
else
  _fail "memory compaction stale fixture setup failed"
fi

COMPACT_PREVIEW=$(curl -sf "$BASE/memory/compact?project_path=/validate/project&limit=50&max_summary_chars=2000" 2>/dev/null)
if ITEM_ID="$ITEM_ID" DUP_ID="$DUP_ID" LOW_STALE_ID="$LOW_STALE_ID" COMPACT_PREVIEW="$COMPACT_PREVIEW" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["COMPACT_PREVIEW"])
raw=json.dumps(d)
actions=d["actions"]
assert d["status"] == "planned"
assert d["dry_run"] is True
assert d["scanned_item_count"] >= 5
assert d["duplicate_group_count"] >= 1
assert d["stale_candidate_count"] >= 1
assert d["applied_action_count"] == 0
assert any(a["action"] == "tag_duplicate" and a["item_id"] == os.environ["DUP_ID"] and a["duplicate_of"] == os.environ["ITEM_ID"] for a in actions)
assert any(a["action"] == "tag_stale_candidate" and a["item_id"] == os.environ["LOW_STALE_ID"] for a in actions)
assert any(a["action"] == "create_compaction_summary" for a in actions)
assert "Spectrona Memory Compaction" in d["summary_text"]
assert "abc123XYZsecrettoken" not in raw
assert "REDACTED_SECRET" in d["summary_text"]
PY
then
  _pass "GET /memory/compact previews redacted duplicate and stale compaction plan"
else
  _fail "GET /memory/compact preview invalid"
fi

COMPACT_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/memory/compact" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project"}')
[ "$COMPACT_NO_CONFIRM_STATUS" = "400" ] && _pass "POST /memory/compact requires confirm=true" \
  || _fail "POST /memory/compact did not require confirm=true (status=$COMPACT_NO_CONFIRM_STATUS)"

COMPACT_APPLY=$(curl -sf -X POST "$BASE/memory/compact" \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/validate/project","confirm":true,"limit":50,"max_summary_chars":2000}')
SUMMARY_ID=$(echo "$COMPACT_APPLY" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('summary_item_id') or '')" 2>/dev/null || echo "")
if ITEM_ID="$ITEM_ID" DUP_ID="$DUP_ID" LOW_STALE_ID="$LOW_STALE_ID" COMPACT_APPLY="$COMPACT_APPLY" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["COMPACT_APPLY"])
raw=json.dumps(d)
actions=d["actions"]
assert d["status"] == "applied"
assert d["dry_run"] is False
assert d["summary_item_id"]
assert d["applied_action_count"] >= 4
assert any(a["action"] == "pin_canonical" and a["item_id"] == os.environ["ITEM_ID"] and a["applied"] is True for a in actions)
assert any(a["action"] == "tag_duplicate" and a["item_id"] == os.environ["DUP_ID"] and a["applied"] is True for a in actions)
assert any(a["action"] == "tag_stale_candidate" and a["item_id"] == os.environ["LOW_STALE_ID"] and a["applied"] is True for a in actions)
assert any(a["action"] == "create_compaction_summary" and a["applied"] is True for a in actions)
assert "abc123XYZsecrettoken" not in raw
PY
then
  _pass "POST /memory/compact applies confirmed compaction plan safely"
else
  _fail "POST /memory/compact apply invalid"
fi

COMPACT_ITEMS=$(curl -sf "$BASE/memory/items?project_path=/validate/project&limit=100" 2>/dev/null)
if ITEM_ID="$ITEM_ID" DUP_ID="$DUP_ID" LOW_STALE_ID="$LOW_STALE_ID" SUMMARY_ID="$SUMMARY_ID" COMPACT_ITEMS="$COMPACT_ITEMS" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["COMPACT_ITEMS"])
by_id={item["id"]: item for item in items}
canonical=by_id[os.environ["ITEM_ID"]]
duplicate=by_id[os.environ["DUP_ID"]]
stale=by_id[os.environ["LOW_STALE_ID"]]
summary=by_id[os.environ["SUMMARY_ID"]]
assert canonical["pinned"] is True
assert {"canonical", "compacted"}.issubset(set(canonical["tags"]))
assert {"duplicate", "stale", "compacted"}.issubset(set(duplicate["tags"]))
assert {"compaction_candidate", "stale", "low_importance"}.issubset(set(stale["tags"]))
assert summary["memory_type"] == "session_summary"
assert summary["source_tool"] == "spectrona_compactor"
assert summary["pinned"] is True
assert "Spectrona Memory Compaction" in summary["content"]
assert "abc123XYZsecrettoken" not in json.dumps(items)
PY
then
  _pass "GET /memory/items shows compaction tags and generated summary"
else
  _fail "GET /memory/items compaction mutation state invalid"
fi

# ── PATCH — pin/update/redaction lifecycle ────────────────────────────────────

echo ""
echo "--- PATCH /memory/items/{id} ---"
PATCH_PIN=$(curl -sf -X PATCH "$BASE/memory/items/$ITEM_ID" \
  -H "Content-Type: application/json" \
  -d '{"pinned":true}')
if echo "$PATCH_PIN" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['pinned'] is True" >/dev/null 2>&1; then
  _pass "PATCH memory item can pin an item"
else
  _fail "PATCH memory item did not pin item"
fi

PINNED_GET=$(curl -sf "$BASE/memory/items?project_path=/validate/project&pinned=true" 2>/dev/null)
if ITEM_ID="$ITEM_ID" PINNED_GET="$PINNED_GET" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["PINNED_GET"])
assert any(item["id"] == os.environ["ITEM_ID"] and item["pinned"] is True for item in items)
PY
then
  _pass "GET /memory/items filters by pinned state"
else
  _fail "GET /memory/items pinned filter invalid"
fi

PATCH_UPDATE=$(curl -sf -X PATCH "$BASE/memory/items/$ITEM_ID" \
  -H "Content-Type: application/json" \
  -d '{"memory_type":"user_preference","content":"prefer short validation notes","importance_score":0.9,"tags":["updated","preference"]}')
if echo "$PATCH_UPDATE" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['memory_type']=='user_preference'; assert d['content']=='prefer short validation notes'; assert d['importance_score']==0.9; assert set(d['tags'])=={'updated','preference'}" >/dev/null 2>&1; then
  _pass "PATCH memory item updates type, content, tags, and importance"
else
  _fail "PATCH memory item update fields invalid"
fi

PATCH_SECRET=$(curl -sf -X PATCH "$BASE/memory/items/$SECRET_ID" \
  -H "Content-Type: application/json" \
  -d '{"content":"rotated sk-proj-abc123XYZupdatedtoken9999"}')
if echo "$PATCH_SECRET" | grep -q "abc123XYZupdatedtoken"; then
  _fail "PATCH memory item leaked updated raw secret"
elif echo "$PATCH_SECRET" | grep -q "REDACTED_SECRET"; then
  _pass "PATCH memory item redacts updated secret content"
else
  _fail "PATCH memory item secret update missing redaction marker"
fi

if TEST_DB="$TEST_DB" SECRET_ID="$SECRET_ID" python3 - <<'PY' >/dev/null 2>&1
import os, sqlite3
with sqlite3.connect(os.environ["TEST_DB"]) as conn:
    row=conn.execute(
        "SELECT content, redacted_content, encrypted_content, raw_storage_mode FROM memory_items WHERE id=?",
        (os.environ["SECRET_ID"],),
    ).fetchone()
assert row is not None
content, redacted, encrypted, mode = row
for value in (content, redacted, encrypted):
    assert "abc123XYZupdatedtoken" not in (value or "")
assert mode == "redacted"
PY
then
  _pass "SQLite memory update keeps raw secret out of storage"
else
  _fail "SQLite memory update stored raw secret"
fi

# ── DELETE — confirm and removal ──────────────────────────────────────────────

echo ""
echo "--- DELETE /memory/items/{id} ---"
DELETE_NO_CONFIRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/memory/items/$ITEM_ID")
[ "$DELETE_NO_CONFIRM_STATUS" = "400" ] && _pass "DELETE memory item requires confirm=true" \
  || _fail "DELETE memory item did not require confirm=true (status=$DELETE_NO_CONFIRM_STATUS)"

DELETE_RESP=$(curl -sf -X DELETE "$BASE/memory/items/$ITEM_ID?confirm=true")
if echo "$DELETE_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['status']=='deleted'; assert d['id']" >/dev/null 2>&1; then
  _pass "DELETE memory item removes confirmed item"
else
  _fail "DELETE memory item response invalid"
fi

AFTER_DELETE=$(curl -sf "$BASE/memory/items?project_path=/validate/project&limit=20" 2>/dev/null)
if ITEM_ID="$ITEM_ID" AFTER_DELETE="$AFTER_DELETE" python3 - <<'PY' >/dev/null 2>&1
import json, os
items=json.loads(os.environ["AFTER_DELETE"])
assert all(item["id"] != os.environ["ITEM_ID"] for item in items)
PY
then
  _pass "GET /memory/items excludes deleted item"
else
  _fail "GET /memory/items still returned deleted item"
fi

TIMELINE_AFTER_DELETE=$(curl -sf "$BASE/memory/timeline?item_id=$ITEM_ID&limit=20" 2>/dev/null)
if TIMELINE_AFTER_DELETE="$TIMELINE_AFTER_DELETE" python3 - <<'PY' >/dev/null 2>&1
import json, os
d=json.loads(os.environ["TIMELINE_AFTER_DELETE"])
types={event["event_type"] for event in d["events"]}
assert {"created", "updated", "deleted"}.issubset(types)
assert all(isinstance(event["summary"], str) and event["summary"] for event in d["events"])
PY
then
  _pass "GET /memory/timeline can filter an item lifecycle through delete"
else
  _fail "GET /memory/timeline item lifecycle invalid after delete"
fi

# ── Audit log checks ──────────────────────────────────────────────────────────

echo ""
echo "--- Audit log ---"
sleep 0.3
LINES_AFTER=$(wc -l < "$AUDIT_LOG" 2>/dev/null || echo 0)
NEW_LINES=$((LINES_AFTER - LINES_BEFORE))

[ "$NEW_LINES" -ge 2 ] && _pass "audit log has >= 2 new events" \
  || _fail "audit log has too few new events (new=$NEW_LINES)"

# Check memory_insert action recorded
MEMORY_INSERT=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
hits=[e for e in lines if e.get('action')=='memory_insert']
print(len(hits))
" 2>/dev/null || echo 0)
[ "$MEMORY_INSERT" -ge 1 ] && _pass "audit log contains memory_insert action" \
  || _fail "audit log missing memory_insert action"

MEMORY_MUTATIONS=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
actions={e.get('action') for e in lines}
print(1 if {'memory_update','memory_delete'}.issubset(actions) else 0)
" 2>/dev/null || echo 0)
[ "$MEMORY_MUTATIONS" -eq 1 ] && _pass "audit log contains memory_update and memory_delete actions" \
  || _fail "audit log missing memory_update or memory_delete action"

MEMORY_COMPACT=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
print(1 if any(e.get('action')=='memory_compact' for e in lines) else 0)
" 2>/dev/null || echo 0)
[ "$MEMORY_COMPACT" -eq 1 ] && _pass "audit log contains memory_compact action" \
  || _fail "audit log missing memory_compact action"

MEMORY_EXTRACT=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
print(1 if any(e.get('action')=='memory_extract_session' for e in lines) else 0)
" 2>/dev/null || echo 0)
[ "$MEMORY_EXTRACT" -eq 1 ] && _pass "audit log contains memory_extract_session action" \
  || _fail "audit log missing memory_extract_session action"

MEMORY_REPLAY=$(tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null \
  | python3 -c "
import json,sys
lines=[json.loads(l) for l in sys.stdin if l.strip()]
print(1 if any(e.get('action')=='memory_replay_session' for e in lines) else 0)
" 2>/dev/null || echo 0)
[ "$MEMORY_REPLAY" -eq 1 ] && _pass "audit log contains memory_replay_session action" \
  || _fail "audit log missing memory_replay_session action"

# Check audit log does NOT contain raw secret
if tail -n "$NEW_LINES" "$AUDIT_LOG" 2>/dev/null | grep -Eq "abc123XYZsecrettoken|abc123XYZencryptedtoken|abc123XYZplaintexttoken|abc123XYZupdatedtoken|abc123XYZsessionsecret"; then
  _fail "CRITICAL: raw secret found in audit log"
else
  _pass "audit log does not contain raw secret value"
fi

# ── Runtime memory capture/injection flow ─────────────────────────────────────

echo ""
echo "--- Runtime memory capture/retrieval/injection ---"
if PYTHONPATH="$RUNTIME_PYTHONPATH:$ROOT/spectrona-cli/src:$ROOT/mcp-inspector/src:$ROOT/runtime-guard/src" \
  python3 "$ROOT/spectrona-gateway/validation/memory_runtime_validate.py" >/dev/null 2>&1; then
  _pass "runtime memory captures, redacts, injects, and records attachments"
else
  _fail "runtime memory capture/retrieval/injection validation failed"
fi

echo ""
echo "=== Phase 3 Memory Routes Result: $PASS passed, $FAIL failed ==="
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
