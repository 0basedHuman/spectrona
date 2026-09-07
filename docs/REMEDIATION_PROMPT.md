# Spectrona — Remediation Master Prompt (Codex)

> Hand this entire file to Codex as the task prompt. It is a standing spec, not a
> one-shot instruction. Codex works one queue item per session and stops.

---

## 0. Role

You are continuing engineering work on **Spectrona**, a local-first security tool for
AI agent configurations (MCP servers, Claude, Cursor, repo secrets). The repo is at
`/Users/harsh/Documents/spectrona`.

An external code review (2026-08-11) reproduced nine defects and identified a
strategic drift. Your job is to execute the remediation queue in Section 6, one item
per session, under the existing build harness described in Section 3 — as amended by
Section 4.

Read `docs/review/index.html` for the full review with evidence before your first session.

---

## 1. The three-way merge

You are merging three inputs. When they conflict, resolve by the precedence table.

| Input | What it is | Where it lives |
|---|---|---|
| **BASE** | What is actually built today — 15,370 LOC across 6 components, 64 sessions of history | the repo; `docs/MEMORY.md`, `docs/SESSION_LOG.md` |
| **REVIEW** | Nine reproduced defects (F1–F9) + strategic recommendations | `docs/review/index.html`, Sections 5–6 below |
| **PROCESS** | The build harness: validation gates, decision log, session log, checkpoint discipline | `CLAUDE.md`, `docs/VALIDATION.md`, `validation/validate_all.sh` |

### Precedence rules

1. **PROCESS wins on *how* you work.** Every non-negotiable in Section 3 stands. The
   review does not license you to skip validation, skip the session log, or make an
   undocumented decision.
2. **REVIEW wins on *what* the code should do.** Where BASE contradicts REVIEW, the
   review is correct — it was reproduced against this code. Do not preserve a behavior
   just because it exists and passes today.
3. **REVIEW wins over PROCESS on *what gets measured*.** This is the one place the
   review overrides the harness, and it is deliberate: the check-count metric is
   itself a finding (F9). See Section 4.
4. **BASE wins on conventions.** Match the existing code's style, module layout,
   dependency-free bias, redaction habits, and `_leading_underscore` private helpers.
   Do not reformat or restructure files you are not changing.
5. **When genuinely unresolvable, stop and write the conflict into
   `docs/DECISIONS.md` as an open question. Do not guess.**

### The known conflict, resolved in advance

BASE treats a rising check count as evidence of progress (91 → 96 → 101 → 107 → 112).
REVIEW finds that this metric rewards adding rules — including rules that should not
exist (F7) — while leaving every real defect undetected (F1–F7 all pass the current
suite).

**Resolution:** the check count is retained but demoted. It is no longer a success
metric and must not be quoted as one in `MEMORY.md` or `SESSION_LOG.md`. Several queue
items will *reduce* it. A reduced count accompanied by a deleted bad rule is a
successful session. See Section 4.

---

## 2. Non-negotiable constraints

- **Defensive security only.** No exploit tooling, no exfiltration paths, no evasion.
  Everything you build detects or prevents.
- **No secret leakage.** Findings, logs, audit records, API responses, and reports
  carry redacted evidence or metadata only — never a raw credential value. This is the
  single most important invariant in the codebase. Every change touching detection,
  reporting, or logging must be checked against it.
- **Local-first (D004).** Nothing is transmitted externally. Any network capability
  (e.g. live token verification) ships **off by default** and **opt-in**.
- **No scope creep.** The queue is the queue. If you find adjacent work, write it into
  `docs/TODO.md` and move on. Do not start it. Scope drift is the root cause the review
  identified; do not reproduce it.
- **One queue item per session.** Finish it, validate it, log it, stop.

---

## 3. The harness (from `CLAUDE.md` — unchanged)

### Start of every session

Read in order, before writing any code:

1. `docs/MEMORY.md`
2. `docs/PHASES.md`
3. `docs/VALIDATION.md`
4. `docs/DECISIONS.md`
5. `docs/SESSION_LOG.md`
6. `validation/README.md`
7. `docs/REMEDIATION_PROMPT.md` (this file)

Then state: active phase / last validation state / **the exact queue item you are
executing this session**.

### Before large edits

Summarize, in this order:
1. exact files to inspect
2. exact files to change
3. exact next step

### End of every session

- Run the master gate: `bash validation/validate_all.sh`
- Update `docs/MEMORY.md` (max 10 lines, the existing format)
- Update `docs/SESSION_LOG.md` (the existing format: User intent / Implementation
  steps / Files changed / Validation results / Notes / Next recommended step)
- Update `docs/current_refactor_status.md` (completed work, files changed, remaining
  work, exact next step)
- Record any decision in `docs/DECISIONS.md`

### Session numbering

The last logged session is **064**. Start at **065** and increment. One session per
queue item; if an item takes two sessions, log both.

### Rules that do not bend

- Never claim "done" without running validation.
- Never skip the checkpoint before compaction.
- All decisions go in `docs/DECISIONS.md`.
- All session work goes in `docs/MEMORY.md` + `docs/SESSION_LOG.md`.

---

## 4. Harness amendments (REVIEW overrides PROCESS here)

These three changes to the process are themselves queue work. Apply them as you reach
the relevant items; record each in `docs/DECISIONS.md`.

### 4.1 — The success metric changes

**Retire:** "N/N checks passing" as the headline result.

**Adopt:** for detection work, **precision and recall against the config corpus**
(queue item R8). Until the corpus exists, the headline is *"defect F<n> reproduced
before, absent after, with the reproduction script committed."*

Continue running `validate_all.sh` and continue reporting its result. Just stop
treating a bigger number as a better outcome.

### 4.2 — Tests become real tests

`pytest` becomes the harness for anything with logic. Bash validation is retained for
end-to-end smoke only (does the CLI run, does the gateway bind, does the packaged
layout import). Do not add new grep-on-stdout assertions for detector behavior — write
a pytest case instead.

### 4.3 — Every defect fix ships with its reproduction

For each F-item you fix, commit the reproduction script from Section 5 into
`tests/regression/` as a permanent test. The bug must be *provable* before the fix and
*provably gone* after. This replaces the old habit of asserting that a finding ID
appears in stdout.

---

## 5. The nine defects, with reproductions

**Run the reproduction BEFORE you fix.** If it does not reproduce, the code has changed
since the review — **stop, log the discrepancy in `docs/SESSION_LOG.md`, and do not
"fix" anything.** Never write a fix for a bug you have not observed.

All commands run from the repo root.

### F1 — CRITICAL — `SECRET_KNOWN_PREFIX` only inspects `env`

```bash
cat > /tmp/f1.json <<'EOF'
{"mcpServers":{"svc":{"command":"npx","args":["-y","some-server",
 "--api-key","sk-proj-REALSECRETVALUE123456",
 "--token","ghp_ABCDEFGHIJKLMNOP1234"]}}}
EOF
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan mcp --file /tmp/f1.json --json
```
**Broken:** no `SECRET_KNOWN_PREFIX`, `summary.critical == 0`.
**Fixed:** `SECRET_KNOWN_PREFIX` present, `critical >= 1`, exit 1, and the raw value
`REALSECRETVALUE123456` appears **nowhere** in stdout.

### F2 — CRITICAL — shell-risk substring matching blocks English

```bash
PYTHONPATH=runtime-guard/src:policy-engine/src python3 - <<'EOF'
from runtime_guard.mcp_proxy import _detect_shell_risk
for t,a in [
 ('write_file',{'path':'n.md','content':'In a nutshell, the executive team approved it.'}),
 ('write_file',{'path':'n.md','content':'We shall execute the plan.'}),
 ('write_file',{'path':'n.md','content':'Seashells by the seashore'}),
 ('save',{'command':'anything at all'}),
]:
    print(_detect_shell_risk(t,a), t, list(a.values())[-1][:50])
EOF
```
**Broken:** all `True`.
**Fixed:** all `False`. A genuine shell call — tool `run_shell`, or an argument the
server's schema declares as a command — must still return `True`.

### F3 — CRITICAL — gateway has no authentication

```bash
grep -nE "middleware|Depends|Security|api_key|bearer|token" \
  spectrona-gateway/src/spectrona_gateway/app.py
```
**Broken:** no output.
**Fixed:** an auth dependency is applied to every router except `/health`; an
unauthenticated `POST /policy/presets/relaxed/apply` returns 401; `Origin` and `Host`
are validated.

### F4 — HIGH — proxy desyncs on notifications

```bash
mkdir -p /tmp/f4 && cat > /tmp/f4/server.py <<'EOF'
import sys, json
for line in sys.stdin:
    if not line.strip(): continue
    m = json.loads(line)
    if m.get("method") == "tools/list":
        print(json.dumps({"jsonrpc":"2.0","method":"notifications/message",
                          "params":{"level":"info","data":"listing"}}), flush=True)
        print(json.dumps({"jsonrpc":"2.0","id":m["id"],
                          "result":{"tools":[{"name":"read_file"}]}}), flush=True)
EOF
PYTHONPATH=runtime-guard/src:policy-engine/src python3 - <<'EOF'
import subprocess, json
from runtime_guard.mcp_proxy import _forward_to_upstream
up = subprocess.Popen(["python3","/tmp/f4/server.py"], stdin=subprocess.PIPE,
     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
print(json.dumps(_forward_to_upstream(up, {"jsonrpc":"2.0","id":7,"method":"tools/list"})))
up.terminate()
EOF
```
**Broken:** returns the notification, no `id`, tools lost.
**Fixed:** returns `{"id":7,"result":{"tools":[...]}}`; the notification is forwarded
to the client separately, not swallowed.

### F5 — HIGH — DLP misses most credential formats

```bash
PYTHONPATH=spectrona-gateway/src python3 - <<'EOF'
from spectrona_gateway.dlp import findings_count
for n,s in {
 'stripe':'sk_live_51H8xYzAbCdEfGhIjKlMnOp',
 'google':'AIzaSyD-1234567890abcdefghijklmnop',
 'sendgrid':'SG.AbCdEfGh1234.IjKlMnOpQrStUvWxYz567890',
 'hf':'hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234',
 'rsa':'-----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKC',
 'pg':'postgres://admin:SuperSecret123@db.internal:5432/prod',
 'jwt':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r',
 'aws':'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
 'gitlab':'glpat-AbCdEfGhIjKlMnOpQrSt',
}.items(): print(('MISS' if findings_count(s)==0 else 'ok  '), n)
EOF
```
**Broken:** 9 MISS.
**Fixed:** 0 MISS, and a benign-text corpus produces zero findings (no entropy rule
firing on base64 images, UUIDs, git SHAs, or lockfile hashes).

### F6 — HIGH — policy engine fails open

```bash
PYTHONPATH=policy-engine/src python3 - <<'EOF'
from policy_engine import load_policy_text, PolicyEngine, PolicyContext
a = load_policy_text("version: 1\ndefault_action: allow\nrules:\n  - id: t\n    action: deny\n")
print('A empty-match  ->', PolicyEngine(a).evaluate(PolicyContext(route='r',provider_type='p')).action)
b = load_policy_text("version: 1\ndefault_action: allow\nrules:\n  - id: s\n    action: deny\n    match:\n      shel_risk: true\n")
print('B typo-key     ->', PolicyEngine(b).evaluate(PolicyContext(route='r',provider_type='p',shell_risk=True)).action)
EOF
```
**Broken:** A prints `deny` (matches everything); B prints `allow` (rule silently dead).
**Fixed:** both raise a validation error at **load** time, before any request is
evaluated. A policy that fails to parse or validate is fatal — never a permissive
fallback.

### F7 — MEDIUM — noise on correct configurations

```bash
cat > /tmp/f7.json <<'EOF'
{"mcpServers":{
 "filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","."]},
 "github":{"command":"npx","args":["-y","@modelcontextprotocol/server-github"],
           "env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"${GITHUB_TOKEN}"}},
 "sentry":{"command":"uvx","args":["mcp-server-sentry","--auth-token","${SENTRY_TOKEN}"]}}}
EOF
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan mcp --file /tmp/f7.json --json
```
**Broken:** 6 findings; `${SENTRY_TOKEN}` reported as an unpinned package.
**Fixed:** `MCP_NO_AUDIT_LOG` deleted entirely; `${...}` references excluded from the
package rule; total findings ≤ 2 and every remaining one is actionable.

### F8 — MEDIUM — D002 not implemented

```bash
grep -rniE "yaml|load_rules|rules/" mcp-inspector/src/ | grep -v "\"\"\"\|#"
```
**Broken:** no code path reads `mcp-inspector/rules/*.yaml`.
**Fixed:** either a real loader exists, or D002 is amended in `docs/DECISIONS.md` to
state that detection is code. Both are acceptable; leaving the log describing a system
that does not exist is not.

### F9 — MEDIUM — no unit tests

```bash
find . -name "test_*.py" -o -name conftest.py -o -name pytest.ini
```
**Broken:** empty.
**Fixed:** `pytest` runs green from the repo root and is wired into
`validation/validate_all.sh`.

---

## 6. The remediation queue

Execute **in order**. Do not reorder without a `docs/DECISIONS.md` entry.

### BLOCK A — ship-blockers (~1 week)

> These five separate "would mislead a user who trusted it" from "safe to publish."
> Nothing else in this queue matters until Block A is closed.

| ID | Work | Fixes | Est |
|---|---|---|---|
| **R1** | Scan `args`, `command`, and nested values for secrets — walk the whole server object, not one field | F1 | ~2h |
| **R2** | Delete `MCP_NO_AUDIT_LOG` and its detector, rule entry, fixtures, and checks; exclude `${...}` from the package rule | F7 | ~1h |
| **R3** | Gateway bearer token from `~/.spectrona/config.yaml`, required on all non-`/health` routes; validate `Origin` and `Host`; never bind `0.0.0.0` | F3 | ~3h |
| **R4** | Schema-validate policy at load; reject unknown match keys and empty `match`; parse failure is fatal | F6 | ~3h |
| **R5** | MCP proxy defaults to dry-run; enforcement requires explicit opt-in and prints why | F2 | ~1h |

**R1 notes.** One recursive walk over the server object. Report the JSON path in
`source` (e.g. `mcpServers.svc.args[3]`) so the finding is actionable. Args are the
higher-severity surface — they are what `ps aux` exposes — so do not down-rank them
relative to `env`.

**R2 notes.** This *reduces* the check count. That is correct and expected. Also remove
the invented `auditLog` key from the safe fixtures — it was added so validation would
pass and is not part of the MCP specification. Record the deletion in `DECISIONS.md`:
an unactionable finding is worse than no finding.

**R3 notes.** Token generated at `spectrona init`, `0600`, never logged, never echoed
by `spectrona status`. The dashboard reads it from the same config. `confirm: true`
stays as an accident guard; it is not a security control and must not be described as
one.

**R4 notes.** Prefer a real YAML parser over extending the hand-rolled one. If adding a
dependency is unacceptable, keep the parser but add a strict schema layer in front of
`PolicyEngine` and reject anything it does not recognize. Fail closed, always.

**R5 notes.** Do **not** attempt to fix shell-risk detection in this item — that is R7.
R5 only makes the bad detector harmless by removing it from the blocking path.

### BLOCK B — foundation (~4 days)

| ID | Work | Fixes | Est |
|---|---|---|---|
| **R6** | `pytest` harness; port detector assertions out of bash; add `tests/regression/` with F1–F7 repros; wire into `validate_all.sh` | F9 | ~1d |
| **R7** | Unified detection library used by scanner + gateway + proxy; layered prefix → entropy → structural validation; rewrite shell/filesystem risk to match on schema and argument keys, never free text | F1, F2, F5 | ~3d |

**R7 is the most important item in this document.** It collapses `dlp.py` and
`secrets_detector.py` into one package so a format is added once and every consumer
gets it. Layer the checks the way `gitleaks` and TruffleHog do: prefix match, then
entropy, then structural validation — Stripe, AWS, and GitHub tokens carry verifiable
checksums, which is how you gain precision instead of trading it for recall. Live
network verification is **off by default and opt-in** (D004).

Shell-risk detection is rebuilt in the same item: match on the tool's declared input
schema and on argument keys that actually reach a shell. Never substring-match content.

### BLOCK C — the moat (~1 week)

| ID | Work | Fixes | Est |
|---|---|---|---|
| **R8** | Public MCP config corpus + precision benchmark | F7, F9 | ~1w |

Harvest ~1,000 real `mcpServers` configurations from public GitHub. Hand-label a
stratified sample. Build `validation/corpus_benchmark.py` reporting per-rule precision
and recall. **Gate every rule at ≥95% precision; disable any rule that misses.**

This one asset does three jobs: it makes false positives measurable rather than
arguable, it becomes the regression suite, and it is the launch story. "We scanned
1,000 public MCP configs and N% leak credentials" is a post that gets read, and the
tool that produced it gets installed. Anyone can write regexes; nobody else has the
benchmark.

Store only redacted metadata in the repo — never a harvested credential, even from a
public source. Record the corpus methodology in `docs/DECISIONS.md`.

### BLOCK D — distribution (~3 days)

| ID | Work | Est |
|---|---|---|
| **R9** | SARIF output, GitHub Action, `npx` wrapper | ~3d |

Highest leverage per hour in this document. **SARIF first** — it lands findings in the
GitHub code-scanning tab and the VS Code SARIF viewer for free. Then a composite
GitHub Action so the scan runs on every pull request. Then an `npx spectrona` wrapper:
the MCP audience is a Node audience, and `npx` will out-install a Homebrew formula that
needs a tap, a Python runtime, and a `PYTHONPATH` shim.

### BLOCK E — protocol (~3 days)

| ID | Work | Fixes | Est |
|---|---|---|---|
| **R10** | Rewrite proxy transport: two pumps, pending-request map keyed by JSON-RPC id, bidirectional notification passthrough, upstream stderr surfaced to the Spectrona log | F4 | ~3d |

### Deferred — do not start

`R11` scope freeze: branch out memory replay / compaction / timeline / staleness /
context packages / session extraction, VS Code terminal routing, local-LLM fallback,
and LaunchAgent plists. Roughly 1,500+ lines written while Phase 1 was still unshipped.
**Propose this as a `DECISIONS.md` entry and wait for the maintainer's answer before
deleting anything.**

---

## 7. Per-session protocol

```
1. Read the seven files in Section 3.
2. State: active phase | last validation state | queue item ID for this session.
3. Run the Section 5 reproduction for the defect this item fixes.
   - Does not reproduce? STOP. Log the discrepancy. Do not fix.
4. Summarize: files to inspect | files to change | exact next step.
5. Implement. Match existing conventions (BASE precedence).
6. Verify:
   a. the reproduction now shows the fixed behavior
   b. the repro is committed under tests/regression/
   c. pytest green (once R6 lands)
   d. bash validation/validate_all.sh passes
   e. no raw secret appears in any output, log, report, or audit record
7. Update: MEMORY.md | SESSION_LOG.md | current_refactor_status.md
   | DECISIONS.md (if a decision was made) | VALIDATION.md | PHASES.md
8. Report honestly. If a step was skipped, say so. If a check fails, show the
   output. Never round a partial result up to "done."
9. STOP. One queue item per session.
```

---

## 8. Required decision entries

Write these into `docs/DECISIONS.md` as you reach them, in the existing D-number format
(Decision / Why / Alternatives rejected / Impact / Revisit). Next available: **D005**.

- **D005** — Detection quality is measured by corpus precision, not check count.
  (Amends the validation regime; land with R6.)
- **D006** — The runtime layer ships advisory-only until the false-positive rate is
  measured on real traffic. (Amends Phase 2; land with R5.)
- **D007** — Resolution of D002: either the YAML rule loader becomes real, or detection
  is declared to be code. (Land with R7.)
- **D008** — `MCP_NO_AUDIT_LOG` deleted; unactionable findings are worse than none.
  (Land with R2.)
- **D009** — Scope freeze proposal for Phase 3 and integration surfaces. (Propose only;
  requires maintainer sign-off.)

---

## 9. Guardrails

**Do not:**
- Add a new detection rule. The queue removes rules and improves existing ones. New
  rules require a `DECISIONS.md` entry and a corpus precision result.
- Grow the bash check count as a goal. Several items reduce it; that is success.
- Build anything in Phase 3 (memory, replay, compaction, context packages).
- Add dashboard features, provider integrations, or packaging work outside R9.
- Edit a safe fixture so a rule passes. That is how F7 happened. If a rule needs the
  fixture changed to look clean, the rule is wrong.
- Print, log, or commit a raw credential — including in tests, corpus data, and
  reproduction scripts. Use synthetic values with real *shapes*.
- Claim completion without the master gate output pasted into `SESSION_LOG.md`.
- Start two queue items in one session.

**Do:**
- Prove the bug, then fix it, then prove it is gone.
- Delete code when the review says delete. Removal is progress here.
- Stop and ask when BASE and REVIEW conflict in a way Section 1 does not resolve.
- Keep the existing dependency-free bias unless R4 or R7 makes a dependency the
  clearly safer engineering call — and say so in `DECISIONS.md` if you add one.

---

## 10. Definition of done

**Block A done** — the five ship-blocker reproductions all show fixed behavior, the
master gate passes, and `spectrona scan mcp` on a config with secrets in `args` reports
CRITICAL with the raw value absent from every output path.

**Overall done** — the scanner is accurate against a public corpus at ≥95% precision,
it runs in CI via SARIF, it installs with `npx`, and the runtime layer is honest about
being advisory. At that point Spectrona is a tool people use, which is the one thing
64 sessions of building has not yet produced.
