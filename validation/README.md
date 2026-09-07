# Validation

## Master command

```bash
bash validation/validate_all.sh
```

Runs all phase validation scripts in sequence. Fails if any phase fails.

## Phase scripts

| Script | Phase | Status |
|---|---|---|
| validation/pytest_validate.sh | Regression suite — pytest | ACTIVE |
| validation/corpus_validate.sh | R8 corpus precision benchmark | ACTIVE |
| mcp-inspector/validation/phase1_validate.sh | Phase 1 — mcp-inspector | ACTIVE |
| runtime-guard/validation/phase2_validate.sh | Phase 2 — runtime-guard | ACTIVE |
| claudedb/validation/phase3_validate.sh | Phase 3 — ClaudeDB | SKIPPED (not started) |

## Rules

- Never claim a feature is done without running validation.
- Always run validate_all.sh before checkpointing a session.
- Pytest owns detector and regression assertions; bash scripts are retained for smoke and integration coverage.
- R8 corpus validation checks the seed benchmark, harvester query breadth, offline labeling workflow, and labeled-record promotion guard; full GitHub harvesting remains token/network-gated and manual.
- A SKIP result is acceptable for phases not yet started.
- A FAIL result must be fixed before moving on.
