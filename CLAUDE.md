# Spectrona — Engineering Context

## Start-of-session checklist (required)

Read in order before writing any code:

1. docs/MEMORY.md
2. docs/PHASES.md
3. docs/VALIDATION.md
4. docs/DECISIONS.md
5. docs/SESSION_LOG.md
6. validation/README.md

Then determine: active phase / last validation state / exact next task.

## Repo layout

```
spectrona/
├── mcp-inspector/          # Phase 1 — OSS wedge (active)
│   ├── rules/              # YAML risk rule definitions
│   ├── examples/           # fixture configs + sample reports
│   └── validation/         # phase1_validate.sh
├── runtime-guard/          # Phase 2 — policy enforcement (future)
├── claudedb/               # Phase 3 — context freshness (future)
├── policy-engine/          # future
├── docs/                   # MEMORY, PHASES, VALIDATION, DECISIONS, SESSION_LOG
└── validation/             # validate_all.sh (master gate)
```

## Non-negotiable rules

- Never say "done" without running validation.
- Never skip checkpoint before compaction.
- All decisions go in docs/DECISIONS.md.
- All session work goes in docs/MEMORY.md + docs/SESSION_LOG.md.
- Defensive security only — no secret exfiltration, no exploit tooling.

## Active phase

PHASE 1 — mcp-inspector scanner

Master validation: `bash validation/validate_all.sh`
