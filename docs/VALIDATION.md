# Validation State

## Master command

```bash
bash validation/validate_all.sh
```

---

## Pytest — regression suite

**Script:** `validation/pytest_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] `pytest.ini` exists and discovers tests under `tests/`
- [x] `python3 -m pytest` runs from the repo root
- [x] F1 permanent regression passes for args/nested secret scanning and redacted output
- [x] F2 R5/R7 regression passes for advisory dry-run default and ordinary-English non-risk behavior
- [x] F2 direct shell-risk detector reproduction passes; genuine shell tools and schema-declared command fields still detect
- [x] F3 gateway auth reproduction passes without opening a listening socket
- [x] F4 proxy notification desync reproduction is present as strict xfail until R10
- [x] F5 DLP credential-format reproduction passes for all reviewed formats
- [x] F5 benign corpus has zero findings for UUIDs, git SHAs, lockfile hashes, base64 image data, and normal prose
- [x] F6 policy schema validation reproduction passes
- [x] F7 noisy correct-config reproduction passes
- [x] MCP, Claude, Cursor, and repo detector IDs are asserted through direct scanner API tests
- [x] Detector regression tests assert raw fixture secrets and raw risky text are absent from finding evidence
- [x] R8 seed corpus benchmark contract is asserted from pytest
- [x] R8 harvester query fan-out, URL encoding, fetch-skip behavior, deduplication, and JSON extraction are asserted from pytest
- [x] R8 labeling queue contract is asserted from pytest
- [x] R8 labeled corpus promotion contract is asserted from pytest

---

## Corpus — precision benchmark

**Script:** `validation/corpus_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] `validation/corpus_benchmark.py` exists and compiles
- [x] `validation/harvest_mcp_corpus.py` exists and compiles
- [x] `validation/corpus_label_queue.py` exists and compiles
- [x] `validation/corpus_promote_labeled.py` exists and compiles
- [x] Redacted seed corpus exists under `validation/corpus/`
- [x] Reviewed corpus has at least 199 labeled cases
- [x] Benchmark reports per-rule precision and recall
- [x] Measured rules pass the 95% precision gate on the 199-case reviewed corpus
- [x] Harvester defaults fan out across common MCP query shapes
- [x] Token-backed GitHub harvest produced a redacted unlabeled queue for human review
- [x] One hundred eighty-seven public GitHub queue records were manually reviewed and promoted into the benchmark corpus
- [x] Benchmark reports a measured `MCP_UNPINNED_PACKAGE` recall gap: 80 true positives, 5 false negatives, 0 false positives
- [x] Corpus-backed shell detector precision fix excludes package-name substring noise
- [x] Labeling queue helper writes stratified unlabeled records with scanner predictions
- [x] Promotion helper rejects unlabeled queue records before corpus write
- [x] Corpus excludes raw reviewed secret samples

---

## Phase 1 — mcp-inspector

**Script:** `mcp-inspector/validation/phase1_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS — master gate passed.

**Checks:**
- [x] Rule files exist and non-empty
- [x] Rule count minimums met
- [x] MCP, Claude, Cursor, and repo fixture files exist and are valid JSON where applicable
- [x] Sample report documents expected findings
- [x] Docs files exist
- [x] Implementation TODO file exists
- [x] Source files exist (cli, models, MCP/Claude/Cursor/Repo parsers, MCP/Claude/Cursor/Repo/prompt-injection/postinstall detectors, terminal/JSON/HTML reporters, shim)
- [x] Unsafe fixture → exit 1 + MCP_FS_OUTSIDE_REPO finding
- [x] Safe fixture → exit 0 + no HIGH findings
- [x] Missing file → exit 2 (no crash)
- [x] scan --json produces valid JSON
- [x] scan --json unsafe → summary.high >= 1
- [x] scan --json safe → summary.high == 0
- [x] report --json works
- [x] report --html outputs standalone HTML with findings and redaction
- [x] report --html --output writes standalone HTML file
- [x] report --html escapes finding markup
- [x] report rejects --json and --html together
- [x] Unsafe fixture → CRITICAL (SECRET_KNOWN_PREFIX) + HIGH (MCP_FS_OUTSIDE_REPO)
- [x] Args/nested MCP server credentials → SECRET_KNOWN_PREFIX with redacted JSON-path evidence
- [x] Unsafe fixture → MCP_SHELL_UNRESTRICTED finding
- [x] Unsafe fixture → MCP_UNPINNED_PACKAGE finding
- [x] F7 reproduction → no audit-log findings, no `${...}` package evidence, and only actionable package output
- [x] Unsafe fixture → MCP_TOOL_PROMPT_INJECTION_RISK finding
- [x] Unsafe fixture → MCP_POSTINSTALL_SCRIPT finding
- [x] Terminal output does not contain full secret value
- [x] JSON output does not contain full secret value
- [x] Safe fixture → no SECRET_KNOWN_PREFIX
- [x] Safe fixture → no MCP_SHELL_UNRESTRICTED
- [x] Safe fixture → no MCP_UNPINNED_PACKAGE
- [x] Safe fixture → no MCP_TOOL_PROMPT_INJECTION_RISK
- [x] `scan --json` prompt-injection finding does NOT expose raw risky tool description text
- [x] Safe fixture → no MCP_POSTINSTALL_SCRIPT
- [x] `scan --json` postinstall finding does NOT expose raw script text
- [x] Local package.json postinstall script → MCP_POSTINSTALL_SCRIPT
- [x] Unsafe Claude settings → exit 1 with `CLAUDE_DANGEROUS_PERMISSION`, `CLAUDE_HOOK_SHELL_INJECTION`, and `CLAUDE_NO_DENY_LIST`
- [x] Safe Claude settings → exit 0 with no Claude findings
- [x] `scan claude --json` outputs valid JSON with expected finding IDs
- [x] `scan claude` output does NOT contain raw fixture secret values
- [x] Oversized `CLAUDE.md` → `CLAUDE_HUGE_CONTEXT`
- [x] `scan claude --file <directory>` discovers `.claude/settings.json`
- [x] `scan claude --file <missing>` exits 2 without crashing
- [x] Unsafe Cursor project → exit 1 with `CURSOR_AGENT_AUTO_RUN` and `CURSOR_RULES_PROMPT_INJECTION`
- [x] Safe Cursor project → exit 0 with no Cursor findings
- [x] `scan cursor --json` outputs valid JSON with expected finding IDs
- [x] `scan cursor` output does NOT contain raw fixture secret values
- [x] Global Cursor MCP config → `CURSOR_MCP_ENABLED_GLOBALLY`
- [x] `scan cursor --file <directory>` discovers `.cursor/settings.json` and Cursor rules
- [x] `scan cursor --file <missing>` exits 2 without crashing
- [x] Unsafe repo → exit 1 with `SECRET_ENV_FILE_EXPOSED`, `SECRET_KNOWN_PREFIX`, and `SECRET_HIGH_ENTROPY_VALUE`
- [x] Safe repo → exit 0 with no repo secret findings
- [x] `scan repo --json` outputs valid JSON with expected finding IDs
- [x] `scan repo` output does NOT contain raw fixture secret values
- [x] Git-tracked secret-bearing file → `SECRET_IN_GIT_HISTORY`
- [x] `scan repo --file <missing>` exits 2 without crashing

**Fixture used:**
- Unsafe: `mcp-inspector/examples/unsafe-mcp-configs/basic-unrestricted-filesystem.json`
- Safe: `mcp-inspector/examples/safe-mcp-configs/repo-only-filesystem.json`
- Unsafe Claude: `mcp-inspector/examples/unsafe-claude-configs/settings-with-dangerous-permissions.json`
- Safe Claude: `mcp-inspector/examples/safe-claude-configs/settings-scoped-permissions.json`
- Unsafe Cursor: `mcp-inspector/examples/unsafe-cursor-configs/project`
- Safe Cursor: `mcp-inspector/examples/safe-cursor-configs/project`
- Unsafe Repo: `mcp-inspector/examples/unsafe-repos/basic`
- Safe Repo: `mcp-inspector/examples/safe-repos/basic`

**Commands:**
```bash
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan mcp --file <path>
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan mcp --file <path> --json
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan claude --file <path>
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan claude --file <path> --json
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan cursor --file <path>
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan cursor --file <path> --json
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan repo --file <path>
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector scan repo --file <path> --json
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector report --html --file <path>
PYTHONPATH=mcp-inspector/src python3 -m mcp_inspector report --html --file <path> --output report.html
bash mcp-inspector/bin/mcp-inspector scan mcp --file <path>
```

---

## Phase 2 — spectrona-gateway

**Script:** `spectrona-gateway/validation/phase2_gateway_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS — master gate passed.

**Checks:**
- [x] Scaffold files exist (app, config, audit, dlp, routes, providers)
- [x] FastAPI/uvicorn/httpx/spectrona_cli/local_llms/secrets/policy_engine/mcp_inspector/runtime_guard importable
- [x] Gateway starts in mock mode
- [x] GET /health → {status: ok}
- [x] All non-`/health` routes require local bearer authentication from gateway config/env
- [x] Unauthenticated `POST /policy/presets/relaxed/apply` returns 401
- [x] Gateway rejects disallowed Host headers
- [x] Gateway rejects disallowed Origin headers
- [x] Gateway config refuses all-interface host values
- [x] POST /openai/v1/chat/completions → valid OpenAI-compat response
- [x] POST /anthropic/v1/messages → valid Anthropic-compat response
- [x] POST /local/v1/chat/completions → valid OpenAI-compatible local response
- [x] GET /ui → dashboard shell wired to runtime, DLP, blocks, MCP, protected-app, provider-routing, local-runtime selection/fallback, memory management/extraction/compaction/replay, and policy APIs/actions
- [x] GET /policy → current policy metadata and presets without raw policy text
- [x] GET /policy/presets → relaxed, balanced, and strict preset metadata
- [x] POST /policy/presets/{preset}/apply requires explicit `confirm=true`
- [x] POST /policy/presets/{preset}/apply writes policy preset with backup and can restore balanced
- [x] GET /policy/backups → restorable policy backup metadata
- [x] POST /policy/backups/{backup}/restore requires explicit `confirm=true`
- [x] POST /policy/backups/{backup}/restore restores a policy backup and preserves current policy backup
- [x] GET /mcp/scan → redacted MCP scanner findings with severity and server metadata
- [x] GET /mcp/scan does NOT contain raw secret values
- [x] GET /mcp/apps → protected app status API reports detected MCP app states
- [x] GET /mcp/apps does NOT contain raw secret values
- [x] POST /mcp/apps/{app}/protect requires explicit `confirm=true`
- [x] POST /mcp/apps/{app}/protect wraps config with gateway policy/audit settings
- [x] POST /mcp/apps/{app}/protect does NOT contain raw secret values
- [x] GET /mcp/apps reflects protected state after app protect action
- [x] GET /mcp/apps detects drift after protected app config changes
- [x] POST /mcp/apps/{app}/protect repairs drifted app config
- [x] POST /mcp/apps/{app}/unprotect restores backup
- [x] POST /mcp/apps/{app}/unprotect does NOT contain raw secret values
- [x] GET /events/recent → recent model-call events with policy metadata
- [x] GET /events/blocks → aggregate denied and approval-required runtime events
- [x] GET /events/dlp → aggregate DLP findings without payload content
- [x] GET /events/dlp does NOT contain raw secret values
- [x] GET /events/token-usage → aggregate usage by day, route, provider, model, and client
- [x] GET /events/token-usage does NOT contain raw secret values
- [x] Audit log written on every request
- [x] DLP hit recorded (dlp_findings_count >= 1) for secret-containing request
- [x] Audit log does NOT contain raw secret value
- [x] Runtime event records do NOT contain raw secret value
- [x] Mock provider usage fields are captured
- [x] Fake upstream provider usage fields are captured
- [x] Token usage is estimated when provider usage is absent
- [x] Gateway policy enforcement allows normal requests
- [x] Gateway policy enforcement denies configured clients
- [x] Gateway policy enforcement returns approval-required for configured risk
- [x] Gateway policy enforcement redacts secret-bearing requests
- [x] Gateway response policy hook redacts secret-bearing model output
- [x] Gateway loads `policy_dry_run` from config/env
- [x] Gateway policy dry-run records would-actions without blocking or redacting
- [x] Gateway dry-run HTTP validation records would-block, would-approval, and would-redact while requests still succeed
- [x] OpenAI passthrough forwards to configured upstream
- [x] Anthropic passthrough forwards to configured upstream
- [x] OpenAI-compatible local passthrough forwards to configured upstream
- [x] Passthrough redacts raw secrets before forwarding to upstream
- [x] Passthrough redacts raw secrets from upstream model responses before returning to clients
- [x] Response-side DLP records runtime events and audit logs without raw secret values
- [x] Provider auth headers are set from Spectrona env vars
- [x] Gateway loads `~/.spectrona/config.yaml`-style config
- [x] Gateway loads provider API keys from stored secrets
- [x] Gateway provider env vars override stored secrets
- [x] Gateway loads `local_fallbacks` from config/env
- [x] GET /providers/health reports provider and local LLM runtime config status without live check
- [x] GET /providers/health reports Ollama, LM Studio, llama.cpp, and vLLM local runtime candidates
- [x] GET /providers/health reports configured local fallback count and fallback runtime metadata
- [x] POST /providers/local-runtimes/{id}/select requires explicit `confirm=true`
- [x] POST /providers/local-runtimes/{id}/select updates Spectrona config with backup
- [x] GET /providers/health reflects selected local runtime without gateway restart
- [x] GET /providers/integrations reports Claude/Codex/VS Code routing setup state
- [x] GET /providers/integrations does NOT contain local routing token
- [x] GET /integrations reports aggregate provider routing, MCP app, and local runtime integration state
- [x] GET /integrations does NOT contain raw secrets or local routing token
- [x] POST /integrations/repair requires explicit `confirm=true`
- [x] POST /providers/integrations/{id}/protect requires explicit `confirm=true`
- [x] POST /providers/integrations/{id}/protect creates Claude routing env
- [x] POST /providers/integrations/{id}/protect patches Codex routing config with backup
- [x] POST /providers/integrations/{id}/protect patches VS Code workspace settings with backup
- [x] POST /providers/integrations/{id}/protect does NOT contain local routing token
- [x] GET /providers/integrations reflects protected provider routing
- [x] GET /providers/integrations detects provider routing drift
- [x] POST /providers/integrations/{id}/protect repairs provider routing drift
- [x] POST /providers/integrations/{id}/unprotect removes Codex routing block
- [x] POST /providers/integrations/{id}/unprotect removes VS Code routing settings
- [x] Provider integration mutation APIs do NOT contain local routing token
- [x] POST /integrations/repair repairs aggregate actionable provider/MCP integrations
- [x] POST /integrations/repair does NOT contain raw secrets or local routing token
- [x] GET /providers/health?live=true checks configured fake upstreams including local provider
- [x] Local LLM discovery validates fake Ollama, LM Studio, llama.cpp, and vLLM upstreams
- [x] Local LLM fallback routing retries selected runtime failures through a configured local fallback
- [x] Local fallback passthrough records `fallback_passthrough` runtime events and token usage

---

## Dashboard Browser Render

**Script:** `spectrona-gateway/validation/dashboard_browser_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] Starts a gateway on an isolated localhost port with isolated config, logs, and DB
- [x] Loads the dashboard via authenticated `/ui?token=...` bootstrap and authenticated browser API calls
- [x] Creates runtime traffic and memory fixtures for dashboard rendering
- [x] Chrome headless captures a dashboard screenshot
- [x] Screenshot is a nonblank PNG with expected dimensions
- [x] Chrome headless captures post-JS dashboard DOM
- [x] Rendered DOM contains expected dashboard panels, live seeded data, and redacted secret placeholders without raw secret leakage

**Behavior:**
- Skips cleanly when `SPECTRONA_BROWSER_BIN` or the default Chrome binary is unavailable.
- Uses `SPECTRONA_BROWSER_VALIDATE_KEEP_TMP=true` to preserve debug artifacts when needed.

---

## Policy Engine

**Script:** `policy-engine/validation/policy_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS — F6 reproduced before fix and absent after; master gate passed.

**Checks:**
- [x] Policy engine package scaffold exists
- [x] Policy fixtures exist
- [x] Policy engine modules compile
- [x] Default policy allows normal requests
- [x] `dlp_findings_min` can trigger `redact`
- [x] `shell_risk` can trigger `deny`
- [x] `filesystem_risk` can trigger `deny`
- [x] `client` matching can trigger `deny`
- [x] `route`, `provider_type`, and `model` matching work
- [x] `shell_risk` can trigger `require_approval`
- [x] Relaxed, balanced, and strict policy presets load through the shared engine
- [x] Empty/missing rule `match` fails at load time
- [x] Unknown match keys fail at load time
- [x] Invalid match value types fail at load time
- [x] Invalid policy text is rejected before request evaluation

---

## Phase 2C — spectrona-cli

**Script:** `spectrona-cli/validation/phase2_cli_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] CLI command scaffold exists
- [x] Local LLM discovery module scaffold exists
- [x] `spectrona init` writes config and logs directory
- [x] `spectrona init` writes local provider defaults plus `policy_dry_run` and memory protection defaults
- [x] `spectrona init` writes default `policy.yaml`
- [x] `spectrona init` is idempotent without `--force`
- [x] Local LLM selection helper updates config with backup
- [x] Local LLM discovery marks configured fallback runtimes and ignores hosted fallback URLs
- [x] `spectrona status` exits cleanly
- [x] `spectrona status` reports config, policy, OpenAI/Anthropic/local providers, logs, memory DB, mode, and policy dry-run state
- [x] `spectrona status` does not print provider secrets
- [x] `spectrona policy status --json` reports active balanced policy
- [x] `spectrona policy presets --json` lists relaxed, balanced, and strict
- [x] `spectrona policy apply` requires `--confirm`
- [x] `spectrona policy apply relaxed --confirm --json` writes preset with backup
- [x] `spectrona policy backups --json` reports restorable backups
- [x] `spectrona policy restore` requires `--confirm`
- [x] `spectrona policy restore <backup> --confirm --json` restores backup and preserves current policy backup
- [x] `spectrona policy status` table output works
- [x] `spectrona secrets status --json` reports OpenAI/Anthropic/local key state without values
- [x] `spectrona secrets set` stores a provider key without printing the raw secret
- [x] `spectrona secrets status <provider>` reflects stored keys without printing the raw secret
- [x] `spectrona secrets get <provider>` returns a key only when explicitly requested
- [x] `spectrona secrets delete <provider>` removes a stored key
- [x] `spectrona status` reports stored provider keys without printing stored secret values
- [x] `spectrona secrets migrate-config --json` reports migrated provider keys without values
- [x] `spectrona secrets migrate-config` does NOT print raw migrated secret values
- [x] `spectrona secrets migrate-config` writes a config backup and scrubs plaintext provider keys
- [x] `spectrona secrets migrate-config` stores migrated OpenAI/Anthropic/local keys
- [x] `spectrona status` reports migrated stored keys without printing raw values
- [x] `spectrona secrets migrate-config` is idempotent after config scrub
- [x] `spectrona scan mcp <safe fixture>` exits 0 and reports clean
- [x] `spectrona scan mcp <unsafe fixture>` exits 1 and reports findings
- [x] `spectrona scan mcp --json` outputs valid JSON
- [x] `spectrona scan mcp --json` reports MCP tool prompt-injection risk without raw tool text
- [x] `spectrona scan mcp --json` reports suspicious postinstall risk without raw script text
- [x] `spectrona scan claude <safe fixture>` exits 0 and reports clean
- [x] `spectrona scan claude <unsafe fixture>` exits 1 and reports findings
- [x] `spectrona scan claude --json` outputs valid JSON without raw fixture secrets
- [x] `spectrona scan cursor <safe fixture>` exits 0 and reports clean
- [x] `spectrona scan cursor <unsafe fixture>` exits 1 and reports findings
- [x] `spectrona scan cursor --json` outputs valid JSON without raw fixture secrets
- [x] `spectrona scan repo <safe fixture>` exits 0 and reports clean
- [x] `spectrona scan repo <unsafe fixture>` exits 1 and reports findings
- [x] `spectrona scan repo --json` outputs valid JSON with repo secret finding IDs
- [x] `spectrona scan repo --json` does NOT expose raw fixture secrets
- [x] `spectrona scan repo --html --output` writes a redacted HTML report
- [x] Gateway health handles running or unavailable gateway cleanly
- [x] Gateway stop is clean when no process is running
- [x] `spectrona stop` alias is clean when no process is running
- [x] Top-level `spectrona start`, `restart`, and `stop` lifecycle works
- [x] `spectrona service print` emits LaunchAgent plist
- [x] `spectrona service install` writes LaunchAgent plist
- [x] `spectrona service load --dry-run` prints launchctl load command
- [x] `spectrona service unload --dry-run` prints launchctl unload command
- [x] `spectrona service uninstall` removes LaunchAgent plist
- [x] `spectrona mcp proxy --help` works and imports runtime-guard
- [x] `spectrona mcp wrap --output` writes a wrapped config
- [x] `spectrona mcp wrap` terminal output does NOT expose raw secrets
- [x] `spectrona mcp wrap --apply` creates a backup and rewrites the config
- [x] `spectrona mcp undo` restores the backup
- [x] `spectrona mcp apps --json` reports missing, unprotected, protected, partial, drift, and recommended action state
- [x] `spectrona mcp apps --json` does NOT expose raw secrets
- [x] `spectrona mcp apps` table output works
- [x] `spectrona mcp protect <app-id> --json` wraps a detected app MCP config and creates backup
- [x] `spectrona mcp protect <app-id> --json` does NOT expose raw secrets
- [x] `spectrona mcp apps --json` reflects protected state after app protect
- [x] `spectrona mcp unprotect <app-id>` restores backup
- [x] `spectrona mcp unprotect <app-id>` fails cleanly when backup is missing
- [x] `spectrona integrations status --json` aggregates Claude/Codex/VS Code provider routing, MCP app, and local runtime state
- [x] `spectrona integrations status --json` does NOT expose raw secrets
- [x] `spectrona integrations status` table output works and includes local LLM runtimes
- [x] `spectrona integrations repair` requires `--confirm`
- [x] `spectrona integrations repair --confirm --json` repairs actionable Claude/Codex/VS Code provider and MCP integrations
- [x] `spectrona integrations repair --confirm --json` does NOT expose raw secrets
- [x] `spectrona integrations repair` mutates only confirmed temp fixtures with backups and MCP policy/audit args
- [x] `spectrona integrations status --json` reflects repaired state
- [x] `spectrona integrations repair --confirm --json` is idempotent after repairs
- [x] protect commands remain print-only
- [x] `protect vscode --print` emits VS Code workspace terminal provider routing settings
- [x] `protect status --json` reports Claude/Codex/VS Code provider routing setup state
- [x] `protect status --json` does NOT expose local routing token
- [x] `protect claude --apply/--undo` writes/removes routing env block
- [x] `protect codex --apply/--undo` patches/removes config block and creates backup
- [x] `protect vscode --apply/--undo` patches/removes workspace settings and creates backup
- [x] `protect status --json` reflects protected provider routing
- [x] `protect status --json` detects provider routing drift
- [x] `protect codex --apply` repairs provider routing drift
- [x] `protect vscode --apply` repairs provider routing drift
- [x] logs tail does not crash when log is missing

---

## Phase 3A — memory HTTP routes

**Script:** `spectrona-gateway/validation/phase3_memory_routes_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] Gateway starts with isolated SQLite DB
- [x] Memory staleness helper exists
- [x] Memory context package helper exists
- [x] Memory timeline helper exists
- [x] Memory compaction helper exists
- [x] Memory session extraction helper exists
- [x] Memory session replay helper exists
- [x] Memory storage protection helper exists
- [x] POST /memory/items stores normal item
- [x] POST /memory/items defaults to redacted raw memory storage
- [x] GET /memory/items returns stored item
- [x] GET /memory/items returns source tool, tags, pinned, redacted state, and storage mode metadata
- [x] GET /memory/events returns created item event metadata
- [x] GET /memory/items searches redacted content and filters by tag/source/pinned state
- [x] GET /memory/items exposes stale context detection metadata
- [x] GET /memory/items search does not match hidden raw secret content
- [x] Secret-containing memory item records DLP hit
- [x] Secret-containing memory defaults to redacted storage metadata
- [x] SQLite memory content does NOT store raw secret by default
- [x] Encrypted raw memory opt-in stores encrypted metadata
- [x] SQLite encrypted memory keeps raw secrets out of plaintext columns
- [x] Encrypted memory content decrypts with the local memory key
- [x] Plaintext raw memory requests are downgraded by policy gate
- [x] SQLite plaintext-gated memory stores only redacted content
- [x] GET response returns redacted content only
- [x] GET /memory/timeline returns redacted memory audit timeline metadata
- [x] GET /memory/timeline does NOT expose raw secret values
- [x] GET /memory/context returns a redacted fresh context package
- [x] GET /memory/context excludes stale memory by default
- [x] GET /memory/extract previews redacted runtime session metadata
- [x] POST /memory/extract requires explicit `confirm=true`
- [x] POST /memory/extract applies confirmed session extraction safely
- [x] GET /memory/items shows extracted redacted session summary
- [x] GET /memory/replay previews redacted metadata-only replay from runtime events and memory summaries
- [x] POST /memory/replay requires explicit `confirm=true`
- [x] POST /memory/replay applies confirmed metadata-only replay safely
- [x] GET /memory/items shows replay session summary without raw secrets
- [x] GET /memory/compact previews a redacted duplicate/stale compaction plan
- [x] POST /memory/compact requires explicit `confirm=true`
- [x] POST /memory/compact applies confirmed compaction plan safely
- [x] GET /memory/items shows compaction tags and generated summary
- [x] PATCH /memory/items/{id} can pin an item
- [x] PATCH /memory/items/{id} updates type, content, tags, and importance
- [x] PATCH /memory/items/{id} redacts updated secret content
- [x] SQLite memory update keeps raw secret out of storage
- [x] DELETE /memory/items/{id} requires explicit `confirm=true`
- [x] DELETE /memory/items/{id}?confirm=true removes the item
- [x] GET /memory/items excludes deleted items
- [x] GET /memory/timeline can filter an item lifecycle through delete
- [x] Audit log records memory_insert action
- [x] Audit log records memory_update and memory_delete actions
- [x] Audit log records memory_compact action
- [x] Audit log records memory_extract_session action
- [x] Audit log records memory_replay_session action
- [x] Audit log does NOT contain raw secret value
- [x] Runtime memory captures marked request memory after request policy redaction
- [x] Runtime memory captures marked response memory after response guard approval
- [x] Runtime memory injects relevant redacted memory into the next forwarded request when enabled
- [x] Runtime memory skips stale unpinned memory during injection
- [x] Runtime memory records attachment events without raw secrets

---

## Packaging — Homebrew layout

**Script:** `packaging/validate_packaging.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] Homebrew formula exists
- [x] Formula Ruby syntax is valid
- [x] Formula exposes `spectrona` executable
- [x] Formula wrapper pins Homebrew `python@3.11`
- [x] Formula includes `policy-engine`
- [x] Formula includes `runtime-guard`
- [x] Formula includes brew service command
- [x] Formula includes post-install log directory setup
- [x] Formula caveats include init, service, dashboard, and integration guidance
- [x] Gateway package data includes UI assets
- [x] Release builder exists and compiles
- [x] Release builder creates a source archive, manifest, SHA, and expected contents
- [x] Release builder produces stable SHA across output directories
- [x] Packaged `spectrona status` works from side-by-side libexec layout
- [x] Packaged `spectrona secrets status --json` can import the secret helper
- [x] Packaged `spectrona secrets migrate-config --json` can import the secret helper
- [x] Packaged `spectrona init` works from side-by-side libexec layout
- [x] Packaged `spectrona init` writes `policy.yaml`
- [x] Packaged `spectrona policy status --json` can import `policy-engine`
- [x] Packaged `spectrona policy apply/backups` can mutate policy with backup
- [x] Packaged layout includes dashboard UI asset
- [x] Packaged `spectrona` shim exposes all side-by-side component paths
- [x] Packaged `spectrona protect status --json` can import routing helper
- [x] Packaged `spectrona integrations status --json` can import manager/runtime-guard/local LLM discovery and fallback metadata
- [x] Packaged `spectrona integrations repair --confirm --json` can mutate temp fixtures
- [x] Packaged `spectrona mcp proxy --help` can import `runtime-guard`
- [x] Packaged `spectrona mcp wrap --output` can import `runtime-guard`
- [x] Packaged `spectrona mcp apps --json` can import `runtime-guard`
- [x] Packaged `spectrona mcp protect` can import `runtime-guard`
- [x] Packaged `spectrona mcp unprotect` can import `runtime-guard`
- [x] Packaged `spectrona scan mcp` works with side-by-side components
- [x] Packaged `spectrona scan mcp --json` reports MCP prompt-injection and suspicious postinstall risks without raw unsafe text
- [x] Packaged `spectrona scan claude` works with side-by-side components
- [x] Packaged `spectrona scan cursor` works with side-by-side components
- [x] Packaged `spectrona scan repo` works with side-by-side components and redacts raw fixture secrets
- [x] Packaged `spectrona scan repo --html --output` writes a redacted HTML report

---

## Runtime Guard — MCP proxy

**Script:** `runtime-guard/validation/phase2_validate.sh`

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Checks:**
- [x] Runtime guard package scaffold exists
- [x] MCP proxy and redaction modules compile
- [x] MCP config wrapping module compiles
- [x] `runtime_guard.mcp_proxy` and `policy_engine` import together
- [x] Safe MCP `tools/call` requests pass through to an upstream handler
- [x] Filesystem paths inside repo are allowed
- [x] MCP proxy defaults to dry-run and forwards shell-risk false positives while auditing would-block metadata
- [x] Explicit MCP proxy enforcement denies shell-risk calls
- [x] Explicit MCP proxy enforcement denies filesystem paths outside repo
- [x] Explicit MCP proxy enforcement can return approval-required for shell risk
- [x] Explicit MCP proxy enforcement redacts secret-bearing MCP inputs before forwarding
- [x] Explicit MCP proxy enforcement redacts secret-bearing MCP outputs before returning to the client
- [x] MCP dry-run records would-block, would-approval, and would-redact actions while allowing traffic
- [x] MCP audit log is metadata-only and does not contain raw secrets
- [x] MCP config wrapper rewrites servers behind `spectrona mcp proxy`
- [x] MCP config wrapper avoids double wrapping
- [x] MCP config wrapper can apply with backup and restore with undo
- [x] MCP app discovery reports missing, invalid, unprotected, protected, and partial states
- [x] MCP app discovery reports drift and repair recommendation metadata
- [x] MCP app discovery output does NOT contain raw secrets
- [x] MCP app protect/unprotect wraps detected configs, repairs partial configs, restores missing configs from backup, and reports metadata only
- [x] `python -m runtime_guard.mcp_proxy --help` works
- [x] `spectrona mcp proxy --help` documents `--dry-run` and `--enforce`

---

## Phase 3 — ClaudeDB

**Script:** `claudedb/validation/phase3_validate.sh`

**Last run:** N/A
**Result:** NOT STARTED

---

## Fixture → Rule mapping

| Fixture | Expected Rule IDs | Severity |
|---|---|---|
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | MCP_FS_OUTSIDE_REPO | HIGH |
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | MCP_SHELL_UNRESTRICTED | CRITICAL |
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | SECRET_KNOWN_PREFIX | CRITICAL |
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | MCP_UNPINNED_PACKAGE | MEDIUM |
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | MCP_TOOL_PROMPT_INJECTION_RISK | MEDIUM |
| unsafe-mcp-configs/basic-unrestricted-filesystem.json | MCP_POSTINSTALL_SCRIPT | HIGH |
| safe-mcp-configs/scoped-filesystem.json | (none expected above LOW) | — |
| unsafe-claude-configs/settings-with-dangerous-permissions.json | CLAUDE_DANGEROUS_PERMISSION | HIGH |
| unsafe-claude-configs/settings-with-dangerous-permissions.json | CLAUDE_HOOK_SHELL_INJECTION | HIGH |
| unsafe-claude-configs/settings-with-dangerous-permissions.json | CLAUDE_NO_DENY_LIST | LOW |
| generated oversized CLAUDE.md fixture | CLAUDE_HUGE_CONTEXT | MEDIUM |
| safe-claude-configs/settings-scoped-permissions.json | (none expected) | — |
| unsafe-cursor-configs/project | CURSOR_AGENT_AUTO_RUN | HIGH |
| unsafe-cursor-configs/project | CURSOR_RULES_PROMPT_INJECTION | MEDIUM |
| generated global .cursor/mcp.json fixture | CURSOR_MCP_ENABLED_GLOBALLY | MEDIUM |
| safe-cursor-configs/project | (none expected) | — |
| unsafe-repos/basic | SECRET_ENV_FILE_EXPOSED | HIGH |
| unsafe-repos/basic | SECRET_KNOWN_PREFIX | CRITICAL |
| unsafe-repos/basic | SECRET_HIGH_ENTROPY_VALUE | HIGH |
| generated git-tracked repo fixture | SECRET_IN_GIT_HISTORY | HIGH |
| safe-repos/basic | (none expected) | — |

## Full suite

**Last run:** 2026-09-22 (Session 084 — R8 corpus recall shard)
**Result:** PASS

**Command:**
```bash
bash validation/validate_all.sh
```

Note: server-backed gateway validations need permission to bind localhost in sandboxed environments.
