# runtime-guard

**Status:** Phase 2 — MCP proxy MVP active.

## Built

- Dependency-free Python package: `runtime_guard`
- MCP stdio JSON-RPC proxy entry point: `spectrona-mcp-proxy`
- Top-level CLI path: `spectrona mcp proxy`
- MCP config wrapper: `spectrona mcp wrap`
- MCP config restore path: `spectrona mcp undo`
- MCP app discovery/status: `spectrona mcp apps`
- MCP app protect path: `spectrona mcp protect <app-id>`
- MCP app restore path: `spectrona mcp unprotect <app-id>`
- Read-only detection for Claude Code, Claude Desktop, Codex, VS Code user, and workspace MCP configs
- MCP app config drift detection and metadata-only repair recommendations
- Restore of missing app configs when a Spectrona backup exists
- Policy evaluation for `tools/call`
- Shell-risk and filesystem-risk detection
- `allow`, `deny`, `require_approval`, and `redact` decisions via `policy-engine`
- Advisory dry-run mode by default; blocking/redaction enforcement requires `--enforce` or `SPECTRONA_MCP_ENFORCE=true`
- Redaction of MCP tool inputs before forwarding to an upstream command
- Metadata-only MCP audit log at `~/.spectrona/logs/mcp_audit.jsonl` by default

## Still planned

- Provider routing setup/repair
- Redact MCP tool outputs
- Per-project MCP allowlists
- Per-tool deny rules
- Approval prompt UX
- Shell wrapper and git wrapper
- Claude hooks integration

## Run

```bash
spectrona mcp proxy
```

By default the proxy audits policy decisions without blocking or redacting MCP traffic. Opt into enforcement only after accepting the current detector false-positive risk:

```bash
spectrona mcp proxy --enforce
```

With a manually supplied upstream MCP server command:

```bash
spectrona mcp proxy -- npx -y @example/mcp-server
```

Wrap an existing MCP config into a new file:

```bash
spectrona mcp wrap ~/.claude/mcp.json --repo-root . --output ~/.claude/mcp.spectrona.json
```

Apply wrapping in place with a backup:

```bash
spectrona mcp wrap ~/.claude/mcp.json --repo-root . --apply
spectrona mcp undo ~/.claude/mcp.json
```

Show detected MCP app protection status without printing server env values:

```bash
spectrona mcp apps
spectrona mcp apps --json
```

Protect or restore a detected app config by app id:

```bash
spectrona mcp protect claude-code
spectrona mcp unprotect claude-code
```

This MVP provides the executable proxy/policy layer, reversible config wrapping, app MCP status discovery, drift detection, metadata-only repair recommendations, and explicit consent-based app protect/unprotect commands.

## Validation

```bash
bash runtime-guard/validation/phase2_validate.sh
```
