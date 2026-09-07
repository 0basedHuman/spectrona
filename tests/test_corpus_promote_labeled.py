import json

from validation import corpus_label_queue, corpus_promote_labeled


def test_promote_rejects_unlabeled_queue_records(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    output_path = tmp_path / "labeled.jsonl"
    assert corpus_label_queue.main([
        "--input",
        str(corpus_label_queue.ROOT / "validation" / "corpus" / "mcp_configs_seed.jsonl"),
        "--output",
        str(queue_path),
        "--sample-size",
        "2",
    ]) == 0

    assert corpus_promote_labeled.main([
        "--input",
        str(queue_path),
        "--output",
        str(output_path),
    ]) == 2
    assert not output_path.exists()


def test_promote_strips_prediction_only_fields(tmp_path):
    queue_path = tmp_path / "queue.jsonl"
    labeled_path = tmp_path / "queue_labeled.jsonl"
    output_path = tmp_path / "labeled.jsonl"
    assert corpus_label_queue.main([
        "--input",
        str(corpus_label_queue.ROOT / "validation" / "corpus" / "mcp_configs_seed.jsonl"),
        "--output",
        str(queue_path),
        "--sample-size",
        "3",
    ]) == 0

    rows = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
    with labeled_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            row["reviewed"] = True
            row["expected_finding_ids"] = row["predicted_finding_ids"]
            row["label_notes"] = "Reviewed for promotion test."
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    assert corpus_promote_labeled.main([
        "--input",
        str(labeled_path),
        "--output",
        str(output_path),
        "--min-size",
        "3",
        "--check-benchmark",
    ]) == 0

    promoted = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(promoted) == 3
    assert all("predicted_finding_ids" not in row for row in promoted)
    assert all("scanner_findings" not in row for row in promoted)
    assert all("reviewed" not in row for row in promoted)
