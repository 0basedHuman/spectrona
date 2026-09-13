import urllib.error

from validation import harvest_mcp_corpus


def test_extract_first_mcp_config_from_wrapped_json():
    text = """
    const ignored = {"notMcp": true};
    export default {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        }
      }
    };
    """

    config = harvest_mcp_corpus._extract_first_mcp_config(text)

    assert config == {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            }
        }
    }


def test_search_queries_fans_out_and_deduplicates():
    calls = []

    def fake_search(query, token, limit):
        calls.append((query, token, limit))
        if query == "first":
            return iter([
                {"html_url": "https://example.test/a", "url": "api-a", "repository": {"full_name": "o/a"}, "path": "a.json"},
                {"html_url": "https://example.test/b", "url": "api-b", "repository": {"full_name": "o/b"}, "path": "b.json"},
            ])
        return iter([
            {"html_url": "https://example.test/b", "url": "api-b2", "repository": {"full_name": "o/b"}, "path": "dupe.json"},
            {"html_url": "https://example.test/c", "url": "api-c", "repository": {"full_name": "o/c"}, "path": "c.json"},
        ])

    items = list(harvest_mcp_corpus._search_queries(["first", "second"], "token", 3, search=fake_search))

    assert [item["html_url"] for item in items] == [
        "https://example.test/a",
        "https://example.test/b",
        "https://example.test/c",
    ]
    assert calls == [("first", "token", 3), ("second", "token", 1)]


def test_default_queries_cover_common_mcp_shapes():
    queries = harvest_mcp_corpus._queries(None)

    assert len(queries) >= 5
    assert any("@modelcontextprotocol" in query for query in queries)
    assert any("uvx" in query for query in queries)
    assert any("npx" in query for query in queries)


def test_quote_url_encodes_content_paths_with_spaces():
    raw = "https://api.github.com/repositories/1/contents/path with space/config.json?ref=abc123"

    assert harvest_mcp_corpus._quote_url(raw) == (
        "https://api.github.com/repositories/1/contents/path%20with%20space/config.json?ref=abc123"
    )


def test_fetch_candidate_config_skips_errors_without_leaking_token(monkeypatch, capsys):
    def fail_fetch(api_url, token):
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(harvest_mcp_corpus, "_fetch_file", fail_fetch)
    item = {
        "url": "https://api.github.test/content",
        "repository": {"full_name": "owner/repo"},
        "path": "claude config.json",
    }

    assert harvest_mcp_corpus._fetch_candidate_config(item, "token-value") is None
    captured = capsys.readouterr()
    assert "token-value" not in captured.err
    assert "URLError" in captured.err
