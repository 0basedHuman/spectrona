import json

from validation import corpus_label_queue


def test_label_queue_writes_stratified_unlabeled_records(tmp_path):
    output = tmp_path / "queue.jsonl"

    assert corpus_label_queue.main([
        "--input",
        str(corpus_label_queue.ROOT / "validation" / "corpus" / "mcp_configs_seed.jsonl"),
        "--output",
        str(output),
        "--sample-size",
        "5",
        "--json",
    ]) == 0

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert 1 <= len(rows) <= 5
    assert all("predicted_finding_ids" in row for row in rows)
    assert all("scanner_findings" in row for row in rows)
    assert all(row["label_notes"].startswith("UNLABELED") for row in rows)


def test_label_queue_keeps_review_secret_samples_out(tmp_path):
    output = tmp_path / "queue.jsonl"

    assert corpus_label_queue.main([
        "--input",
        str(corpus_label_queue.ROOT / "validation" / "corpus" / "mcp_configs_seed.jsonl"),
        "--output",
        str(output),
        "--sample-size",
        "12",
    ]) == 0

    text = output.read_text(encoding="utf-8")
    assert "REALSECRETVALUE123456" not in text
    assert "SuperSecret123" not in text
    assert "sk_live_51H8xYzAbCdEfGhIjKlMnOp" not in text
