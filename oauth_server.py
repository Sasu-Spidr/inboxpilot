from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import msal
import yaml
from google_auth_oauthlib.flow import Flow

from gmail_connector import SCOPES as GMAIL_SCOPES, json_credentials
from hotmail_connector import SCOPES as HOTMAIL_SCOPES
from token_store import TokenStore

LOG = logging.getLogger("spidr_oauth")


class OAuthOnboardingServer:
    def __init__(self, settings: dict, base_url: str):
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.store = TokenStore(settings["token_encryption_key"])

    def handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - stdlib API
                try:
                    parsed = urlparse(self.path)
                    if parsed.path == "/":
                        self._html(200, render_home(server.settings))
                    elif parsed.path == "/health":
                        self._text(200, "ok")
                    elif parsed.path == "/connect/gmail":
                        self._redirect(server.start_gmail(parsed.query))
                    elif parsed.path == "/oauth/gmail/callback":
                        self._html(200, server.finish_gmail(parsed.query))
                    elif parsed.path == "/connect/hotmail":
                        self._redirect(server.start_hotmail(parsed.query))
                    elif parsed.path == "/oauth/hotmail/callback":
                        self._html(200, server.finish_hotmail(parsed.query))
                    else:
                        self._html(404, page("Lien introuvable", "Cette page n’existe pas."))
                except Exception as exc:
                    LOG.exception("OAuth onboarding failed")
                    self._html(500, page("Connexion impossible", f"Erreur : {escape(str(exc))}"))

            def log_message(self, fmt, *args):
                LOG.info("%s - %s", self.address_string(), fmt % args)

            def _redirect(self, url: str):
                self.send_response(302)
                self.send_header("Location", url)
                self.end_headers()

            def _text(self, status: int, text: str):
                body = text.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _html(self, status: int, html: str):
                body = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler

    def start_gmail(self, query: str) -> str:
        client_id, account, account_cfg = self._account(query, "gmail")
        redirect_uri = f"{self.base_url}/oauth/gmail/callback"
        flow = Flow.from_client_secrets_file(account_cfg["credentials_file"], scopes=GMAIL_SCOPES, redirect_uri=redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=self._sign_state("gmail", client_id, account),
        )
        return auth_url

    def finish_gmail(self, query: str) -> str:
        params = parse_qs(query)
        if "error" in params:
            return page("Connexion Gmail refusée", f"Google a retourné : {escape(params['error'][0])}")
        state = self._verify_state(one(params, "state"), "gmail")
        _, _, account_cfg = self._account(urlencode({"client": state["client"], "account": state["account"]}), "gmail")
        redirect_uri = f"{self.base_url}/oauth/gmail/callback"
        flow = Flow.from_client_secrets_file(account_cfg["credentials_file"], scopes=GMAIL_SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(code=one(params, "code"))
        self.store.save(account_cfg["token_file"], json_credentials(flow.credentials))
        return success_page("Gmail", state["client"], state["account"], account_cfg["token_file"])

    def start_hotmail(self, query: str) -> str:
        client_id, account, account_cfg = self._account(query, "hotmail")
        redirect_uri = f"{self.base_url}/oauth/hotmail/callback"
        app = microsoft_app(account_cfg)
        return app.get_authorization_request_url(
            scopes=HOTMAIL_SCOPES,
            state=self._sign_state("hotmail", client_id, account),
            redirect_uri=redirect_uri,
            prompt="select_account",
        )

    def finish_hotmail(self, query: str) -> str:
        params = parse_qs(query)
        if "error" in params:
            return page("Connexion Hotmail refusée", f"Microsoft a retourné : {escape(params['error'][0])}")
        state = self._verify_state(one(params, "state"), "hotmail")
        _, _, account_cfg = self._account(urlencode({"client": state["client"], "account": state["account"]}), "hotmail")
        cache = msal.SerializableTokenCache()
        app = microsoft_app(account_cfg, cache)
        result = app.acquire_token_by_authorization_code(
            code=one(params, "code"),
            scopes=HOTMAIL_SCOPES,
            redirect_uri=f"{self.base_url}/oauth/hotmail/callback",
        )
        if "access_token" not in result:
            raise RuntimeError(result.get("error_description", str(result)))
        self.store.save(account_cfg["token_file"], {"cache": cache.serialize()})
        return success_page("Hotmail / Outlook", state["client"], state["account"], account_cfg["token_file"])

    def _account(self, query: str, connector: str) -> tuple[str, str, dict]:
        params = parse_qs(query)
        client_id = one(params, "client")
        account = params.get("account", ["main"])[0] or "main"
        clients = self.settings.get("clients", {})
        if client_id not in clients:
            raise ValueError(f"Client inconnu : {client_id}")
        connector_cfg = clients[client_id].get("connectors", {}).get(connector, {})
        for account_cfg in connector_cfg.get("accounts", []):
            account_name = account_cfg.get("account") or account_cfg.get("id") or connector
            if account_name == account:
                return client_id, account, account_cfg
        raise ValueError(f"Compte {connector}/{account} introuvable pour le client {client_id}")

    def _sign_state(self, provider: str, client_id: str, account: str) -> str:
        payload = {"provider": provider, "client": client_id, "account": account, "ts": int(time.time())}
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        sig = hmac.new(self.settings["token_encryption_key"].encode("utf-8"), raw, hashlib.sha256).digest()
        return b64(raw) + "." + b64(sig)

    def _verify_state(self, state: str, provider: str) -> dict:
        raw_b64, sig_b64 = state.split(".", 1)
        raw = b64decode(raw_b64)
        expected = hmac.new(self.settings["token_encryption_key"].encode("utf-8"), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, b64decode(sig_b64)):
            raise ValueError("State OAuth invalide")
        payload = json.loads(raw)
        if payload.get("provider") != provider:
            raise ValueError("Provider OAuth invalide")
        if int(time.time()) - int(payload.get("ts", 0)) > 900:
            raise ValueError("Lien OAuth expiré, veuillez recommencer")
        return payload


def microsoft_app(account_cfg: dict, cache=None):
    client_id = account_cfg.get("client_id") or os.getenv(account_cfg.get("client_id_env", "MICROSOFT_CLIENT_ID"), "")
    if not client_id:
        raise ValueError("Microsoft client_id manquant")
    authority = f"https://login.microsoftonline.com/{account_cfg.get('tenant_id', 'consumers')}"
    return msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)


def load_settings(path: str) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(os.path.expandvars(raw))


def one(params: dict, key: str) -> str:
    value = params.get(key, [""])[0]
    if not value:
        raise ValueError(f"Paramètre manquant : {key}")
    return value


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def render_home(settings: dict) -> str:
    links = []
    for client_id, client in settings.get("clients", {}).items():
        for connector in ("gmail", "hotmail"):
            for account in client.get("connectors", {}).get(connector, {}).get("accounts", []):
                account_name = account.get("account") or account.get("id") or "main"
                links.append(f'<li><a href="/connect/{connector}?client={escape(client_id)}&account={escape(account_name)}">{escape(client_id)} - {connector} - {escape(account_name)}</a></li>')
    return page("Connexion boîte mail", "<p>Choisissez le compte à connecter :</p><ul>" + "\n".join(links) + "</ul>")


def success_page(provider: str, client_id: str, account: str, token_file: str) -> str:
    return page(
        f"Connexion {escape(provider)} réussie",
        f"<p>Le compte <strong>{escape(client_id)} / {escape(account)}</strong> est connecté.</p>"
        "<p>Vous pouvez fermer cette page.</p>"
        f"<p class='muted'>Token chiffré enregistré : {escape(token_file)}</p>",
    )


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 720px; margin: 64px auto; padding: 0 24px; line-height: 1.5; color: #202124; }}
    a {{ color: #0b57d0; }}
    .muted {{ color: #666; font-size: 14px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {body}
</body>
</html>"""


def escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--host", default=os.getenv("OAUTH_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("OAUTH_PORT", "8080")))
    parser.add_argument("--base-url", default=os.getenv("OAUTH_BASE_URL", "http://localhost:8080"))
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
    server = OAuthOnboardingServer(load_settings(args.config), args.base_url)
    httpd = ThreadingHTTPServer((args.host, args.port), server.handler())
    LOG.info("OAuth onboarding listening on %s:%s base_url=%s", args.host, args.port, args.base_url)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
