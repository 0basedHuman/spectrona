import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from spectrona_cli.local_llms import discover_local_llms, local_llm_summary


class ModelListHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"object": "list", "data": [{"id": "local-test-model"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def _start_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelListHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    servers = [_start_server() for _ in range(4)]
    env_pairs = (
        ("SPECTRONA_OLLAMA_BASE_URL", servers[0]),
        ("SPECTRONA_LM_STUDIO_BASE_URL", servers[1]),
        ("SPECTRONA_LLAMA_CPP_BASE_URL", servers[2]),
        ("SPECTRONA_VLLM_BASE_URL", servers[3]),
    )
    for env_name, server in env_pairs:
        os.environ[env_name] = f"http://127.0.0.1:{server.server_port}/v1"

    try:
        statuses = discover_local_llms(
            configured_base_url=os.environ["SPECTRONA_OLLAMA_BASE_URL"],
            configured_provider="openai-compatible",
            live=True,
            timeout_seconds=1.0,
        )
        by_id = {status.runtime_id: status for status in statuses}
        assert set(by_id) == {"ollama", "lm-studio", "llama-cpp", "vllm"}
        assert by_id["ollama"].selected_config is True
        assert by_id["lm-studio"].selected_config is False
        assert by_id["llama-cpp"].selected_config is False
        assert by_id["vllm"].selected_config is False
        for runtime_id, status in by_id.items():
            assert status.adapter == "openai-compatible", runtime_id
            assert status.live_checked is True, runtime_id
            assert status.reachable is True, runtime_id
            assert status.status == "ok", runtime_id
            assert status.status_code == 200, runtime_id
            assert status.api_key_required is False, runtime_id

        summary = local_llm_summary(statuses)
        assert summary["total"] == 4
        assert summary["configured"] == 1
        assert summary["reachable"] == 4
        assert summary["ok"] == 4
        assert summary["live_checked"] is True
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
