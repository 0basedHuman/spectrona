# ClaudeDB

**Status:** Phase 3 — NOT STARTED. Requires Phase 2 (runtime-guard) to ship first.

## Planned capabilities

- Local SQLite / JSONL audit store
- Memory extraction from Claude sessions
- Stale context detection (files changed since last session)
- Audit timeline — who did what, when
- Session replay — reconstruct what Claude saw
- Fresh context packaging — "here's what Claude needs to know to resume"

## Why

Claude Code sessions accumulate context debt:
- Old file versions referenced in memory
- Decisions made in previous sessions not visible
- No structured audit of what Claude actually did

ClaudeDB solves this with a local-first structured store.

## Validation

```bash
bash claudedb/validation/phase3_validate.sh
```
