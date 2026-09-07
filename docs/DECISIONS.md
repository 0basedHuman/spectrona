# Decision Log

---

## D001 — Start with mcp-inspector scanner, not runtime-guard or ClaudeDB

**Decision:** Phase 1 = mcp-inspector local scanner only.

**Why:** Fastest path to 10k+ downloads and immediate user value. Scanner can be used day-one with zero configuration. Runtime-guard and ClaudeDB require more infrastructure and behavioral change from users.

**Alternatives rejected:**
- Full control plane first — too much infrastructure, no adoption signal
- ClaudeDB first — complex, no immediate value without scanner
- Enterprise dashboard first — wrong sequencing; need OSS traction first

**Impact:** Phase 1 must produce a useful CLI report in under 60 seconds with zero config. Must work on existing MCP/Claude/Cursor configs the user already has.

**Revisit:** After stable rules + JSON output + terminal report + fixture validation pass.

---

## D002 — Rules defined in YAML, not code

**Decision:** Risk rules are YAML files, not hardcoded logic.

**Why:** Allows community contributions without code changes. Easy to add new rules. Separates detection logic from rule definitions.

**Alternatives rejected:**
- Hardcoded rules in scanner — hard to contribute, couples rule content to release cycle

**Impact:** Scanner must load and interpret YAML rules. Rule format must be stable from Day 1.

**Revisit:** If YAML becomes a bottleneck for complex detection logic (e.g., entropy calculations).

---

## D003 — Open-source mcp-inspector, private runtime-guard and ClaudeDB

**Decision:** mcp-inspector (scanner + rules + examples) is public OSS. runtime-guard and ClaudeDB are private/pro.

**Why:** OSS scanner maximizes adoption and trust. Monetization comes from enforcement and context layers, not detection.

**Alternatives rejected:**
- Fully closed-source — no adoption signal, no community trust
- Fully open-source — no monetization path

**Impact:** mcp-inspector must be genuinely useful standalone. Pro features must be clearly valuable beyond free tier.

**Revisit:** After Phase 1 ships and download metrics are established.

---

## D004 — Local-first, no external data transmission

**Decision:** All scanning happens locally. No config data, secrets, or findings are sent externally.

**Why:** Security products that transmit user data are a liability. Trust requires local-first operation. Users will not adopt a security tool that phones home.

**Impact:** No analytics on findings. No remote rule updates (rules ship with the package). Report stays on disk.

**Revisit:** If aggregated (non-identifying) telemetry is explicitly opt-in with clear disclosure.

---

## D005 — Detection quality is measured by corpus precision

**Decision:** Detection work is measured by precision and recall against the config corpus, not by increasing bash check counts. Until R8 lands the corpus benchmark, defect fixes are measured by a reproduced defect becoming absent with a permanent pytest regression.

**Why:** The review found that check-count growth rewarded adding rules, including unactionable rules such as `MCP_NO_AUDIT_LOG`, while real reproduced defects still passed the old harness. Detector behavior needs unit/regression tests and a precision target, not more stdout greps.

**Alternatives rejected:**
- Keep check count as the headline metric — reinforces the failure mode that produced F7/F9.
- Remove bash validation entirely — loses useful end-to-end smoke coverage for CLI, gateway binding, packaging, and dashboard rendering.
- Wait for R8 before adding pytest — leaves fixed defects without a real regression harness.

**Impact:** `pytest` is now wired into `validation/validate_all.sh` and owns detector/regression assertions. Bash validation remains for scaffold and end-to-end smoke. Known open defects are represented as strict xfail tests until their queue item lands.

**Revisit:** After R8 establishes the public MCP config corpus and precision/recall benchmark.

---

## D006 — Runtime enforcement is advisory until measured

**Decision:** The MCP runtime proxy ships advisory-only by default. Blocking and redaction enforcement require an explicit opt-in through `--enforce` or `SPECTRONA_MCP_ENFORCE=true`.

**Why:** F2 reproduced that the current shell-risk detector can classify ordinary English text as shell risk. Until R7 rewrites detection and R8 measures precision on real traffic/configs, blocking by default can mislead users and interrupt valid work.

**Alternatives rejected:**
- Keep blocking by default — preserves a known false-positive blocker.
- Remove runtime policy behavior entirely — loses useful audit and dry-run visibility.
- Fix shell-risk detection in R5 — violates the queue boundary; R7 owns the detector rewrite.

**Impact:** Wrapped MCP configs and `spectrona mcp protect` stay advisory unless the operator explicitly opts into enforcement. Audit logs record would-block/would-redact metadata without raw MCP payloads.

**Revisit:** After R7 detection rewrite and R8 precision benchmark establish an acceptable false-positive rate.

---

## D007 — Detection is implemented in code, not loaded from YAML

**Decision:** D002 is amended: Spectrona detection is implemented in code. YAML rule files remain a rule catalog and documentation until a future loader can express detector behavior safely.

**Why:** The real detectors need recursive JSON walking, redaction-safe evidence, entropy/structure checks, and runtime context that a simple YAML loader does not currently provide. Leaving D002 as-is described a system that was not built.

**Alternatives rejected:**
- Build a YAML loader in R7 — would add indirection without covering structural validation, redaction, or runtime schema-aware risk checks.
- Leave D002 stale — keeps documenting a nonexistent execution path.

**Impact:** New or changed detection behavior must land as code with pytest coverage and, after R8, corpus precision/recall evidence. Rule IDs and severities can still be documented in YAML catalogs.

**Revisit:** After R8 establishes the config corpus and precision benchmark; reconsider a declarative layer only for checks that can meet the precision gate.

---

## D008 — Delete unactionable MCP audit-log finding

**Decision:** `MCP_NO_AUDIT_LOG` is removed from scanner rules, detector code, fixtures, validation, and reports.

**Why:** The review reproduced that the rule fires on correct MCP configurations because `auditLog` is not part of the MCP specification. A safe fixture had been modified to include an invented key, which manufactured a clean case instead of proving precision.

**Alternatives rejected:**
- Keep the rule at LOW severity — still creates noise on every real config and trains users to ignore findings.
- Keep the rule but require invented config keys in safe fixtures — preserves a false signal and contradicts the MCP spec.

**Impact:** Scanner output is quieter and more honest. Missing runtime auditability remains a product/runtime concern, not a static MCP config finding.

**Revisit:** After R8 establishes a public config corpus and precision benchmark; reintroduce only if a standards-backed, actionable signal meets the precision gate.

---

## D010 — Corpus benchmark stores redacted labeled metadata

**Decision:** R8 corpus data committed to the repo must be redacted, source-attributed, hand-labeled metadata. Full GitHub harvesting is performed by `validation/harvest_mcp_corpus.py`, but harvested candidates are not benchmark inputs until a human fills `expected_finding_ids`.

**Why:** Public configs can contain real credentials and private paths. The benchmark needs reproducible precision/recall evidence without turning the repository into a credential cache or trusting unlabeled crawler output.

**Alternatives rejected:**
- Commit raw harvested MCP configs — violates the no-secret-leakage invariant.
- Treat crawler output as labels — would make precision/recall meaningless.
- Wait for the full 1,000-case corpus before landing the benchmark harness — delays the validation mechanism R8 is meant to establish.

**Impact:** `validation/corpus_benchmark.py` gates measured rules at 95% precision. The committed seed corpus proves the format and benchmark contract; the full R8 completion requires running the harvester with GitHub access, generating a `validation/corpus_label_queue.py` review queue, and promoting manually labeled redacted cases through `validation/corpus_promote_labeled.py`. Scanner predictions in the queue are reviewer triage metadata, not labels, and promotion strips them from benchmark inputs.

**Revisit:** After the full corpus reaches roughly 1,000 labeled public configurations.

---

## D011 — Initial Git repository excludes local and generated artifacts

**Decision:** The first Git commit tracks source, docs, fixtures, validation scripts, and the intentional unsafe `.env` scanner fixture. It excludes local agent settings, pytest caches, bytecode, logs, build outputs, package caches, and ordinary developer `.env` files.

**Why:** The workspace was not a Git repository when the GitHub remote was requested. The initial push needed a clean repository boundary that preserves validation fixtures without publishing local machine permissions or generated files.

**Alternatives rejected:**
- Commit every file in the workspace — would publish `.claude/settings.local.json`, caches, bytecode, and other local state.
- Ignore every `.env` file — would drop `mcp-inspector/examples/unsafe-repos/basic/.env`, which is an intentional scanner regression fixture.

**Impact:** `origin` points at `https://github.com/0basedHuman/spectrona.git`, and `main` now tracks `origin/main`. Future fixture `.env` files must be explicitly whitelisted if they are required for validation.

**Revisit:** If repository layout changes or additional fixture secret-shape files are added.
