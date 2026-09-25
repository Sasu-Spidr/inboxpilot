#!/usr/bin/env python3
"""Expose a loopback-only OpenBao proxy for the short-lived CI smoke job."""
from __future__ import annotations

import argparse
import json
import stat
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ALLOWED_PATHS = {
    "/v1/secret/data/inboxpilot/crypto",
    "/v1/secret/data/inboxpilot/groq",
    "/v1/secret/data/inboxpilot/oauth/gmail",
    "/v1/secret/data/inboxpilot/oauth/microsoft",
}


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "InboxPilotOpenBaoCI/1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/healthz":
            self.send_response(204)
            self.end_headers()
            return
        if self.path not in ALLOWED_PATHS:
            self._json_error(403, "path is not allowed by the CI proxy")
            return

        server = self.server
        request = urllib.request.Request(
            f"{server.bao_address}{self.path}",  # type: ignore[attr-defined]
            headers={"X-Vault-Token": server.bao_token},  # type: ignore[attr-defined]
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = exc.code
            content_type = exc.headers.get("Content-Type", "application/json")
        except urllib.error.URLError:
            self._json_error(502, "OpenBao is unavailable")
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status: int, message: str) -> None:
        body = json.dumps({"errors": [message]}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(address: str, token: str, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ProxyHandler)
    server.bao_address = address.rstrip("/")  # type: ignore[attr-defined]
    server.bao_token = token  # type: ignore[attr-defined]
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8100, type=int)
    args = parser.parse_args()

    if not args.token_file.is_file():
        raise SystemExit("OpenBao token file does not exist")
    if args.token_file.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise SystemExit("OpenBao token file must be mode 0600")
    token = args.token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("OpenBao token file is empty")
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("The CI proxy may only listen on loopback")

    server = make_server(args.address, token, args.host, args.port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
