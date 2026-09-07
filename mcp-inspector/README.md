# mcp-inspector

Open-source local-first security scanner for MCP configs, Claude configs, Cursor configs, and repos.

**Status:** Phase 1 scanner is implemented for MCP, Claude, Cursor, repo-level secret, prompt-injection, and supply-chain risks.

## What it detects

| Category | Examples |
|---|---|
| MCP permissions | filesystem access outside repo, unrestricted shell |
| Secrets | API keys in env, high-entropy values, .env not in .gitignore |
| Prompt injection | risky tool descriptions, cursorrules directives |
| Supply chain | unpinned packages, postinstall scripts |
| Claude config | oversized CLAUDE.md, dangerous permissions, hook injection |

## Commands

```bash
mcp-inspector scan                  # scan everything
mcp-inspector scan mcp              # scan MCP configs only
mcp-inspector scan claude           # scan Claude configs
mcp-inspector scan cursor           # scan Cursor configs
mcp-inspector scan repo             # scan repo structure
mcp-inspector report --json         # JSON output
mcp-inspector report --html         # HTML report
```

Currently implemented: `scan mcp`, `scan claude`, `scan cursor`, `scan repo`, JSON reports, HTML reports, risky MCP tool description detection, and suspicious postinstall detection.

## Validation

```bash
bash mcp-inspector/validation/phase1_validate.sh
```

## Rule files

- `rules/mcp-risk-rules.yaml` — MCP server risks
- `rules/claude-risk-rules.yaml` — Claude config risks
- `rules/cursor-risk-rules.yaml` — Cursor config risks
- `rules/secrets-risk-rules.yaml` — Secret detection

## Examples

- `examples/unsafe-mcp-configs/` — fixtures that should trigger HIGH/CRITICAL
- `examples/safe-mcp-configs/` — fixtures that should produce no findings
- `examples/unsafe-claude-configs/` — Claude settings fixtures that should trigger findings
- `examples/safe-claude-configs/` — Claude settings fixtures that should produce no findings
- `examples/unsafe-cursor-configs/` — Cursor fixtures that should trigger findings
- `examples/safe-cursor-configs/` — Cursor fixtures that should produce no findings
- `examples/unsafe-repos/` — repo fixtures that should trigger findings
- `examples/safe-repos/` — repo fixtures that should produce no findings
- `examples/sample-reports/` — expected report output
