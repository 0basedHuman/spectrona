# Roadmap

## Product Goal

Spectrona should become a local-first install that routes AI traffic and MCP tool usage through a controllable local security layer.

Target flow:

```bash
brew install spectrona
spectrona init
spectrona start
```

Target routing:

```text
Claude            -> Spectrona Gateway -> Anthropic
Codex/OpenAI apps -> Spectrona Gateway -> OpenAI
Local apps        -> Spectrona Gateway -> Ollama / LM Studio / llama.cpp / vLLM
MCP tools         -> Spectrona MCP Proxy -> approved MCP servers
```

Core guarantees:

- Local-first operation
- DLP redaction before logging
- Audit logs for model calls and MCP actions
- MCP risk scanning and runtime control
- Policy enforcement before dangerous actions
- Memory capture and context continuity
- Redacted memory storage by default, with encrypted raw storage only by explicit opt-in

Detailed implementation tasks are tracked in `docs/TODO.md`.

## Phase 1 — mcp-inspector

Target: useful local scanner, OSS-friendly, immediate value.

Current status: active and built for the tracked scanner rules, with MCP, Claude, Cursor, repo secret, MCP tool-description prompt-injection, and suspicious postinstall scanning implemented.

- [x] Scaffold + rule files + fixtures
- [x] Scanner CLI: `mcp-inspector scan mcp`
- [x] JSON report output
- [x] HTML report: `mcp-inspector report --html`
- [x] Terminal report with severity labels
- [x] Detect filesystem MCP access outside repo
- [x] Detect known secret prefixes in MCP env/config
- [x] Detect unrestricted shell MCP servers
- [x] Detect unpinned package-based MCP installs
- [x] Detect risky MCP tool description / prompt-injection text
- [x] Detect suspicious postinstall scripts
- [x] Claude config scanner: `scan claude`
- [x] Detect Claude dangerous auto-approved permissions
- [x] Detect missing Claude deny list
- [x] Detect Claude hook shell-injection risk
- [x] Detect oversized `CLAUDE.md`
- [x] Cursor config scanner: `scan cursor`
- [x] Detect Cursor terminal auto-run / disabled confirmation
- [x] Detect prompt-injection-prone Cursor rules
- [x] Detect globally scoped Cursor MCP servers
- [x] Repo scanner: `scan repo`
- [x] Detect exposed repo env files not ignored by `.gitignore`
- [x] Detect high-entropy repo secret values
- [x] Detect git-tracked secret-bearing files
- [x] Fixture-based validation
- [x] Phase 1 validation passing
- [ ] README polish for OSS release
- [ ] Public GitHub repo prep

## Phase 2 — Installable Local Gateway

Target: always-on local gateway that can sit between AI clients and upstream providers.

Current status: mock gateway exists, real OpenAI/Anthropic passthrough works through configurable upstream URLs, env vars, config-file keys, and stored provider secrets. A generic OpenAI-compatible local provider route is available.

- [x] FastAPI gateway scaffold
- [x] `GET /health`
- [x] OpenAI-compatible mock route
- [x] Anthropic-compatible mock route
- [x] DLP hit counting
- [x] Response-side model output DLP/policy hook
- [x] Audit log writes without raw secret leakage
- [x] Basic memory routes
- [x] Runtime memory capture/retrieval/injection hooks for OpenAI, Anthropic, and local-compatible routes
- [x] Real OpenAI provider passthrough
- [x] Real Anthropic provider passthrough
- [x] Upstream credential loading from env vars
- [x] Upstream credential loading from config file
- [x] Upstream credential loading from Keychain-backed secret store
- [x] `spectrona secrets set/get/status/delete`
- [x] `spectrona secrets migrate-config` backs up config files and scrubs plaintext provider keys
- [x] Config file under `~/.spectrona/config.yaml`
- [x] `spectrona init`
- [x] `spectrona start`
- [x] `spectrona stop`
- [x] `spectrona restart`
- [x] `spectrona gateway start`
- [x] `spectrona gateway stop`
- [x] `spectrona gateway restart`
- [x] `spectrona status` checks gateway, config, providers, logs
- [x] `spectrona policy status/presets/apply/backups/restore`
- [x] Background gateway process mode
- [x] LaunchAgent plist generation/install/uninstall
- [x] LaunchAgent load/unload command support
- [ ] Long-running OS service mode fully validated with launchctl
- [ ] `brew services start spectrona`
- [x] Health checks for upstream providers
- [x] Health checks for OpenAI-compatible local provider
- [x] Runtime model-call event store
- [x] Recent runtime event query API
- [x] Token usage accounting API
- [x] Token usage daily, route, model, provider, and app/client dashboard view
- [x] Runtime blocks summary API
- [x] DLP activity summary API
- [x] Policy dry-run mode for gateway request/response decisions
- [x] Runtime summaries include dry-run would-block, would-approval, and would-redact counts
- [x] Policy status API at `/policy`
- [x] Policy presets API for relaxed, balanced, and strict modes
- [x] Consent-based policy preset apply API with backup
- [x] Policy backup list/restore API with confirmed rollback
- [x] Read-only gateway dashboard at `/ui`
- [x] Dashboard packaged with gateway assets
- [x] MCP scan results API at `/mcp/scan`
- [x] Dashboard MCP scan panel with redacted findings
- [x] Dashboard runtime blocks and DLP activity panels
- [x] Dashboard runtime panels show dry-run would-action counts
- [x] Dashboard Policy panel with preset apply actions
- [x] Dashboard Policy panel restore actions for policy backups
- [x] Browser screenshot and post-JS DOM validation for `/ui`
- [x] MCP app integration status API at `/mcp/apps`
- [x] Dashboard Protected Apps panel for MCP config protection state
- [x] Consent-based MCP app protect/unprotect APIs
- [x] Dashboard Protected Apps actions for MCP config protection/restore
- [x] MCP app config drift detection and repair recommendations
- [x] Dashboard Protected Apps drift badges and repair action state
- [x] Provider routing integration status API at `/providers/integrations`
- [x] Consent-based provider routing protect/unprotect APIs
- [x] Dashboard Provider Routing panel for Claude/Codex setup, drift, repair, and remove actions
- [x] Aggregate integration manager CLI/API status and confirmed repair for provider routing plus MCP apps
- [x] Local LLM runtime discovery for Ollama, LM Studio, llama.cpp, and vLLM
- [x] Local LLM runtime status exposed through provider health, aggregate integrations, CLI, and dashboard
- [x] Confirmed local LLM runtime selection through provider API and dashboard with Spectrona config backup
- [x] Local LLM fallback routing metadata, retry behavior, audit/event tracking, and dashboard badges

## Phase 3 — Homebrew / One-Command Install

Target: installable by normal users without cloning the repo.

Target commands:

```bash
brew install spectrona
spectrona init
spectrona start
```

- [x] Single top-level `spectrona` executable
- [x] Package active modules behind one installable distribution layout
- [x] Homebrew formula template
- [x] Deterministic source release archive builder with SHA manifest
- [x] Post-install guidance
- [x] Formula service block for `brew services start spectrona`
- [x] Default config directory: `~/.spectrona/`
- [x] Default log directory: `~/.spectrona/logs/`
- [x] Default DB path: `~/.spectrona/memory.db`
- [ ] Published release artifact URL/SHA in tap formula
- [ ] Validate `brew install spectrona` from tap
- [ ] Validate `brew services start spectrona` from tap install
- [ ] Safe upgrade path for config/schema changes
- [ ] Uninstall cleanup docs
- [x] Local validation for packaged install layout
- [ ] CI validation for packaged install

## Phase 4 — Claude, Codex, And VS Code Routing

Target: make Claude, Codex/OpenAI-compatible clients, and VS Code workspace-launched clients route through Spectrona with safe, reversible setup.

Current status: print-only setup guidance, reversible apply/undo, provider routing status, dashboard setup/repair actions, stored upstream provider keys, manual plaintext-key migration, and VS Code workspace settings routing exist for supported routing targets. Automatic migration/preservation during integration setup is still open.

- [x] `spectrona protect claude --print`
- [x] `spectrona protect codex --print`
- [x] `spectrona protect vscode --print`
- [x] `spectrona protect status`
- [x] Detect Claude routing env target
- [x] Detect Codex config target
- [x] Detect VS Code workspace settings target
- [x] Backup existing config before changes
- [x] `spectrona protect claude --apply`
- [x] `spectrona protect codex --apply`
- [x] `spectrona protect vscode --apply`
- [x] `spectrona protect claude --undo`
- [x] `spectrona protect codex --undo`
- [x] `spectrona protect vscode --undo`
- [x] Generate Claude env routing to local Anthropic-compatible gateway
- [x] Patch Codex/OpenAI config to local OpenAI-compatible gateway
- [x] Patch VS Code workspace terminal env settings to local OpenAI/Anthropic-compatible gateway
- [x] Detect Claude/Codex/VS Code routing drift
- [x] Repair Claude/Codex/VS Code routing drift
- [x] Expose Claude/Codex/VS Code routing status/actions through gateway and dashboard
- [x] Store real upstream API keys securely through `spectrona secrets`
- [x] Migrate plaintext config-file upstream API keys with backup through `spectrona secrets migrate-config`
- [ ] Migrate/preserve existing plaintext upstream API keys during integration setup
- [ ] Optionally make Spectrona the default provider
- [ ] Validate routed calls end-to-end

## Phase 5 — MCP Runtime Control

Target: move from MCP scanning to runtime MCP enforcement.

Current status: MCP proxy MVP exists and can enforce policy on `tools/call` over stdio. Explicit MCP config wrap/undo is built. App-specific MCP status discovery, consent-based protect/unprotect, drift detection, and repair recommendations for Claude, Codex, and VS Code MCP configs are built. MCP tool inputs and outputs are redacted before crossing the proxy boundary.

- [x] MCP proxy server MVP
- [x] Import explicit MCP server config files
- [x] Discover app MCP config locations for Claude Code, Claude Desktop, Codex, and VS Code
- [x] Report missing, invalid, unprotected, protected, and partial MCP protection states
- [x] Wrap configured MCP servers behind Spectrona
- [x] Intercept MCP tool calls
- [x] Block risky filesystem actions by policy
- [x] Block risky shell actions by policy
- [x] Detect and redact secrets in MCP inputs
- [x] Detect and redact secrets in MCP outputs
- [x] Policy dry-run mode for MCP calls and tool outputs
- [x] Approval-required flow for dangerous tools
- [ ] Per-project MCP allowlists
- [ ] Per-tool deny rules
- [x] MCP audit log
- [x] CLI commands to wrap/undo MCP protection
- [x] CLI command to show app MCP protection status
- [x] CLI commands to protect/unprotect detected app MCP configs
- [x] Detect MCP app config drift after protection
- [x] Recommend repair/restore actions for drifted MCP app configs
- [x] Restore missing MCP app configs from Spectrona backup
- [x] Validation fixtures for allowed, blocked, and approval-required MCP calls
- [x] Validation fixtures for MCP config wrap/apply/undo
- [x] Validation fixtures for MCP app discovery/status without raw secret output
- [x] Validation fixtures for MCP app protect/unprotect and partial repair
- [x] Validation fixtures for MCP app drift detection and repair recommendations
- [x] Validation fixtures for MCP dry-run would-actions

## Phase 6 — Local LLM Support

Target: route local model traffic through the same local gateway and policy/audit layer.

- [x] OpenAI-compatible local endpoint adapter
- [x] Ollama preset and health behavior
- [x] LM Studio preset and health behavior
- [x] llama.cpp server preset and health behavior
- [x] vLLM preset and health behavior
- [x] Provider selection in `~/.spectrona/config.yaml`
- [x] Dashboard/API selection for local runtime candidates
- [x] Health checks for local providers
- [x] Fallback routing rules
- [x] Audit local model calls
- [x] DLP on local model prompts/responses
- [x] Validate each local runtime with fake OpenAI-compatible upstreams
- [x] Validate local fallback retry path with fake fallback upstream

## Phase 7 — Runtime Guard Policy Engine

Target: enforce policy before damage occurs across gateway, MCP, shell, and git surfaces.

- [x] Local policy YAML engine
- [x] Allow/deny/require-approval/redact actions
- [x] Policy presets for relaxed, balanced, and strict modes
- [ ] Shell command wrapper
- [ ] Git command wrapper
- [x] MCP policy integration
- [x] Gateway policy integration
- [ ] Claude hooks integration
- [ ] Approval prompt UX
- [x] Policy decision audit log
- [x] Dry-run mode
- [x] Policy API/dashboard controls with confirmed preset changes and backup
- [x] Policy backup rollback API/dashboard controls
- [x] CLI policy preset apply and backup restore controls
- [x] Aggregate integration manager policy-safe repair flow for provider and MCP app configs

## Phase 8 — ClaudeDB / Memory

Target: structured context freshness, replay, and continuity.

Current status: SQLite memory store, HTTP memory routes, memory search/management, memory audit timeline, stale context detection, fresh context packages, runtime session extraction, metadata-only session replay, memory compaction, redacted-by-default storage, encrypted raw-storage opt-in, plaintext raw-storage policy gating, and opt-in runtime memory capture/retrieval/injection exist.

- [x] Local SQLite memory store
- [x] Store redacted memory content by default
- [x] Encrypted raw memory storage opt-in
- [x] Policy gate for plaintext raw memory storage
- [x] HTTP create/list memory routes
- [x] Audit memory inserts
- [x] Memory search/filter API
- [x] Memory pin/update/delete API
- [x] Dashboard memory search, pinned filter, redacted/stale state, context package preview, audit timeline, session extraction, metadata-only replay, compaction preview/apply, pin, and delete actions
- [x] Capture marked memory from model requests and responses
- [x] Retrieve relevant memory before provider forwarding
- [x] Inject redacted relevant memory into OpenAI, Anthropic, and local-compatible requests when enabled
- [x] Record memory attachment events per item
- [x] Stale context detection by age/tag with runtime injection filtering
- [x] Fresh context package generation
- [x] Audit timeline
- [x] Compaction logic
- [x] Full memory extraction from runtime session metadata
- [x] Session replay
- [x] Memory search/filter UX

## Release Milestones

### Alpha

- [ ] `brew install spectrona` works
- [x] `spectrona init && spectrona start` starts local gateway
- [x] OpenAI and Anthropic passthrough works
- [x] Claude/Codex print setup works
- [x] MCP scanner works
- [x] Full local validation passes

### Beta

- [x] Claude/Codex apply/undo setup works
- [x] Local LLM adapters work
- [x] MCP proxy blocks at least shell/filesystem high-risk calls
- [x] Policy YAML enforcement works
- [x] Audit viewer / logs UX is usable

### Public Launch

- [ ] GitHub repo public
- [ ] README and install docs polished
- [ ] CI validation
- [ ] Versioned releases
- [ ] Homebrew tap published
- [ ] Security model documented

## Non-goals

- Cloud-first architecture
- Enterprise dashboard before local product traction
- Generic AI control plane
- Hosted vector DB / RAG platform
- Portkey / Runlayer / Koi clone
