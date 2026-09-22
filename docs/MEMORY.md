# MEMORY — Spectrona Engineering Context

Compact session memory. Each entry max 10 lines.
Do NOT store transcripts, code dumps, or logs.

---

## 2026-09-21 — Session 083: R8 corpus expansion shard
Prompt Summary: Continue R8 by labeling another redacted GitHub queue slice.
Decision: Promoted 47 additional unambiguous queue records; benchmark corpus now has 135 labeled cases.
Decision: Skipped broader-policy cases such as Deno `--allow-run` until a rule decision exists.
Files Changed: labeled corpus, corpus validation minimum, checkpoint docs.
Validation: R8 1,000-case blocker reproduced; 135-case benchmark PASS; corpus validation PASS; focused pytest PASS; master gate PASS.
Next: Continue R8 only by labeling remaining queue records and harvesting more candidates until roughly 1,000 reviewed configs pass the precision gate.

## 2026-09-13 — Session 082: R8 corpus labeling shard
Prompt Summary: Continue R8 by labeling more records from the local redacted GitHub queue.
Decision: Promoted 44 additional unambiguous queue records; benchmark corpus now has 88 labeled cases.
Decision: Skipped ambiguous broader-policy cases instead of inventing new rules or labels.
Files Changed: labeled corpus, corpus validation minimum, checkpoint docs.
Validation: R8 1,000-case blocker reproduced; 88-case benchmark PASS; corpus validation PASS; focused pytest PASS; master gate PASS.
Next: Continue R8 only by labeling remaining queue records and harvesting more candidates until roughly 1,000 reviewed configs pass the precision gate.

## 2026-09-13 — Session 081: R8 corpus precision shard
Prompt Summary: Continue R8 labeling from the local redacted public GitHub queue.
Decision: Promoted 25 additional manually reviewed queue records; benchmark corpus now has 44 labeled cases.
Decision: Corpus exposed and fixed scanner shell substring noise on `@executeautomation/playwright-mcp-server`.
Files Changed: scanner shell detector, detector pytest, labeled corpus, corpus gate, checkpoint docs.
Validation: R8 1,000-case blocker reproduced; 44-case benchmark PASS; focused pytest PASS; master gate PASS.
Next: Continue R8 by labeling more queue records and harvesting more candidates until roughly 1,000 reviewed configs pass the precision gate.

## 2026-09-13 — Session 080: R8 reviewed corpus shard
Prompt Summary: Continue R8 after token-backed queue generation.
Decision: Promote only manually reviewed, unambiguous local queue records; scanner predictions remain triage only.
Decision: Seven public GitHub configs were added to the labeled benchmark corpus with source URLs and redacted metadata.
Files Changed: labeled corpus, corpus validation minimum, checkpoint docs.
Validation: R8 1,000-case blocker reproduced; 19-case benchmark PASS; corpus validation PASS; master gate PASS.
Next: Continue R8 by labeling more queue records and repeating harvest until roughly 1,000 reviewed configs pass the precision gate.

## 2026-09-13 — Session 079: R8 token-backed redacted queue
Prompt Summary: Use local token file safely and continue R8 public corpus work.
Decision: Token file was sourced only inside harvest commands; no token value was printed, logged, or committed.
Decision: Harvester now percent-encodes GitHub API URLs and skips unreadable candidates instead of aborting.
Files Changed: harvester resilience, harvester tests, queue ignore rule, checkpoint docs; local redacted queue generated for review.
Validation: R8 blocker reproduced; harvested 196 redacted candidate queue records; focused R8 tests PASS; master gate PASS.
Next: Human-label queue records, promote reviewed labels, repeat harvest toward roughly 1,000 labeled configs, then enforce full benchmark.

## 2026-09-10 — Session 078: R8 harvest still token-blocked
Prompt Summary: Continue R8 public corpus work.
Decision: Do not reuse pasted credentials; no `GITHUB_TOKEN` or `gh` auth path is visible to this Codex shell.
Decision: R8 cannot harvest public GitHub candidates in this environment yet.
Files Changed: checkpoint docs only.
Validation: R8 blocker reproduced; `bash validation/validate_all.sh` PASS; no code or corpus changes made.
Next: Restart/launch Codex with a fresh `GITHUB_TOKEN` in its environment, then rerun R8 harvest/queue/label/promote.

## 2026-09-07 — Session 077: R8 token availability check
Prompt Summary: Continue R8 after maintainer handled the exposed GitHub token.
Decision: Do not reuse or log pasted credentials; only consume `GITHUB_TOKEN` from the local process environment.
Decision: R8 remains blocked here because `GITHUB_TOKEN` is absent from this Codex shell.
Files Changed: checkpoint docs only.
Validation: R8 blocker reproduced; `bash validation/validate_all.sh` PASS; no code or corpus changes made.
Next: Export a fresh `GITHUB_TOKEN` in the environment visible to Codex, then rerun R8 harvest/queue/label/promote.

## 2026-09-07 — Session 076: Repository remote and push checkpoint
Prompt Summary: Add GitHub remote, push current Spectrona workspace, then continue R8 boundary.
Decision: D011 records initial repo hygiene: cache/local agent settings ignored; fixture `.env` remains tracked.
Decision: Remote `origin` set to `https://github.com/0basedHuman/spectrona.git`; initial commit pushed to `main`.
Files Changed: root `.gitignore`, docs checkpoint updates, Git metadata initialized locally.
Validation: `bash validation/validate_all.sh` PASS after checkpoint docs.
Next: Continue R8 only with GITHUB_TOKEN: harvest, queue, label, promote full corpus, enforce 95% precision gate.

## 2026-09-07 — Session 075: R8 harvester query breadth
Prompt Summary: Continue R8 while full public harvest remains unavailable in this shell.
Decision: D010 unchanged; expanded harvesting still emits redacted unlabeled candidates only.
Decision: R8 remains open until token-backed harvest and human labeling produce roughly 1,000 cases.
Files Changed: GitHub harvester query fan-out/dedup, harvester tests, corpus validation/docs, checkpoint docs.
Validation: 1,000-case threshold still fails at 12 cases; no GITHUB_TOKEN; harvester tests PASS; pytest PASS; master gate PASS.
Next: Continue R8 only with GITHUB_TOKEN: harvest candidates, queue, label, promote full corpus, enforce 95% precision gate.

## 2026-09-07 — Session 074: R8 labeled corpus promotion guard
Prompt Summary: Continue R8 with no GitHub token available and no move to R9.
Decision: D010 extended: promotion strips scanner predictions and accepts only reviewed human-labeled records.
Decision: R8 full corpus remains externally blocked until GitHub harvest and manual labeling are available.
Files Changed: corpus promotion helper, corpus validation/docs, pytest promotion tests, checkpoint docs.
Validation: 1,000-case threshold still fails at 12 cases; no GITHUB_TOKEN; promotion guard PASS; pytest PASS; master gate PASS.
Next: Continue R8 only with GITHUB_TOKEN: harvest, queue, label, promote ~1,000 redacted records, then enforce full benchmark.

## 2026-09-07 — Session 073: R8 labeling queue workflow
Prompt Summary: Continue R8, not R9, after the corpus benchmark foundation.
Decision: D010 remains: queue predictions are triage metadata only, never labels.
Decision: Full R8 still requires GitHub token/network access plus manual labeling to reach roughly 1,000 cases.
Files Changed: corpus label queue helper, corpus validation, corpus docs, pytest queue tests, checkpoint docs.
Validation: 1,000-case threshold reproduced as failing at 12 cases; no GITHUB_TOKEN; label queue PASS; pytest PASS; master gate PASS.
Next: Continue R8 only: run harvester with GITHUB_TOKEN, generate/label queue, promote redacted labeled cases, enforce full benchmark.

## 2026-09-07 — Session 072: R8 corpus benchmark foundation
Prompt Summary: Continue remediation queue with R8: MCP config corpus and precision benchmark.
Decision: D010 records corpus methodology: committed data is redacted/labeled metadata; harvesting is token-gated and manually labeled.
Decision: Added 95% precision benchmark gate over a redacted seed corpus; full ~1,000-config harvest remains R8 work.
Files Changed: corpus benchmark, seed corpus, harvest helper, corpus validation, pytest benchmark tests, docs.
Validation: Pre-fix benchmark absent; seed benchmark PASS; pytest PASS; corpus validation PASS; master gate PASS.
Next: Continue R8 only: run/label the full public GitHub corpus, then enforce the benchmark on that corpus.

## 2026-08-22 — Session 071: R7 unified detection and risk rewrite
Prompt Summary: Execute remediation queue item R7 for F1/F2/F5 detection consolidation.
Decision: D007 amends D002: detection is implemented in code; YAML rule files are catalog/docs until a safe loader exists.
Decision: Added dependency-free `spectrona_detection`; scanner, gateway DLP, runtime redaction, and repo secret scanning use it.
Files Changed: shared detector package, scanner/gateway/runtime imports, proxy risk matching, pytest regressions, validation/packaging wiring, docs.
Validation: F2/F5 reproduced before fix and fixed after; benign DLP corpus zero findings; pytest PASS; component checks PASS; master gate PASS.
Next: Stop per protocol. Next session should execute R8 only: public MCP config corpus and precision benchmark.

## 2026-08-22 — Session 070: R6 pytest regression harness
Prompt Summary: Execute remediation queue item R6 for F9: no unit tests.
Decision: D005 records corpus precision/recall as the detection quality metric; pytest now owns detector/regression assertions.
Decision: F2/F4/F5 reproductions are strict xfail until their owning queue items land; fixed F1/F3/F6/F7 regressions pass.
Files Changed: pytest config, regression/detector tests, pytest validation script, master gate wiring, docs.
Validation: F9 reproduced before fix; `python3 -m pytest` PASS; pytest validation PASS; master gate PASS.
Next: Stop per protocol. Next session should execute R7 only: unified detection library and shell-risk rewrite.

## 2026-08-12 — Session 069: R5 MCP proxy advisory default
Prompt Summary: Execute remediation queue item R5 for F2 containment only.
Decision: D006 records MCP runtime enforcement as advisory-only by default until detector precision is measured.
Decision: `spectrona mcp proxy` and runtime module now require `--enforce` or `SPECTRONA_MCP_ENFORCE=true` before blocking/redaction.
Files Changed: `mcp_proxy.py`, Spectrona MCP CLI, runtime/CLI/packaging validation, F2 dry-run regression, docs.
Validation: F2 false-positive detector reproduced before fix; dry-run regression PASS; runtime PASS; CLI PASS; packaging PASS; master gate PASS.
Next: Stop per protocol. Next session should execute R6 only: pytest harness and permanent regression suite wiring.

## 2026-08-12 — Session 068: R4 strict policy load validation
Prompt Summary: Execute remediation queue item R4 for F6: policy engine fail-open behavior.
Decision: Policy loading now schema-validates rules, rejects empty/missing `match`, unknown fields, unknown match keys, and bad value types.
Decision: Invalid policy text fails at `load_policy_text()` before request evaluation; gateway request policy remains fail-closed on load errors.
Files Changed: `policy_engine/loader.py`, policy validation, F6 regression, docs.
Validation: F6 reproduced before fix; F6 regression PASS; policy engine PASS; gateway PASS; master gate PASS.
Next: Stop per protocol. Next session should execute R5 only: MCP proxy dry-run default / explicit enforcement opt-in.

## 2026-08-12 — Session 067: R3 gateway local auth
Prompt Summary: Execute remediation queue item R3 for F3: unauthenticated gateway routes.
Decision: Gateway now requires a local bearer token for every non-`/health` route and rejects bad Host/Origin headers.
Decision: `spectrona init` generates a gateway token in `config.yaml`, chmods config to `0600`, and `status` validation proves it is not echoed.
Files Changed: gateway auth/config/app/UI, CLI init/gateway config/start guard, validations, packaging smoke, F3 regression, docs.
Validation: F3 reproduced before fix; R3 regression PASS; Phase 2 gateway PASS; Phase 2C CLI PASS; master gate PASS.
Next: Stop per protocol. Next session should execute R4 only: strict policy load-time validation.

## 2026-08-12 — Session 066: R2 delete audit-log noise
Prompt Summary: Execute remediation queue item R2 for F7: noisy correct MCP configs.
Decision: Deleted `MCP_NO_AUDIT_LOG`; D008 records that unactionable findings are worse than none.
Decision: Package detection skips `${...}` refs and aggregates unpinned package evidence by server path.
Files Changed: scanner/rules/package detector, safe fixtures, validation/packaging checks, sample report, F7 regression, docs.
Validation: F7 reproduced before and absent after; regression script PASS; Phase 1 PASS; full suite PASS.
Next: Stop per protocol. Next session should execute R3 only: gateway auth, Origin/Host validation, and localhost binding.

## 2026-08-12 — Session 065: R1 args/nested secret scanning
Prompt Summary: Execute remediation queue item R1 for F1: secrets in MCP args were invisible.
Decision: `SECRET_KNOWN_PREFIX` now walks each MCP server object recursively and reports JSON paths.
Decision: Package evidence ignores known-secret-shaped args so secondary findings do not leak credentials.
Files Changed: `secrets_detector.py`, `package_detector.py`, `tests/regression/f1_args_secret_repro.py`, docs.
Validation: F1 reproduced before and absent after; regression script PASS; Phase 1 PASS; full suite PASS.
Next: Stop per protocol. Next session should execute R2 only: delete `MCP_NO_AUDIT_LOG` and exclude `${...}` package refs.

## 2026-08-07 — Session 064: Missing MCP audit/logging scanner
Prompt Summary: Continue scanner expansion after suspicious postinstall detection.
Decision: Added `MCP_NO_AUDIT_LOG` detection for MCP servers without meaningful audit/log config.
Decision: Safe MCP fixtures now declare `auditLog` so safe fixtures remain clean.
Files Changed: `audit_detector.py`, scanner wiring, safe MCP fixtures, validation, README, docs.
Validation: Phase 1 -> PASS (112/112); CLI -> PASS (127/127); packaging -> PASS (38/38); full suite -> PASS.
Next: Scanner expansion is complete for tracked rules; next target is published Homebrew tap or secret rotation/status metadata.

## 2026-08-07 — Session 063: Suspicious postinstall scanner

Prompt Summary:
- Continue scanner expansion after MCP tool prompt-injection detection.

Decision:
- Added `MCP_POSTINSTALL_SCRIPT` detection for embedded MCP package manifests and local package.json references.
- Evidence records suspicious pattern labels, not raw postinstall script text.

Files Changed:
- `postinstall_detector.py`, scanner wiring, unsafe MCP fixture, validation, README, docs

Validation:
- Phase 1 -> PASS (107/107); CLI -> PASS (126/126); packaging -> PASS (37/37); full suite -> PASS.

Next:
- Missing MCP audit/logging detector.

## 2026-08-07 — Session 062: MCP tool prompt-injection scanner

Prompt Summary:
- Continue scanner expansion after HTML reports.

Decision:
- Added `MCP_TOOL_PROMPT_INJECTION_RISK` detection for risky MCP server/tool description metadata.
- Evidence records matched directive pattern labels, not full description text.

Files Changed:
- `prompt_injection_detector.py`, scanner wiring, unsafe MCP fixture, validation, README, docs

Validation:
- Phase 1 -> PASS (101/101); CLI -> PASS (125/125); packaging -> PASS (37/37); full suite -> PASS.

Next:
- Suspicious postinstall script detector or missing MCP audit/logging detector.

## 2026-08-07 — Session 061: HTML reports

Prompt Summary:
- Continue scanner expansion after `scan repo`.

Decision:
- Added standalone HTML report output through `mcp-inspector report --html` and Spectrona scan `--html --output`.
- Reused existing JSON report shape; HTML escapes all finding fields and preserves redacted evidence.

Files Changed:
- `html_reporter.py`, mcp-inspector CLI, Spectrona scan CLI, validation, README, docs

Validation:
- Phase 1 -> PASS (96/96); CLI -> PASS (124/124); packaging -> PASS (36/36); full suite -> PASS.

Next:
- Risky MCP tool description/prompt-injection detection, suspicious postinstall detection, or missing MCP audit/logging detector.

## 2026-08-07 — Session 060: Repo scanner

Prompt Summary:
- Continue scanner expansion after `scan cursor`.

Decision:
- Added `scan repo` for repo-level secret risks: exposed `.env`, known prefixes, high entropy, and git-tracked secret-bearing files.
- Evidence is metadata-only/redacted before terminal, JSON, and packaged CLI output.

Files Changed:
- `repo_parser.py`, `repo_detector.py`, scanner/CLI wiring, repo fixtures, validation, docs

Validation:
- Phase 1 -> PASS (91/91); CLI -> PASS (123/123); packaging -> PASS (35/35); full suite -> PASS.

Next:
- HTML reports, risky MCP tool description/prompt-injection, suspicious postinstall, or missing MCP audit/logging detector.

## 2026-08-07 — Session 059: Cursor config scanner

Prompt Summary:
- Continue scanner expansion after `scan claude`.

Decision:
- Added `mcp-inspector scan cursor` and `spectrona scan cursor` for Cursor project/user config.
- Detects terminal auto-run / disabled confirmation, prompt-injection-prone Cursor rules, and globally scoped Cursor MCP servers.
- Evidence is summarized/redacted before terminal/JSON reporting.

Files Changed:
- `cursor_parser.py`, `cursor_detector.py`, scanner/CLI wiring, Cursor fixtures, validation, docs

Validation:
- Phase 1 -> PASS (79/79); CLI -> PASS (119/119); packaging -> PASS (34/34); full suite -> PASS.

Next:
- Continue scanner expansion with `scan repo`, HTML reports, or high-entropy secret detection.

## 2026-08-07 — Session 058: Claude config scanner

Prompt Summary:
- Continue the next scanner expansion item with validation at each step.

Decision:
- Added `mcp-inspector scan claude` and `spectrona scan claude` for Claude settings and `CLAUDE.md`.
- Detects dangerous auto-approved permissions, missing deny list, hook shell-injection risk, and oversized `CLAUDE.md`.
- Evidence is summarized/redacted before terminal/JSON reporting.

Files Changed:
- `claude_parser.py`, `claude_detector.py`, scanner/CLI wiring, Claude fixtures, validation, docs

Validation:
- Phase 1 -> PASS (62/62); CLI -> PASS (115/115); packaging -> PASS (33/33); full suite -> PASS.

Next:
- Continue scanner expansion with `scan cursor` or `scan repo`, or publish the Homebrew tap.

## 2026-08-05 — Session 057: Dashboard browser validation

Prompt Summary:
- Continue to the next roadmap item after metadata-only session replay.

Decision:
- Added Chrome-headless dashboard validation that starts an isolated gateway, seeds runtime/memory fixtures, captures `/ui`, and validates screenshot/DOM output.
- The validator checks a nonblank PNG, post-JS dashboard panels, seeded traffic/memory content, and redaction without raw secret leakage.
- Wired the browser validator into the master validation gate with clean skip behavior when Chrome is unavailable.

Files Changed:
- `spectrona-gateway/validation/dashboard_browser_validate.sh`, `validation/validate_all.sh`, docs

Validation:
- Dashboard browser -> PASS (6/6); `bash validation/validate_all.sh` -> PASS.

Next:
- Publish Homebrew release/tap, start scanner expansion, or add secret rotation/status metadata.

## 2026-08-05 — Session 056: Metadata-only session replay

Prompt Summary:
- Continue to the next roadmap item after Homebrew release artifact validation.

Decision:
- Added metadata-only session replay from runtime events plus redacted session-summary memories.
- Added `GET/POST /memory/replay`; confirmed apply stores a pinned redacted `session_summary`.
- Dashboard Memory panel now previews replay and has a confirm-gated Replay action.

Files Changed:
- `memory/replay.py`, memory routes/UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (62/62); Phase 2 gateway -> PASS (93/93); `bash validation/validate_all.sh` -> PASS.

Next:
- Publish Homebrew release/tap, add browser screenshot validation, or start scanner expansion.

## 2026-08-05 — Session 055: Homebrew release artifact builder

Prompt Summary:
- Continue to the next roadmap item after VS Code routing.

Decision:
- Added deterministic local release archive generation for Homebrew publishing.
- Strengthened the Homebrew formula wrapper, post-install setup, service caveats, and packaged shim component paths.
- Packaging validation now checks formula guidance, release archive contents/SHA, deterministic SHA, and packaged CLI imports.

Files Changed:
- `packaging/build_release.py`, `packaging/homebrew/spectrona.rb`, `packaging/README.md`, `packaging/validate_packaging.sh`, `spectrona-cli/bin/spectrona`, docs

Validation:
- Packaging -> PASS (32/32); `bash validation/validate_all.sh` -> PASS.

Next:
- Publish release/tap and validate real `brew install`/`brew services`, or continue with session replay.

## 2026-08-05 — Session 054: VS Code provider routing

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added VS Code workspace provider routing to the existing Claude/Codex routing manager.
- `spectrona protect vscode` now prints/applies/undos `.vscode/settings.json` terminal env routing with backup.
- Gateway/provider integration APIs and aggregate repair now detect, protect, unprotect, and repair VS Code provider routing.

Files Changed:
- `spectrona_cli/routing.py`, protect CLI/dispatch, integration manager, Phase 2/2C/packaging validation, docs

Validation:
- Phase 2 gateway -> PASS (93/93); CLI -> PASS (111/111); packaging -> PASS (24/24); `bash validation/validate_all.sh` -> PASS.

Next:
- Build session replay or published Homebrew tap validation.

## 2026-08-05 — Session 053: Raw memory protection

Prompt Summary:
- Continue building with validation/correlation and stop looping.

Decision:
- Memory writes now store redacted content by default; raw plaintext storage is policy-gated and disabled unless explicitly allowed.
- Added encrypted raw-memory opt-in with local key file support and storage metadata on memory API responses.
- Dashboard Memory rows can surface encrypted/plaintext/legacy storage state when relevant.

Files Changed:
- `memory/protection.py`, memory store/routes, gateway/CLI config defaults, dashboard UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (56/56); Phase 2 gateway -> PASS (91/91); CLI -> PASS (106/106); `bash validation/validate_all.sh` -> PASS.

Next:
- Build session replay or VS Code provider-routing integration.

## 2026-08-05 — Session 052: Runtime session extraction

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added `project_path` to runtime events with migration and provider route accounting.
- Added `GET/POST /memory/extract` to preview/apply redacted session summaries from runtime event metadata.
- Dashboard Memory panel now shows session extraction status and a confirm-gated Extract action.

Files Changed:
- `events/store.py`, provider route accounting, `memory/sessions.py`, memory API/UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (46/46); Phase 2 gateway -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add session replay or raw memory encryption/policy gate.

## 2026-08-05 — Session 051: Memory compaction

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added redacted memory compaction preview and confirmed apply flow for duplicate and stale low-importance memory.
- Applying compaction pins canonical duplicates, tags duplicate/stale candidates, and creates a redacted `session_summary`.
- Dashboard Memory panel now shows compaction status and a confirm-gated Compact action.

Files Changed:
- `memory/compact.py`, memory route models/API, dashboard UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (39/39); Phase 2 gateway -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add full session extraction or session replay.

## 2026-08-04 — Session 050: Memory audit timeline

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added `GET /memory/timeline` for metadata-only memory lifecycle events.
- Timeline joins memory events to redacted current memory metadata and preserves item lifecycle filtering through deletes.
- Dashboard Memory panel now shows recent created/updated/deleted/attached memory timeline rows.

Files Changed:
- `memory/timeline.py`, memory store event metadata, memory route models/API, dashboard UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (32/32); Phase 2 gateway -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add full session extraction, session replay, or compaction logic.

## 2026-08-04 — Session 049: Fresh context packages

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added `GET /memory/context` to generate a redacted fresh context package from memory items.
- Package generation uses existing search/type/source/tag/pinned filters and excludes stale memory by default.
- Dashboard Memory panel now shows a compact fresh context package preview backed by the new API.

Files Changed:
- `memory/context.py`, memory route models/API, dashboard UI, Phase 2/3 validation, docs

Validation:
- Phase 3 memory -> PASS (29/29); Phase 2 gateway -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add full session extraction, audit timeline, or compaction logic.

## 2026-08-04 — Session 048: Stale context detection

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added computed stale metadata for memory items using `memory_stale_after_days`, stale tags, pin override, age, and last attachment.
- Runtime memory injection now skips stale unpinned memory; dashboard shows stale badges/reasons.
- No DB migration was needed because staleness is computed at retrieval time.

Files Changed:
- `memory/staleness.py`, memory retrieval/API/runtime/UI, config defaults, Phase 2/3 validation, docs

Validation:
- Focused runtime memory validator -> PASS; Phase 3 memory -> PASS (27/27); Phase 2 gateway -> PASS (91/91); Phase 2 CLI -> PASS (106/106); `bash validation/validate_all.sh` -> PASS.

Next:
- Add full session extraction or compaction/fresh-context package generation.

## 2026-08-04 — Session 047: Runtime memory capture and injection

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added runtime memory capture for marked request/response text after gateway policy/response guard approval.
- Added opt-in relevant memory injection before OpenAI, Anthropic, and local-compatible provider forwarding.
- Runtime-captured memory and injected context are redacted; attachment events record item usage without raw secrets.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/memory/runtime.py`, provider routes, memory events API, Phase 3 validation, docs

Validation:
- Focused runtime memory validator -> PASS; `bash spectrona-gateway/validation/phase3_memory_routes_validate.sh` -> PASS (25/25); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add stale context detection/session extraction, or continue scanner expansion.

## 2026-08-04 — Session 046: Memory search and management

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added memory search/filter API over redacted content, source tool, memory type, tags, and pinned state.
- Added PATCH update/pin and confirmed DELETE routes; HTTP responses still return redacted content only.
- Dashboard Memory panel now has search/type/pinned filters plus Pin/Unpin/Delete actions and redacted/pinned badges.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/memory/{store,retrieve}.py`, `routes/memory.py`, dashboard UI, Phase 2/3 validation, docs

Validation:
- `bash spectrona-gateway/validation/phase3_memory_routes_validate.sh` -> PASS (22/22); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (91/91); `bash validation/validate_all.sh` -> PASS.

Next:
- Add runtime memory capture/retrieval/injection, or start scanner expansion.

## 2026-08-03 — Session 045: Local LLM fallback routing

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added opt-in local-only fallback routing through `local_fallbacks` / `SPECTRONA_LOCAL_FALLBACKS`.
- Gateway retries configured local fallback runtimes after selected-runtime request errors or 502/503/504 responses.
- Hosted fallback URLs are ignored so local traffic does not silently fail over to OpenAI/Anthropic.
- Fallback status is exposed through CLI integration status, `/providers/health`, `/integrations`, runtime events, token usage, and dashboard badges.

Files Changed:
- `spectrona-cli/src/spectrona_cli/local_llms.py`, integration manager/table output, gateway passthrough/local routes, dashboard UI, validation scripts, docs

Validation:
- Focused fallback validator -> PASS; `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (106/106); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (91/91); `bash packaging/validate_packaging.sh` -> PASS (24/24); `bash validation/validate_all.sh` -> PASS.

Next:
- Add memory search/delete/pin UI/API or start scanner expansion.

## 2026-08-03 — Session 044: Local LLM runtime selection

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added confirmed local runtime selection for Ollama, LM Studio, llama.cpp, and vLLM candidates.
- Selection patches Spectrona config with backup and updates the running gateway local provider settings without restart.
- Dashboard Provider Routes panel now exposes Select actions for non-selected local runtimes.

Files Changed:
- `spectrona-cli/src/spectrona_cli/local_llms.py`, gateway config/provider routes, dashboard UI, CLI/gateway validation, docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (105/105); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (89/89); `bash packaging/validate_packaging.sh` -> PASS (24/24); `bash validation/validate_all.sh` -> PASS.

Next:
- Add local fallback routing rules, or add memory search/delete/pin UI.

---

## 2026-08-03 — Session 043: Local LLM runtime discovery

Prompt Summary:
- Continue the roadmap with validation/correlation at each step.

Decision:
- Added local runtime presets/status for Ollama, LM Studio, llama.cpp, and vLLM.
- Exposed local runtime status through CLI integrations, gateway `/providers/health`, gateway `/integrations`, dashboard Provider Routes, and packaged layout validation.
- Runtime detection is status/health-only; provider selection and fallback routing remain open.

Files Changed:
- `spectrona-cli/src/spectrona_cli/local_llms.py`, integration manager/CLI wiring, gateway provider/integration routes, dashboard UI, validation scripts, docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (104/104); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (86/86); `bash packaging/validate_packaging.sh` -> PASS (24/24); `bash validation/validate_all.sh` -> PASS.

Next:
- Add config/UI provider selection and fallback routing, or add memory search/delete/pin UI.

---

## 2026-07-30 — Session 042: Token usage history dashboard

Prompt Summary:
- Continue with the next roadmap item after aggregate integration manager.

Decision:
- Extended token usage API with `today`, `by_day`, and `by_route` while preserving provider/model/client totals.
- Updated dashboard Token Usage panel with today/input/output summary and grouped usage bars.
- Summary cards now show calls/tokens for today with all-time notes.
- Token usage responses remain metadata-only and secret-free.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/events/store.py`, dashboard UI, gateway validation, docs

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (84/84); `bash validation/validate_all.sh` -> PASS.

Next:
- Continue local LLM endpoint detection or add memory search/delete/pin UI.

---

## 2026-07-29 — Session 041: Aggregate integration manager

Prompt Summary:
- Continue with the next roadmap item after CLI policy controls.

Decision:
- Added shared integration manager for provider routing and MCP app status/repair.
- Added `spectrona integrations status/repair`; repair requires `--confirm`.
- Added gateway `/integrations` and confirmed `/integrations/repair` APIs.
- Manager returns metadata-only JSON and reuses existing routing/MCP protect logic.

Files Changed:
- `spectrona-cli/src/spectrona_cli/integration_manager.py`, CLI/gateway route wiring, CLI/gateway/packaging validation, docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (103/103); `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (83/83); `bash packaging/validate_packaging.sh` -> PASS (24/24); `bash validation/validate_all.sh` -> PASS.

Next:
- Add token usage daily/model/app UI or continue local LLM endpoint detection.

---

## 2026-07-29 — Session 040: CLI policy controls

Prompt Summary:
- Continue after policy rollback APIs/UI controls.

Decision:
- Added `spectrona policy` CLI with status, presets, apply, backups, and restore subcommands.
- Mutating policy commands require `--confirm`.
- CLI policy apply/restore writes backups and returns metadata-only JSON when requested.
- Packaged Homebrew-style layout now validates policy command import/mutation behavior.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/policy.py`, CLI parser, CLI/packaging validation, docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (92/92); `bash packaging/validate_packaging.sh` -> PASS (22/22); `bash validation/validate_all.sh` -> PASS.

Next:
- Continue background integration manager or add token usage daily aggregation.

---

## 2026-07-27 — Session 039: Policy rollback APIs and UI controls

Prompt Summary:
- Continue after policy APIs and UI presets.

Decision:
- Added `/policy/backups` metadata API for `.spectrona.bak*` policy backups.
- Added confirmed `/policy/backups/{backup_id}/restore` API.
- Restore validates backup policy text and backs up the current policy before replacing it.
- Dashboard Policy panel now shows recent backups with Restore actions.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/routes/policy.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- Docs/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (77/77); `bash validation/validate_all.sh` -> PASS.

Next:
- Add CLI policy rollback command or continue background integration manager.

---

## 2026-07-27 — Session 038: Policy APIs and UI presets

Prompt Summary:
- Continue to the next tracked slice after policy dry-run mode.

Decision:
- Added shared policy presets: relaxed, balanced, strict.
- Added gateway `/policy` APIs for current policy status, preset metadata, preset preview, and confirmed preset apply.
- Policy apply writes a backup before replacing the active policy file.
- Dashboard now shows policy state and preset apply actions.

Files Changed:
- `policy-engine/src/policy_engine/presets.py`, gateway policy route/UI/app wiring, gateway/policy validation, docs

Validation:
- Focused policy/gateway checks passed; `bash validation/validate_all.sh` -> PASS.

Next:
- Continue background integration manager or add richer policy editing/rollback UX.

---

## 2026-07-26 — Session 037: Policy dry-run mode

Prompt Summary:
- Continue roadmap implementation with validation at each step.

Decision:
- Added policy dry-run behavior for gateway requests/responses and MCP tool input/output decisions.
- Dry-run records `would_*` actions and `dry_run_*` policy actions without blocking or redacting traffic.
- Event summaries and dashboard panels now expose would-block, would-approval, and would-redact counts.
- `spectrona init` writes `policy_dry_run: false`; `spectrona status` reports dry-run state.

Files Changed:
- `policy-engine`, `spectrona-gateway`, `runtime-guard`, `spectrona-cli`, validation helpers, docs

Validation:
- Focused policy/gateway/CLI/runtime checks passed; `bash validation/validate_all.sh` -> PASS.

Next:
- Add policy APIs/editor presets or continue toward background integration manager.

---

## 2026-07-26 — Session 036: MCP output redaction

Prompt Summary:
- Continue after gateway response-side DLP.

Decision:
- Added MCP tool response evaluation with the shared policy engine using output DLP findings.
- `tools/call` upstream responses are redacted before returning to the MCP client when output contains known secret prefixes.
- Strict policies can block or require approval on secret-bearing MCP outputs.
- MCP audit adds metadata-only response events; raw tool input/output payloads are never logged.

Files Changed:
- `runtime-guard/src/runtime_guard/mcp_proxy.py`
- `runtime-guard/validation/mcp_proxy_validate.py`
- `runtime-guard/validation/phase2_validate.sh`
- Docs/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `PYTHONPATH=runtime-guard/src:policy-engine/src python3 runtime-guard/validation/mcp_proxy_validate.py` -> PASS
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (17/17)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add policy dry-run mode that records would-block/would-redact decisions without enforcing them.

---

## 2026-07-26 — Session 035: Gateway response-side DLP

Prompt Summary:
- Continue after config secret migration.

Decision:
- Added response policy evaluation for model output bytes using the existing policy engine and DLP detector.
- Added shared `routes/response_guard.py` and wired OpenAI, Anthropic, and local-compatible routes through it.
- Response secrets are redacted before returning to clients; response policy metadata is included in runtime events.
- Fake upstream validation now returns a synthetic response secret and proves client output, runtime events, DLP summary, and audit logs stay redacted.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/policy.py`
- `spectrona-gateway/src/spectrona_gateway/routes/response_guard.py` (new)
- OpenAI/Anthropic/local route handlers
- Gateway passthrough validation and docs

Validation:
- `python3 spectrona-gateway/validation/passthrough_fake_upstream.py` -> PASS
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (66/66)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (83/83)
- `bash packaging/validate_packaging.sh` -> PASS (20/20)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add MCP output redaction or begin policy dry-run mode.

---

## 2026-07-26 — Session 034: Config secret migration

Prompt Summary:
- Continue to the next tracked item after Keychain-backed provider secrets.

Decision:
- Added `spectrona secrets migrate-config` to move plaintext config provider keys into the configured secret backend.
- Migration creates a `config.yaml.spectrona.bak*` backup before scrubbing `openai_api_key`, `anthropic_api_key`, and `local_api_key`.
- Command output and JSON are metadata-only; raw values are only available through explicit `spectrona secrets get`.
- Migration is idempotent after config scrub and works in the packaged Homebrew-style layout.

Files Changed:
- `spectrona-cli/src/spectrona_cli/secrets.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `packaging/validate_packaging.sh`
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (83/83)
- `bash packaging/validate_packaging.sh` -> PASS (20/20)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add gateway response-side DLP/policy hook before returning model output.

---

## 2026-07-26 — Session 033: Keychain-backed provider secrets

Prompt Summary:
- Continue roadmap implementation with validation at each step.

Decision:
- Added `spectrona_cli.secrets` with macOS Keychain default and deterministic file backend for tests.
- Added `spectrona secrets set/get/status/delete` and redacted provider status integration.
- Gateway now loads OpenAI, Anthropic, and local provider keys from stored secrets with env vars taking precedence.
- Validation isolates test secret stores so real user env/Keychain state cannot affect provider-health assertions.

Files Changed:
- `spectrona-cli/src/spectrona_cli/secrets.py` (new)
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/src/spectrona_cli/commands/status.py`
- `spectrona-gateway/src/spectrona_gateway/config.py`
- CLI/gateway/packaging validation fixtures and docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (77/77)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (64/64)
- `bash packaging/validate_packaging.sh` -> PASS (19/19)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add migration from plaintext config-file provider keys into the secret store with backup.

---

## 2026-07-26 — Session 032: Provider routing integration status/actions

Prompt Summary:
- Continue to the next tracked item after MCP app drift detection/repair.

Decision:
- Added shared `spectrona_cli.routing` helper for Claude/Codex provider routing status, apply, undo, drift, and repair metadata.
- Added `spectrona protect status --json` and table output.
- Gateway now exposes `/providers/integrations` plus confirmed protect/unprotect actions.
- Dashboard now shows Provider Routes and Provider Routing setup/repair/remove controls.

Files Changed:
- `spectrona-cli/src/spectrona_cli/routing.py` (new)
- `spectrona-cli/src/spectrona_cli/commands/protect.py`
- `spectrona-cli/src/spectrona_cli/commands/gateway.py`
- `spectrona-gateway/src/spectrona_gateway/routes/providers.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- CLI/gateway/packaging validation fixtures and docs

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (67/67)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (62/62)
- `bash packaging/validate_packaging.sh` -> PASS (18/18)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add Keychain-backed secret storage for upstream provider keys.

---

## 2026-07-26 — Session 031: MCP app drift detection and repair recommendations

Prompt Summary:
- Continue to the next tracked item after MCP app protect/unprotect API/dashboard actions.

Decision:
- Added metadata-only MCP app drift detection with `recommended_action` and `repair_available` status.
- Dashboard now shows drift/action state and uses Repair when protect is repairing a drifted config.
- CLI `spectrona mcp apps` now shows drift/action metadata without exposing server env values.
- Restore now recreates missing config paths when a Spectrona backup exists.

Files Changed:
- `runtime-guard/src/runtime_guard/mcp_apps.py`
- `runtime-guard/src/runtime_guard/mcp_config.py`
- `spectrona-cli/src/spectrona_cli/commands/mcp.py`
- `spectrona-gateway/src/spectrona_gateway/routes/mcp.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- Runtime/CLI/gateway validation fixtures and docs

Validation:
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (17/17)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (62/62)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (51/51)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add provider routing integration status/repair or start Keychain-backed secret storage.

---

## 2026-07-26 — Session 030: MCP app protect/unprotect API/dashboard actions

Prompt Summary:
- Continue to the next tracked item after MCP app status API/dashboard.

Decision:
- Added confirmed POST endpoints for MCP app protect/unprotect behind the gateway.
- Dashboard Protected Apps rows now show Protect/Restore buttons when actions are available.
- POST action endpoints require `confirm: true` and return metadata-only mutation results.
- Gateway-applied wrapping now passes configured policy path and MCP audit log to the proxy command.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/routes/mcp.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- Docs/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (49/49)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (62/62)
- `bash packaging/validate_packaging.sh` -> PASS (17/17)
- `bash validation/validate_all.sh` -> PASS
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (48/48, docs-aware final check)

Next:
- Add config drift detection and repair recommendations for app integrations.

---

## 2026-07-26 — Session 029: MCP app status API/dashboard

Prompt Summary:
- Continue to the next tracked item after MCP app protect/unprotect.

Decision:
- Added gateway `GET /mcp/apps` using `runtime_guard.mcp_apps.discover_mcp_apps`.
- Added `SPECTRONA_MCP_APP_HOME` / `paths.mcp_app_home` for isolated app-status discovery.
- Dashboard now fetches `/mcp/apps` and shows a Protected Apps metric and panel.
- CLI gateway startup now includes `runtime-guard/src` in its runtime `PYTHONPATH`.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/config.py`
- `spectrona-gateway/src/spectrona_gateway/routes/mcp.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `spectrona-cli/src/spectrona_cli/commands/gateway.py`
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (43/43)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (62/62)
- `bash packaging/validate_packaging.sh` -> PASS (17/17)
- `bash validation/validate_all.sh` -> PASS
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (48/48, docs-aware final check)

Next:
- Add consent-based gateway action endpoints and dashboard buttons for MCP app protect/unprotect.

---

## 2026-07-26 — Session 028: MCP app protect/unprotect

Prompt Summary:
- Continue to the next tracked item after MCP app discovery/status.

Decision:
- Added app-level MCP mutation helpers on top of discovery and existing wrap/restore code.
- Added `spectrona mcp protect <app-id>` and `spectrona mcp unprotect <app-id>`.
- Protect wraps detected app configs in place with `.spectrona.bak`; unprotect restores that backup.
- JSON and terminal mutation output stay metadata-only and do not print MCP env payloads.

Files Changed:
- `runtime-guard/src/runtime_guard/mcp_apps.py`
- `runtime-guard/validation/mcp_apps_protect_validate.py` (new)
- `runtime-guard/validation/phase2_validate.sh`
- `spectrona-cli/src/spectrona_cli/commands/mcp.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `packaging/validate_packaging.sh`
- Docs/README/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (17/17)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (62/62)
- `bash packaging/validate_packaging.sh` -> PASS (17/17)
- `bash validation/validate_all.sh` -> PASS
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (48/48, docs-aware final check)

Next:
- Expose MCP app integration status/actions through gateway APIs and the dashboard.

---

## 2026-07-26 — Session 027: MCP app discovery/status

Prompt Summary:
- Continue to the next tracked item after MCP config wrap/undo.

Decision:
- Added `runtime_guard.mcp_apps` for read-only MCP config discovery/status.
- Added `spectrona mcp apps` and `spectrona mcp apps --json`.
- Detects Claude Code, Claude Desktop, Codex, VS Code user, and workspace MCP config locations.
- Reports missing, invalid, unprotected, protected, and partial states without printing server env values.

Files Changed:
- `runtime-guard/src/runtime_guard/mcp_apps.py` (new)
- `runtime-guard/src/runtime_guard/mcp_config.py`
- `runtime-guard/validation/mcp_apps_validate.py` (new)
- `runtime-guard/validation/phase2_validate.sh`
- `spectrona-cli/src/spectrona_cli/commands/mcp.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `packaging/validate_packaging.sh`
- Docs/README/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (15/15)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (57/57)
- `bash packaging/validate_packaging.sh` -> PASS (15/15)
- `bash validation/validate_all.sh` -> PASS
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (48/48, docs-aware final check)

Next:
- Add consent-based MCP app protect/repair flow or expose app integration state in the dashboard.

---

## 2026-07-26 — Session 026: MCP config wrap/undo

Prompt Summary:
- Continue to the next tracked item after MCP runtime proxy MVP.

Decision:
- Added `runtime_guard.mcp_config` to import and wrap MCP config files.
- Added `spectrona mcp wrap` with `--output` and explicit `--apply` modes.
- Added backup-based `spectrona mcp undo`.
- Wrapped servers keep original env and upstream command behind `spectrona mcp proxy`; terminal output stays metadata-only.

Files Changed:
- `runtime-guard/src/runtime_guard/mcp_config.py` (new)
- `runtime-guard/validation/mcp_config_wrap_validate.py` (new)
- `runtime-guard/validation/phase2_validate.sh`
- `spectrona-cli/src/spectrona_cli/commands/mcp.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `packaging/validate_packaging.sh`
- Docs/README/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (12/12)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (54/54)
- `bash packaging/validate_packaging.sh` -> PASS (14/14)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add app-specific MCP config discovery and setup/repair for Claude, Codex, and VS Code.

---

## 2026-07-26 — Session 025: MCP runtime proxy MVP

Prompt Summary:
- Continue to the next tracked item after runtime Blocks/DLP dashboard panels.

Decision:
- Added `runtime_guard` package with MCP stdio JSON-RPC proxy MVP.
- Proxy evaluates `tools/call` with shared `policy-engine`, detects shell/filesystem risk, redacts secret-bearing inputs, and writes metadata-only MCP audit logs.
- Added `spectrona mcp proxy` CLI entrypoint and included `runtime-guard` in Homebrew-style packaging.
- Automatic import/wrapping of existing MCP server configs remains open.

Files Changed:
- `runtime-guard/` package, README, and validation
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/src/spectrona_cli/commands/mcp.py` (new)
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `packaging/homebrew/spectrona.rb`
- `packaging/validate_packaging.sh`
- Docs/TODO/ROADMAP/PHASES/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash runtime-guard/validation/phase2_validate.sh` -> PASS (9/9)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (49/49)
- `bash packaging/validate_packaging.sh` -> PASS (13/13)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add MCP config import/wrap command so Claude/Codex/VS Code MCP servers can be routed through the proxy.

---

## 2026-07-25 — Session 024: runtime blocks and DLP panels

Prompt Summary:
- Continue to the next tracked item after MCP scan visibility.

Decision:
- Added metadata-only `/events/blocks` and `/events/dlp` summary APIs on top of the existing runtime event store.
- Dashboard now fetches block and DLP summaries and shows dedicated Runtime Blocks and DLP Activity panels.
- Summary cards now use full block/DLP aggregates instead of only recent table rows.
- Validation creates allowed, redacted, and blocked events in the same gateway DB; policy helper also validates approval-required aggregation.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/events/store.py`
- `spectrona-gateway/src/spectrona_gateway/routes/events.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `spectrona-gateway/validation/policy_gateway_validate.py`
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache_compile ... py_compile ...` -> PASS
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (41/41)
- `bash validation/validate_all.sh` -> PASS

Next:
- Begin MCP runtime proxy MVP.

---

## 2026-07-25 — Session 023: MCP scan API/dashboard panel

Prompt Summary:
- Continue to the next tracked item after the read-only dashboard.

Decision:
- Added gateway `GET /mcp/scan` using existing `mcp_inspector.scanner.scan_mcp_config()`.
- Added config/env support for `mcp_config_path` and `repo_root`.
- Added dashboard MCP risk card and MCP scan panel with severity, server name, rule id, and remediation text.
- Added `mcp-inspector/src` to CLI gateway runtime `PYTHONPATH` for side-by-side packaged installs.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/routes/mcp.py` (new)
- `spectrona-gateway/src/spectrona_gateway/app.py`
- `spectrona-gateway/src/spectrona_gateway/config.py`
- `spectrona-gateway/src/spectrona_gateway/ui/index.html`
- `spectrona-cli/src/spectrona_cli/commands/gateway.py`
- `spectrona-cli/src/spectrona_cli/commands/config_file.py`
- `spectrona-cli/validation/gateway_lifecycle_validate.py`
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache_compile ... py_compile ...` -> PASS
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (38/38)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (47/47)
- `bash packaging/validate_packaging.sh` -> PASS (11/11)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add dedicated runtime blocks/DLP dashboard panels or begin MCP runtime proxy MVP.

---

## 2026-07-25 — Session 022: read-only UI dashboard

Prompt Summary:
- Continue to the next tracked item after event/token accounting.

Decision:
- Added dependency-free gateway-served UI at `/ui`.
- Dashboard reads `/health`, `/providers/health`, `/events/recent`, `/events/token-usage`, and `/memory/items`.
- UI shows gateway status, call count, token totals, block count, live traffic, provider health, usage by provider, and recent memory.
- Added gateway package-data metadata for `ui/*.html`.
- Added UI asset checks to gateway and packaging validation.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/ui/index.html` (new)
- `spectrona-gateway/src/spectrona_gateway/routes/ui.py` (new)
- `spectrona-gateway/src/spectrona_gateway/app.py`
- `spectrona-gateway/pyproject.toml`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `packaging/validate_packaging.sh`
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (35/35)
- `bash packaging/validate_packaging.sh` -> PASS (11/11)
- Manual local API smoke against `/ui` and backing APIs -> PASS
- Browser plugin Node execution and shell `node` were unavailable, so screenshot validation was not run.
- `bash validation/validate_all.sh` -> PASS

Next:
- Add MCP scan results API/view or begin MCP runtime proxy MVP.

---

## 2026-07-25 — Session 021: event/token accounting

Prompt Summary:
- Continue with the next tracked item after policy engine MVP.

Decision:
- Added SQLite `runtime_events` table using existing `SPECTRONA_DB_PATH`.
- Added model-call event recording for OpenAI, Anthropic, local, blocked, approval-required, redacted, and upstream error paths.
- Added token extraction from OpenAI-compatible and Anthropic `usage` fields.
- Added token estimation fallback when usage fields are absent.
- Added `/events/recent` and `/events/token-usage` API routes for future UI.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/events/` (new)
- `spectrona-gateway/src/spectrona_gateway/routes/events.py`, `model_accounting.py` (new)
- OpenAI/Anthropic/local gateway routes
- Gateway validation and fake upstream validation
- Docs/TODO/ROADMAP/VALIDATION/MEMORY/SESSION_LOG

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (32/32)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (47/47)
- `bash packaging/validate_packaging.sh` -> PASS (9/9)
- `bash spectrona-gateway/validation/phase3_memory_routes_validate.sh` -> PASS (11/11)
- `bash validation/validate_all.sh` -> PASS

Next:
- Build read-only UI dashboard backed by `/events/recent`, `/events/token-usage`, `/providers/health`, and MCP scan output.

---

## 2026-07-25 — Session 020: policy engine MVP

Prompt Summary:
- Implement Policy Engine MVP logically, reuse existing code, integrate correctly, validate each step.

Decision:
- Added dependency-free `policy-engine` Python package with YAML-subset policy loading.
- Supports `allow`, `deny`, `redact`, and `require_approval` decisions.
- Matches route, provider, client/app, model, DLP count, filesystem risk, and shell risk.
- `spectrona init` now writes `~/.spectrona/policy.yaml`; gateway loads `SPECTRONA_POLICY_PATH` or config path.
- Gateway enforces request policy before mock/passthrough and audits policy decisions.

Files Changed:
- `policy-engine/` package, fixtures, validation
- `spectrona-gateway/src/spectrona_gateway/policy.py`, routes, config, audit, DLP
- `spectrona-cli` init/status/gateway path handling
- packaging formula/validation and master validation

Validation:
- `bash policy-engine/validation/policy_validate.sh` -> PASS (12/12)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (26/26)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (47/47)
- `bash packaging/validate_packaging.sh` -> PASS (9/9)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add event/token accounting schema, then read-only UI dashboard backed by real runtime events.

---

## 2026-07-25 — Session 019: implementation TODO tracking

Prompt Summary:
- Add the background guard, UI, secrets, memory, MCP runtime, and install work into the TODO list.

Decision:
- Created `docs/TODO.md` as the detailed implementation backlog.
- Added required proof rules: code, validation, docs, no secret leakage, rollback for config changes.
- Prioritized runtime policy, MCP control, keychain secrets, background integration, UI, token accounting, and Homebrew publishing.
- Linked TODO from `docs/ROADMAP.md`.
- Added TODO existence to phase1 docs validation.

Validation:
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (48/48)
- `bash validation/validate_all.sh` -> PASS

Next:
- Start with runtime policy engine MVP or event/token accounting schema.

---

## 2026-05-09 — Session 001: Bootstrap

Prompt Summary:
- Bootstrap full spectrona scaffold per system prompt specification.

Decision:
- Phase 1 active: mcp-inspector scanner only
- Rules in YAML, local-first, OSS scanner / private guard+db
- Four rule files created with full initial rule IDs
- Fixture files created (unsafe + safe + sample report)

Files Changed:
- CLAUDE.md
- mcp-inspector/README.md
- mcp-inspector/rules/mcp-risk-rules.yaml (7 rules)
- mcp-inspector/rules/claude-risk-rules.yaml (4 rules)
- mcp-inspector/rules/cursor-risk-rules.yaml (3 rules)
- mcp-inspector/rules/secrets-risk-rules.yaml (4 rules)
- mcp-inspector/examples/unsafe-mcp-configs/basic-unrestricted-filesystem.json
- mcp-inspector/examples/safe-mcp-configs/scoped-filesystem.json
- mcp-inspector/examples/sample-reports/unsafe-report.json
- mcp-inspector/validation/phase1_validate.sh
- runtime-guard/README.md, validation/phase2_validate.sh
- claudedb/README.md, validation/phase3_validate.sh
- policy-engine/README.md
- docs/MEMORY.md, PHASES.md, VALIDATION.md, DECISIONS.md, SESSION_LOG.md
- docs/ROADMAP.md, ARCHITECTURE.md, COMPETITIVE_NOTES.md
- validation/README.md, validate_all.sh

Validation:
- bash validation/validate_all.sh → PASS (scaffold checks only)
- Scanner logic: NOT IMPLEMENTED

Next:
- Implement Phase 1 scanner in Python or Go
- Start with: mcp-inspector scan mcp → parse JSON → apply mcp-risk-rules.yaml + secrets-risk-rules.yaml → print terminal report
- Exact entry point: mcp-inspector/src/scanner.py (or main.go)
- First target: detect MCP_FS_OUTSIDE_REPO and SECRET_KNOWN_PREFIX from the unsafe fixture

---

## 2026-05-10 — Session 002: Phase 1 Scanner MVP

Prompt Summary:
- Implement filesystem boundary detection (MCP_FS_OUTSIDE_REPO only). No shell, no secrets yet.

Decision:
- Python, src layout, no install required (bin/mcp-inspector shim sets PYTHONPATH)
- Exit 1 on HIGH/CRITICAL findings, exit 0 on clean, exit 2 on error

Files Changed:
- mcp-inspector/src/mcp_inspector/__init__.py
- mcp-inspector/src/mcp_inspector/__main__.py
- mcp-inspector/src/mcp_inspector/cli.py
- mcp-inspector/src/mcp_inspector/models.py
- mcp-inspector/src/mcp_inspector/parsers/mcp_parser.py
- mcp-inspector/src/mcp_inspector/detectors/fs_detector.py
- mcp-inspector/src/mcp_inspector/reporters/terminal.py
- mcp-inspector/src/mcp_inspector/reporters/json_reporter.py
- mcp-inspector/bin/mcp-inspector (shell shim)
- mcp-inspector/pyproject.toml
- mcp-inspector/examples/safe-mcp-configs/repo-only-filesystem.json
- mcp-inspector/validation/phase1_validate.sh (updated with scanner tests)
- docs/VALIDATION.md, MEMORY.md, SESSION_LOG.md

Validation:
- bash validation/validate_all.sh → PASS (32/32)
- Unsafe fixture → MCP_FS_OUTSIDE_REPO HIGH, exit 1
- Safe fixture → clean, exit 0
- JSON output → valid, summary.high=1 on unsafe

Next:
- Phase 1 MVP complete for filesystem detection
- Recommended next: add secrets detection (SECRET_KNOWN_PREFIX) to detect sk-proj- in unsafe fixture
- Entry point: add detectors/secrets_detector.py, wire into cli.py _run_scan()

---

## 2026-05-25 — Session 003: Phase 1A/1B + Gateway + CLI + Memory

Prompt Summary:
- Add secrets detection, scanner.py API, FastAPI gateway, spectrona-cli, memory foundation.

Decisions:
- Python 3.10 (existing constraint). FastAPI installed system-wide.
- Public scanner API in scanner.py; cli.py delegates to it.
- Gateway runs MOCK_MODE by default; real forwarding not yet wired.
- Memory raw content preserved; redacted_content written via DLP.

Files Changed:
- mcp-inspector/src/mcp_inspector/detectors/secrets_detector.py (new)
- mcp-inspector/src/mcp_inspector/scanner.py (new)
- mcp-inspector/src/mcp_inspector/cli.py (updated — delegates to scanner.py)
- mcp-inspector/validation/phase1_validate.sh (updated — +7 secrets checks)
- spectrona-gateway/src/spectrona_gateway/{app,config,audit,dlp}.py (new)
- spectrona-gateway/src/spectrona_gateway/routes/{health,openai_compat,anthropic_compat}.py (new)
- spectrona-gateway/src/spectrona_gateway/providers/passthrough.py (new)
- spectrona-gateway/src/spectrona_gateway/memory/{store,retrieve,compact}.py (new)
- spectrona-gateway/pyproject.toml, validation/phase2_gateway_validate.sh (new)
- spectrona-cli/src/spectrona_cli/{cli,__init__,__main__}.py (new)
- spectrona-cli/src/spectrona_cli/commands/{status,gateway,logs,protect}.py (new)
- spectrona-cli/bin/spectrona, pyproject.toml (new)
- validation/validate_all.sh (updated — includes gateway phase)

Validation:
- bash validation/validate_all.sh → PASS (55 checks: 39 Phase1 + 16 Phase2 gateway)
- Secrets: CRITICAL finding, no raw secret in terminal/JSON output
- Gateway: /health, /openai/v1/chat/completions, /anthropic/v1/messages all PASS
- DLP: dlp_findings_count=1 on secret request, audit log clean
- Memory: insert → redacted_content verified, list/events working

Next:
- Expose memory API routes in gateway (/memory/items, /memory/events)
- Add real provider passthrough (upstream_url from env)
- Add more mcp-inspector detectors (MCP_SHELL_UNRESTRICTED, CLAUDE_HUGE_CONTEXT)
- Add spectrona scan command to CLI (wraps mcp-inspector scanner)

---

## 2026-05-25 — Session 004: Phase 3A + 2C + 1C

Prompt Summary:
- Memory HTTP routes, CLI validation, shell detector.

Decisions:
- GET /memory/items returns redacted_content as `content` field — never exposes raw secrets over HTTP.
- Shell detection: tokens checked in server name + args; direct shell binary in command field also triggers.
- CLI validation: print-only assertion checks output text, not filesystem — avoids macOS wc -l whitespace bug.

Files Changed:
- spectrona-gateway/src/spectrona_gateway/routes/memory.py (new)
- spectrona-gateway/src/spectrona_gateway/app.py (updated — memory router added)
- spectrona-gateway/validation/phase3_memory_routes_validate.sh (new)
- spectrona-cli/validation/phase2_cli_validate.sh (new)
- mcp-inspector/src/mcp_inspector/detectors/shell_detector.py (new)
- mcp-inspector/src/mcp_inspector/scanner.py (updated — added shell_detector)
- mcp-inspector/validation/phase1_validate.sh (updated — +4 shell checks, +1 scaffold)

Validation:
- bash validation/validate_all.sh → PASS (59 checks: 43 Phase1 + 16 Phase2-gateway)
- bash spectrona-gateway/validation/phase3_memory_routes_validate.sh → PASS (11/11)
- bash spectrona-cli/validation/phase2_cli_validate.sh → PASS (16/16)
- Total verified: 86 checks across all scripts

Next:
- Add spectrona scan command to CLI (import scanner.scan_mcp_config)
- Wire phase3 + phase2-cli scripts into validate_all.sh
- Next detector: CLAUDE_HUGE_CONTEXT or MCP_UNPINNED_PACKAGE

---

## 2026-07-12 — Session 005: spectrona scan + validation gate wiring

Prompt Summary:
- Continue from Session 004 next steps.

Decisions:
- Added `spectrona scan mcp [path]` as a thin wrapper around `mcp_inspector.scanner.scan_mcp_config`.
- `spectrona scan mcp --json` preserves scanner JSON and exit semantics: 1 for HIGH/CRITICAL, 0 clean, 2 errors.
- Active Python baseline aligned to 3.9 because local `python3` is 3.9.6 and validation uses `python3`.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/scan.py` (new)
- `spectrona-cli/src/spectrona_cli/cli.py`, `commands/status.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `validation/validate_all.sh`
- Python 3.9 annotation compatibility in mcp-inspector and gateway memory modules
- `pyproject.toml` requires-python aligned to `>=3.9` for active packages
- `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (23/23)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (16/16, outside sandbox for localhost bind)
- `bash spectrona-gateway/validation/phase3_memory_routes_validate.sh` -> PASS (11/11, outside sandbox for localhost bind)
- `bash validation/validate_all.sh` -> PASS (full gate; runtime-guard and ClaudeDB placeholders skipped)

Next:
- Implement next detector: `CLAUDE_HUGE_CONTEXT` or `MCP_UNPINNED_PACKAGE`.
- Consider adding `spectrona scan` default target alias if CLI should scan MCP config without explicit `mcp`.

---

## 2026-07-12 — Session 006: MCP_UNPINNED_PACKAGE detector

Prompt Summary:
- Continue from Session 005 next detector recommendation.

Decision:
- Implemented `MCP_UNPINNED_PACKAGE` before Claude config scanning because MCP fixtures already express pinned vs unpinned packages.
- Detector is MEDIUM severity, so it does not change unsafe exit semantics beyond existing HIGH/CRITICAL findings.

Files Changed:
- `mcp-inspector/src/mcp_inspector/detectors/package_detector.py` (new)
- `mcp-inspector/src/mcp_inspector/scanner.py`
- `mcp-inspector/validation/phase1_validate.sh`
- `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- `bash mcp-inspector/validation/phase1_validate.sh` -> PASS (47/47)
- `bash validation/validate_all.sh` -> PASS

Next:
- Implement `CLAUDE_HUGE_CONTEXT` detector or add MCP audit-log absence detection (`MCP_NO_AUDIT_LOG`).

---

## 2026-07-12 — Session 007: install/routing roadmap expansion

Prompt Summary:
- Add the one-command install, Claude/Codex routing, MCP runtime control, and local LLM gateway vision to the roadmap.

Decision:
- Rewrote `docs/ROADMAP.md` around the target product flow: `brew install spectrona`, `spectrona init`, `spectrona start`.
- Added explicit phases for installable gateway, Homebrew packaging, Claude/Codex routing, MCP runtime control, local LLM adapters, runtime policy, and memory.
- Kept current built status clear: scanner + mock gateway + CLI foundation exists; automatic routing and runtime MCP enforcement are future work.

Files Changed:
- `docs/ROADMAP.md`
- `docs/MEMORY.md`

Validation:
- Pending after roadmap update.

---

## 2026-07-12 — Session 008: real provider passthrough

Prompt Summary:
- Continue building toward installable gateway/productization roadmap.

Decision:
- Implemented real OpenAI and Anthropic passthrough for `SPECTRONA_MOCK_MODE=false`.
- Upstreams are configured through env vars:
  - `SPECTRONA_OPENAI_BASE_URL`, `SPECTRONA_OPENAI_API_KEY` or `OPENAI_API_KEY`
  - `SPECTRONA_ANTHROPIC_BASE_URL`, `SPECTRONA_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY`
  - `SPECTRONA_ANTHROPIC_VERSION`
- Validation uses local fake upstreams, not real provider calls.

Files Changed:
- `spectrona-gateway/src/spectrona_gateway/config.py`
- `spectrona-gateway/src/spectrona_gateway/providers/passthrough.py`
- `spectrona-gateway/src/spectrona_gateway/routes/openai_compat.py`
- `spectrona-gateway/src/spectrona_gateway/routes/anthropic_compat.py`
- `spectrona-gateway/validation/passthrough_fake_upstream.py`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (18/18)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add `spectrona init` and a real `~/.spectrona/config.yaml` configuration path.

---

## 2026-07-12 — Session 009: spectrona init + config file loading

Prompt Summary:
- Continue building and validate each step/module flow.

Decision:
- Added `spectrona init` to create `~/.spectrona/config.yaml` and `~/.spectrona/logs`.
- Added a constrained Spectrona YAML reader instead of introducing a new dependency.
- Gateway reads config file values first, then environment variables override them.
- CLI gateway/status commands read the same config file for host/port.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/config_file.py` (new)
- `spectrona-cli/src/spectrona_cli/commands/init.py` (new)
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/src/spectrona_cli/commands/gateway.py`
- `spectrona-cli/src/spectrona_cli/commands/status.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `spectrona-gateway/src/spectrona_gateway/config.py`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (30/30)
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (19/19)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add `spectrona stop/restart` or background service mode for the gateway.

---

## 2026-07-12 — Session 010: gateway lifecycle commands

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added background process controls before OS service/LaunchAgent work.
- Gateway process state is tracked with `~/.spectrona/gateway.pid`.
- Background logs go to `~/.spectrona/logs/gateway.log`.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/gateway.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/gateway_lifecycle_validate.py` (new)
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `python3 spectrona-cli/validation/gateway_lifecycle_validate.py` -> PASS outside sandbox for localhost bind
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (33/33) outside sandbox for localhost bind
- `bash validation/validate_all.sh` -> PASS

Next:
- Add top-level aliases: `spectrona start`, `spectrona stop`, `spectrona restart`, or move to macOS LaunchAgent/Homebrew service support.

---

## 2026-07-12 — Session 011: top-level gateway lifecycle aliases

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added top-level lifecycle aliases over the already-tested gateway process controls:
  - `spectrona start`
  - `spectrona stop`
  - `spectrona restart`
- Kept `spectrona gateway start/stop/restart` intact.
- Updated lifecycle validation to exercise the product target flow: `spectrona init`, `spectrona start`, health, `spectrona restart`, `spectrona stop`.

Files Changed:
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/gateway_lifecycle_validate.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `python3 spectrona-cli/validation/gateway_lifecycle_validate.py` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (34/34)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add macOS LaunchAgent/Homebrew service support or start Claude/Codex config detection/apply/undo.

---

## 2026-07-12 — Session 012: protect apply/undo

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added reversible Claude/Codex routing setup before LaunchAgent/Homebrew service work.
- Claude apply writes a Spectrona-managed env file, defaulting to `~/.spectrona/claude.env`.
- Codex apply patches a managed TOML block into the target config, defaulting to `~/.codex/config.toml`, and creates a backup.
- Undo removes only the Spectrona-managed block.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/protect.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (38/38)
- `bash validation/validate_all.sh` -> PASS

Next:
- Improve provider credential handling/keychain support, or add macOS LaunchAgent/Homebrew service support.

---

## 2026-07-12 — Session 013: LaunchAgent service plist support

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added safe LaunchAgent plist generation/install/uninstall before launchctl automation.
- `spectrona service install` writes plist only; it prints explicit load/unload commands and does not call `launchctl`.
- Validation uses a temp LaunchAgents directory via `SPECTRONA_LAUNCH_AGENTS_DIR`.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/service.py` (new)
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (42/42)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add LaunchAgent load/unload automation or start Homebrew formula/package layout.

---

## 2026-07-12 — Session 014: LaunchAgent load/unload commands

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added `spectrona service load` and `spectrona service unload` backed by `launchctl`.
- Added `--dry-run` for safe validation and command inspection.
- Full launchctl lifecycle is not yet validated against the real user launchd domain.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/service.py`
- `spectrona-cli/src/spectrona_cli/cli.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (44/44)
- `bash validation/validate_all.sh` -> PASS

Next:
- Build Homebrew formula/package layout, or validate real launchctl load/unload manually on macOS.

---

## 2026-07-12 — Session 016: Homebrew formula and packaged layout validation

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added Homebrew formula template using side-by-side `libexec` layout for `mcp-inspector`, `spectrona-cli`, and `spectrona-gateway`.
- Added packaging validation to the master gate.
- Formula includes a `service do` block using `spectrona start --foreground`.

Files Changed:
- `packaging/homebrew/spectrona.rb` (new)
- `packaging/validate_packaging.sh` (new)
- `validation/validate_all.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- `bash packaging/validate_packaging.sh` -> PASS (7/7)
- `bash validation/validate_all.sh` -> PASS

Next:
- Replace formula placeholder URL/SHA for a real release, or add Homebrew tap docs.

---

## 2026-07-22 — Session 017: upstream provider health checks

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added gateway route `GET /providers/health`.
- Default mode reports provider config/key state without contacting upstreams.
- `?live=true` performs short live checks against configured provider health paths.
- Default health path for OpenAI and Anthropic is `/models`; config/env can override it.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/config_file.py`
- `spectrona-gateway/src/spectrona_gateway/config.py`
- `spectrona-gateway/src/spectrona_gateway/providers/passthrough.py`
- `spectrona-gateway/src/spectrona_gateway/routes/providers.py` (new)
- `spectrona-gateway/src/spectrona_gateway/app.py`
- `spectrona-gateway/validation/passthrough_fake_upstream.py`
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (21/21)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add local LLM provider adapter support or begin MCP runtime proxy groundwork.

---

## 2026-07-22 — Session 018: local OpenAI-compatible provider

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Added `/local/v1/chat/completions` as a generic OpenAI-compatible local model route.
- Local provider config defaults to `http://127.0.0.1:11434/v1` and does not require an API key.
- Provider health now includes local status and optional live checks.
- `spectrona init` and `spectrona status` include local provider settings without leaking optional keys.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/config_file.py`, `status.py`
- `spectrona-gateway/src/spectrona_gateway/config.py`, `app.py`
- `spectrona-gateway/src/spectrona_gateway/providers/passthrough.py`
- `spectrona-gateway/src/spectrona_gateway/routes/local_compat.py` (new)
- `spectrona-gateway/validation/phase2_gateway_validate.sh`
- `spectrona-gateway/validation/passthrough_fake_upstream.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-gateway/validation/phase2_gateway_validate.sh` -> PASS (23/23)
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (46/46)
- `bash validation/validate_all.sh` -> PASS

Next:
- Add dedicated Ollama/LM Studio/llama.cpp/vLLM adapters or begin MCP runtime proxy groundwork.

---

## 2026-07-12 — Session 015: detailed status checks

Prompt Summary:
- Continue building with validation/correlation at each step.

Decision:
- Completed the roadmap item for `spectrona status` checking gateway, config, providers, logs, memory DB, and mode.
- Provider keys are shown only as configured/missing, never printed.
- Status now uses configured log and DB paths instead of hard-coded `~/.spectrona/logs`.

Files Changed:
- `spectrona-cli/src/spectrona_cli/commands/status.py`
- `spectrona-cli/validation/phase2_cli_validate.sh`
- `docs/ROADMAP.md`, `docs/VALIDATION.md`, `docs/MEMORY.md`, `docs/SESSION_LOG.md`

Validation:
- Static compile with `PYTHONPYCACHEPREFIX=/tmp/spectrona_pycache` -> PASS
- `bash spectrona-cli/validation/phase2_cli_validate.sh` -> PASS (46/46)
- `bash validation/validate_all.sh` -> PASS

Next:
- Build Homebrew formula/package layout, or validate real launchctl load/unload manually on macOS.
