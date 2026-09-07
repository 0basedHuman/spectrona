# MCP Config Corpus

This directory stores redacted, hand-labeled MCP configuration examples for the
R8 precision benchmark.

The committed seed corpus is intentionally small and source-attributed. It keeps
raw harvested credentials out of the repo and exercises the benchmark format.
Scale-up harvesting uses `validation/harvest_mcp_corpus.py`, which fans out
across several GitHub code-search queries for common MCP config shapes. The
resulting candidate file is converted into a review queue with
`validation/corpus_label_queue.py`, which attaches scanner predictions and
redacted evidence as metadata. Humans must still set `expected_finding_ids`
before entries are promoted with `validation/corpus_promote_labeled.py` into
`mcp_configs_seed.jsonl` or a larger private/public corpus file.

Each JSONL record contains:

- `case_id`: stable identifier
- `source_url`: public source or synthetic regression source
- `source_type`: `public_docs`, `public_repo`, or `synthetic_regression`
- `repo_root`: benchmark repo root token; defaults to the temp workspace
- `config`: redacted MCP config object
- `files`: optional local files materialized beside the config
- `expected_finding_ids`: scanner finding IDs expected for the case
- `label_notes`: short rationale for the expected labels

Labeling queue records also include:

- `predicted_finding_ids`: scanner output for reviewer triage only
- `scanner_findings`: redacted scanner finding metadata for reviewer triage only

Promotion strips those prediction-only fields. A queue record must have human
labels, non-`UNLABELED` notes, and `reviewed: true` before promotion.

Do not commit raw public credentials. If a public config contains a credential,
replace it with a synthetic value that preserves shape or omit the value and
record only metadata.
