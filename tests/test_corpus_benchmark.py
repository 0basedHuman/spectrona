from validation import corpus_benchmark


def test_seed_corpus_precision_benchmark_passes():
    assert corpus_benchmark.main(["--min-size", "10"]) == 0


def test_seed_corpus_json_contract_has_no_failed_rules():
    cases = corpus_benchmark._load_cases(corpus_benchmark.DEFAULT_CORPUS)
    result = corpus_benchmark._run_benchmark(cases, 0.95)

    assert result["corpus_cases"] >= 10
    assert result["failed_rules"] == []
    assert all(
        item["precision"] is None or item["precision"] >= 0.95
        for item in result["rules"].values()
    )
