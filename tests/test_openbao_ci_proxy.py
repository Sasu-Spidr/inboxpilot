from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scripts.openbao_ci_proxy import make_server


class FakeBaoHandler(BaseHTTPRequestHandler):
    received_token = ""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        type(self).received_token = self.headers.get("X-Vault-Token", "")
        body = json.dumps({"data": {"data": {"api_key": "not-logged"}}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def test_ci_proxy_forwards_only_allowlisted_paths_with_the_ephemeral_token():
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), FakeBaoHandler)
    proxy = make_server(
        f"http://127.0.0.1:{upstream.server_port}",
        "short-lived-token",
        "127.0.0.1",
        0,
    )
    upstream_thread = run(upstream)
    proxy_thread = run(proxy)
    try:
        allowed = urllib.request.urlopen(
            f"http://127.0.0.1:{proxy.server_port}/v1/secret/data/inboxpilot/groq",
            timeout=2,
        )
        assert allowed.status == 200
        assert FakeBaoHandler.received_token == "short-lived-token"

        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(
                f"http://127.0.0.1:{proxy.server_port}/v1/secret/data/inboxpilot/frontend",
                timeout=2,
            )
        assert denied.value.code == 403
    finally:
        proxy.shutdown()
        upstream.shutdown()
        proxy.server_close()
        upstream.server_close()
        proxy_thread.join(timeout=2)
        upstream_thread.join(timeout=2)


def test_ci_proxy_health_endpoint_does_not_contact_openbao():
    proxy = make_server("http://127.0.0.1:1", "token", "127.0.0.1", 0)
    thread = run(proxy)
    try:
        response = urllib.request.urlopen(
            f"http://127.0.0.1:{proxy.server_port}/healthz",
            timeout=2,
        )
        assert response.status == 204
    finally:
        proxy.shutdown()
        proxy.server_close()
        thread.join(timeout=2)
