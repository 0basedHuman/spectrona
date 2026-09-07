# policy-engine

**Status:** MVP active and validated.

## Role

The policy engine evaluates runtime rules against incoming model or future MCP actions and returns an `allow`, `deny`, `redact`, or `require_approval` decision.

It is designed to be:
- Embedded in the Spectrona gateway
- Reused by future MCP runtime control
- Dependency-free for local packaging
- Extensible with new rule matchers

## Current match fields

- `route`
- `provider_type`
- `client` / `app`
- `model`
- `dlp_findings_min`
- `dlp_findings_count`
- `filesystem_risk`
- `shell_risk`

## Validation

```bash
bash policy-engine/validation/policy_validate.sh
```
