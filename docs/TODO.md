# Implementation TODO

This file tracks the concrete work needed to turn Spectrona from a CLI-driven prototype into an always-on local guard layer for Claude, Codex, VS Code, Ollama, and other local or hosted LLM traffic.

For every item completed here, update:

- `docs/ROADMAP.md`
- `docs/VALIDATION.md`
- `docs/SESSION_LOG.md`
- `docs/MEMORY.md`
- The relevant validation script
- `bash validation/validate_all.sh` result

## Operating Rule

No feature is considered done until code, validation, and docs agree.

Required proof for each feature:

- It is reachable through the expected runtime path.
- It has focused validation.
- It passes `bash validation/validate_all.sh`.
- It does not leak raw secrets in logs, terminal output, API responses, or UI state.
- It has a clear rollback or disable path when it changes user config.

## R8 Corpus Follow-Up

- [ ] Investigate the nine measured `MCP_UNPINNED_PACKAGE` false negatives exposed by the 277-case corpus; keep any detector change scoped to an existing rule and prove it against the corpus precision gate.

## P0 - Runtime Guard Foundation

Goal: make Spectrona a real guard layer, not only a scanner/gateway.

- [x] Add local policy YAML format.
- [x] Add policy decision model: `allow`, `deny`, `require_approval`, `redact`.
- [x] Add policy evaluator package shared by gateway and MCP runtime.
- [x] Add CLI policy status/presets/apply/backups/restore commands.
- [x] Add policy audit events with rule id, action, app, provider, and reason.
- [x] Add gateway request policy hook before provider forwarding.
- [x] Add gateway response policy hook before returning model output.
- [x] Add dry-run mode that records what would have been blocked, approved, or redacted.
- [x] Validate allow/deny/approval decisions with fixtures.
- [x] Validate policy decisions never expose raw secrets.
- [x] Validate response-side model output redaction before returning to clients.
- [x] Validate dry-run records would-actions without enforcing block/redaction.

## P0 - MCP Runtime Control

Goal: intercept and control MCP tool calls at runtime.

- [x] Build MCP proxy server MVP.
- [x] Discover Claude/Codex/VS Code MCP config locations and report protection status.
- [x] Import/apply existing Claude/Codex/VS Code MCP server configs through consent-based CLI setup.
- [x] Wrap an explicit MCP config file behind Spectrona.
- [x] Add reversible MCP wrap/undo CLI with backup.
- [x] Add reversible app-level MCP protect/unprotect CLI with backup.
- [x] Intercept tool list requests.
- [x] Intercept tool execution requests.
- [x] Apply policy before every tool execution.
- [x] Block high-risk filesystem access outside allowed roots.
- [x] Block unrestricted shell execution by default.
- [x] Redact secrets from MCP inputs before forwarding.
- [x] Redact secrets from MCP outputs.
- [x] Add MCP dry-run mode that records would-actions without enforcing.
- [x] Add approval-required flow for dangerous MCP tools.
- [x] Add MCP audit log events.
- [x] Add validation fixtures for allowed MCP calls.
- [x] Add validation fixtures for blocked MCP calls.
- [x] Add validation fixtures for approval-required MCP calls.
- [x] Add validation fixtures for MCP config wrap/apply/undo.
- [x] Add validation fixtures for MCP app discovery/status without raw secret output.
- [x] Add validation fixtures for MCP app protect/unprotect and partial repair.
- [x] Add validation fixtures for MCP app drift detection and repair recommendations.
- [x] Add validation fixtures for MCP output redaction before returning tool results.

## P0 - Secret Protection And Encryption

Goal: remove plaintext secrets from normal config and storage paths.

- [x] Add macOS Keychain credential storage.
- [x] Add `spectrona secrets set/get/status/delete` commands.
- [x] Store OpenAI, Anthropic, and optional local provider keys in Keychain.
- [x] Migrate config-file API keys into Keychain with backup.
- [x] Add encrypted-at-rest fields for sensitive local DB content if raw storage is enabled.
- [x] Keep redacted storage as the default.
- [ ] Add secret rotation/status metadata without exposing values.
- [x] Validate normal CLI status, gateway config loading, and packaged-layout checks without exposing stored provider secret values.
- [x] Validate config-key migration backs up, scrubs plaintext keys, stores provider secrets, and does not print secret values.
- [x] Validate current CLI, logs, API responses, and dashboard checks do not print validator secret values.

## P1 - Background Integration Manager

Goal: users should not need repeated CLI intervention after install/setup.

- [ ] Add local setup service or setup UI that detects supported apps.
- [x] Detect Claude Desktop config and MCP config locations for MCP status.
- [x] Detect Codex MCP config locations for MCP status.
- [x] Detect VS Code MCP config locations for MCP status.
- [x] Detect VS Code workspace settings relevant to Claude/Codex/OpenAI-compatible provider routing.
- [x] Detect Ollama running status and default endpoint.
- [x] Detect LM Studio, llama.cpp server, and vLLM endpoints when available.
- [x] Add confirmed UI/API local runtime selection that patches Spectrona config with backup.
- [x] Add CLI protect/unprotect per detected MCP app.
- [x] Add one-click UI protect/unprotect per detected MCP app.
- [x] Extend one-click UI protect/unprotect to provider routing integrations.
- [x] Add aggregate integration manager status/repair for provider routing and MCP app integrations.
- [x] Back up every MCP app config before patching.
- [x] Back up every existing provider routing config before patching.
- [x] Add config drift detection for MCP app configs.
- [x] Add repair flow when MCP app config no longer routes through Spectrona.
- [x] Add config drift detection for Claude/Codex/VS Code provider routing configs.
- [x] Add repair flow when Claude/Codex/VS Code provider routing no longer points to Spectrona.
- [x] Add rollback flow from UI and CLI for provider routing and MCP app configs.
- [x] Add policy rollback flow from UI and CLI.
- [x] Validate Claude/Codex provider routing integration against temp config fixtures.
- [x] Validate aggregate manager repairs Claude/Codex/VS Code routing and VS Code MCP temp fixtures.
- [x] Validate VS Code provider integration against temp config fixtures.

Important constraint:

- `brew install spectrona` should install Spectrona, but should not silently rewrite user app configs. Protection should start through an explicit setup step, UI action, or documented `brew services start spectrona` plus consent-based integration.

## P1 - UI Dashboard

Goal: make the guard layer visible and usable without CLI-first workflows.

- [x] Add gateway-served UI route, for example `/ui`.
- [x] Add read-only dashboard shell backed by real gateway APIs.
- [x] Wire dashboard to gateway health, provider health, recent events, token usage, and recent memory.
- [x] Add UI API endpoint for MCP findings.
- [x] Add UI API endpoint for MCP app integration state.
- [x] Add UI API endpoints for MCP app integration actions.
- [x] Add UI API endpoints for provider integration state/actions.
- [x] Add UI API endpoints for policies.
- [x] Add event store/query API for recent runtime activity.
- [x] Add provider health view.
- [x] Add provider routing view for Claude/Codex/VS Code setup, drift, repair, and remove actions.
- [x] Add protected apps view for Claude/Codex/VS Code MCP configs.
- [x] Add drift badges and repair recommendations to protected apps view.
- [x] Extend provider health/dashboard view to Ollama, LM Studio, llama.cpp, and vLLM local runtime candidates.
- [x] Add confirmed dashboard select action for local LLM runtime candidates.
- [x] Extend provider/app views to VS Code provider routing state.
- [x] Add live traffic table with app/client, provider, model, status, DLP findings, and token totals.
- [x] Add token usage summary and provider totals.
- [x] Add token usage view with daily totals, route totals, model totals, and per-app totals.
- [x] Add MCP scan results view with severity, server name, tool risks, and suggested fixes.
- [x] Add runtime blocks view for denied/approval-required events.
- [x] Add secrets/DLP view showing redaction/block events without raw secrets.
- [x] Surface dry-run would-block, would-approval, and would-redact counts in runtime panels.
- [x] Add recent memory read-only panel.
- [x] Add memory view with search, delete, pin, and redacted/raw state.
- [x] Add policy editor with presets: relaxed, balanced, strict.
- [x] Add policy backup/rollback controls for preset changes.
- [x] Add setup/repair actions for MCP app integrations.
- [x] Add setup/repair view for provider routing integrations.
- [x] Add validation using API smoke tests.
- [x] Add browser screenshot validation when browser tooling is available.

Recommended UI visuals:

- Overview cards for gateway status, protected apps, calls today, tokens today, blocked events, and provider health.
- Live activity stream grouped by allowed, redacted, blocked, and approval-required.
- Token usage charts by provider, app, model, and day.
- MCP risk table with severity colors, server names, risky tools, and remediation actions.
- Secret leakage timeline showing rule id, app, route, and action taken.
- Memory browser with redacted snippets, source app, timestamp, tags, and delete/pin actions.
- Integration checklist showing detected, protected, broken, or not configured status.

## P1 - Token Accounting

Goal: show users cost and usage impact across apps and providers.

- [x] Capture provider usage fields when upstream responses include them.
- [x] Estimate tokens when provider usage is absent.
- [x] Store request and response token counts in runtime event records.
- [x] Aggregate usage by app/client, provider, and model.
- [x] Aggregate usage by route and day.
- [x] Add token usage API endpoint.
- [x] Add token usage UI.
- [x] Validate OpenAI, Anthropic, and local-compatible token accounting paths.

## P1 - Memory Integration With Runtime Calls

Goal: make memory useful, visible, and controlled.

- [x] Capture marked memory candidates from model requests and responses.
- [x] Redact runtime-captured memory before storage and injection.
- [x] Make all raw memory storage opt-in or encrypted by default.
- [x] Add policy gate for raw memory storage.
- [x] Add memory retrieval before model forwarding.
- [x] Inject opt-in relevant memory into prompts only after request policy allows.
- [x] Record which memory items were attached to each request.
- [x] Add stale context detection.
- [x] Add fresh context package API and dashboard preview.
- [x] Add memory audit timeline API and dashboard view.
- [x] Add runtime session extraction preview/apply API and dashboard control.
- [x] Add memory compaction preview/apply API and dashboard control.
- [x] Add metadata-only session replay preview/apply API and dashboard control.
- [x] Add memory search/filter API.
- [x] Add memory delete/pin/update APIs.
- [x] Validate memory search/filter, pin, update, redaction, and confirmed delete APIs.
- [x] Validate redacted fresh context packages exclude stale memory by default.
- [x] Validate memory audit timeline metadata, lifecycle filtering, and raw-secret isolation.
- [x] Validate runtime session extraction metadata, confirmed apply, generated summary, and raw-secret isolation.
- [x] Validate memory compaction duplicate/stale planning, confirmed apply, generated summary, and audit logging.
- [x] Validate metadata-only session replay from runtime events and redacted session summaries with confirmed apply, generated summary, audit logging, and raw-secret isolation.
- [x] Validate default memory writes store redacted content only in SQLite.
- [x] Validate encrypted raw memory opt-in stores decryptable ciphertext without plaintext secrets.
- [x] Validate plaintext raw memory requests are downgraded unless explicitly allowed.
- [x] Validate runtime memory capture, retrieval, redaction, injection, stale filtering, and attachment events.

## P2 - Local LLM Provider Polish

Goal: support common local model runtimes cleanly.

- [x] Generic OpenAI-compatible local endpoint adapter.
- [x] Ollama preset and health behavior.
- [x] LM Studio preset and health behavior.
- [x] llama.cpp server preset and health behavior.
- [x] vLLM preset and health behavior.
- [x] Provider selection in config and UI.
- [x] Fallback routing rules.
- [x] Response-side DLP for local model outputs.
- [x] Validate each adapter with fake local upstreams.
- [x] Validate selected local runtime failure retries through configured local fallback.

## P2 - Published Homebrew Install

Goal: normal users can install and run without cloning the repo.

- [x] Add deterministic release artifact builder and validate local source archive contents/SHA.
- [ ] Publish release artifact.
- [ ] Confirm Homebrew formula URL points to the published release artifact.
- [ ] Replace Homebrew formula placeholder SHA with the published release SHA.
- [ ] Create Homebrew tap.
- [ ] Validate `brew install spectrona` from tap.
- [ ] Validate `brew services start spectrona`.
- [x] Add post-install guidance.
- [ ] Add upgrade/migration flow.
- [ ] Add uninstall cleanup docs.
- [ ] Add CI validation for packaged install.

## P2 - Scanner Expansion

Goal: expand static coverage before and alongside runtime control.

- [x] Add `scan claude`.
- [x] Add `scan cursor`.
- [x] Add `scan repo`.
- [x] Add HTML report output.
- [x] Add high-entropy secret detection.
- [x] Add risky MCP tool description/prompt-injection detection.
- [x] Add suspicious postinstall script detection.
- [x] Add oversized `CLAUDE.md` detector.
- [x] Validate `scan claude` with safe, unsafe, oversized, directory-discovery, JSON, and redaction checks.
- [x] Validate `scan cursor` with safe, unsafe, global MCP, directory-discovery, JSON, and redaction checks.
- [x] Validate `scan repo` with safe, unsafe, git-tracked, JSON, and redaction checks.
- [x] Validate HTML report output, file writing, markup escaping, and raw-secret redaction.
- [x] Validate MCP tool description prompt-injection detection with unsafe/safe fixtures and raw text redaction.
- [x] Validate suspicious postinstall script detection with embedded/local package manifests and raw script redaction.
- [x] Validate every implemented scanner rule with safe and unsafe fixtures.

## Recommended Build Order

1. Published Homebrew tap, release artifact URL/SHA, and `brew services` validation.
2. Secret rotation/status metadata without exposing values.
3. Approval prompt UX beyond metadata-only approval-required actions.
4. CI validation for packaged install and release gates.
5. Upgrade/migration and uninstall cleanup flows for the published install.
