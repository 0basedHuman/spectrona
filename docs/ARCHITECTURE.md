# Architecture

## Phase 1 — mcp-inspector

```
mcp-inspector/
├── rules/                  # YAML rule definitions (static, shipped with package)
│   ├── mcp-risk-rules.yaml
│   ├── claude-risk-rules.yaml
│   ├── cursor-risk-rules.yaml
│   └── secrets-risk-rules.yaml
│
├── src/                    # Scanner implementation (to be created)
│   ├── scanner.py          # Main entry point
│   ├── rule_loader.py      # Load + parse YAML rules
│   ├── parsers/
│   │   ├── mcp_parser.py   # Parse mcp.json / .mcp.json
│   │   ├── claude_parser.py
│   │   └── cursor_parser.py
│   ├── detectors/
│   │   ├── mcp_detector.py
│   │   ├── secrets_detector.py
│   │   └── config_detector.py
│   └── reporters/
│       ├── terminal_reporter.py
│       ├── json_reporter.py
│       └── html_reporter.py
│
├── examples/               # Fixture configs + expected reports
└── validation/             # Validation scripts
```

## Data flow

```
User runs: mcp-inspector scan mcp <path>
    │
    ▼
[mcp_parser] → raw config dict
    │
    ▼
[rule_loader] → list of Rule objects from YAML
    │
    ▼
[mcp_detector + secrets_detector] → list of Finding objects
    │
    ▼
[terminal_reporter | json_reporter | html_reporter] → output
```

## Finding schema

```python
Finding(
    id: str,              # e.g. "MCP_FS_OUTSIDE_REPO"
    title: str,
    severity: Literal["critical", "high", "medium", "low"],
    category: str,
    source: str,          # e.g. "mcpServers.filesystem.args"
    evidence: str,        # redacted value
    why_it_matters: str,
    recommended_fix: str,
    confidence: Literal["high", "medium", "low"]
)
```

## Key constraints

- Local-first: zero network calls
- No secret values in output (redact to first 4 chars + "...")
- Must run in under 60 seconds on any normal repo
- No mandatory config file — works out of the box on existing configs
