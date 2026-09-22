# Phases

## PHASE 1 — mcp-inspector (ACTIVE)

**Goal:** Useful local scanner — runs in under 60 seconds, produces actionable report.

**Commands to implement:**
- `mcp-inspector scan` / `scan mcp|claude|cursor|repo`
- `mcp-inspector report --json`
- `mcp-inspector report --html`

**Must detect:**
- [ ] Filesystem MCP access outside repo
- [ ] Unrestricted shell MCP server
- [x] Secrets in env/args/nested config (known prefixes + high entropy)
- [ ] Risky tool descriptions (prompt injection surface)
- [ ] Unsafe Cursor/Claude settings
- [ ] Suspicious postinstall scripts
- [ ] Unpinned packages
- [ ] Oversized CLAUDE.md (context pollution)

**Success criteria:**
- [x] Fixture-based tests and regression reproductions exist
- [x] Seed corpus precision benchmark exists and is wired into master validation
- [x] GitHub harvester supports query fan-out and candidate deduplication
- [x] Offline labeling queue workflow exists for redacted harvested candidates
- [x] Labeled corpus promotion guard rejects unlabeled records and strips prediction metadata
- [x] Token-backed GitHub harvest produced a redacted public candidate labeling queue
- [x] Public GitHub reviewed shard is promoted into the measured corpus
- [x] Corpus-backed scanner shell precision fix removed package-name substring noise
- [x] Reviewed corpus expanded to 199 labeled cases with 95% precision gate passing
- [ ] Full public MCP config corpus reaches roughly 1,000 labeled redacted configs
- [ ] Unsafe example produces CRITICAL/HIGH findings
- [ ] Safe example produces LOW/NONE findings
- [ ] JSON output works
- [ ] Terminal report works
- [ ] `bash mcp-inspector/validation/phase1_validate.sh` passes

**Validation script:** `mcp-inspector/validation/phase1_validate.sh`

---

## PHASE 2 — runtime-guard (ACTIVE)

**Goal:** Enforce policy before damage occurs.

- [x] Local policy YAML integration for MCP tool calls
- [x] Strict policy load-time schema validation with fail-closed runtime behavior
- [x] MCP stdio proxy MVP
- [x] MCP config wrap/undo CLI
- [x] MCP app discovery/status CLI
- [x] MCP app protect/unprotect CLI
- [x] MCP app protect/unprotect gateway/UI actions
- [x] MCP app drift detection and repair recommendations
- [x] Provider routing status/repair CLI and gateway/UI actions
- [x] Aggregate integration manager CLI/API for provider routing and MCP app repair
- [x] Keychain-backed provider secret storage and gateway credential loading
- [x] Config provider-key migration into secret store with backup/scrub
- [x] Gateway local bearer authentication, Host/Origin validation, and localhost-only CLI binding
- [x] CLI policy preset and rollback controls
- [x] Gateway response-side model output DLP/policy hook
- [x] MCP tool output DLP redaction
- [x] Policy dry-run mode for gateway and MCP enforcement
- [x] MCP proxy advisory-by-default mode with explicit enforcement opt-in
- [x] Shared scanner/gateway/runtime secret detection and schema/key-based MCP shell/filesystem risk matching
- [x] Policy status/preset APIs and dashboard preset controls
- [x] Policy backup listing and restore controls
- [x] Metadata-only MCP audit log
- [ ] Shell wrapper and git wrapper
- [ ] Claude hooks integration
- [ ] Approval prompt UX

**Validation script:** `runtime-guard/validation/phase2_validate.sh`

---

## PHASE 3 — ClaudeDB (FUTURE)

**Goal:** Structured context freshness + replay.

- Local SQLite / JSONL audit store
- Memory extraction from sessions
- Stale context detection
- Audit timeline + replay
- "Fresh context package" for next Claude session

**Validation script:** `claudedb/validation/phase3_validate.sh`
