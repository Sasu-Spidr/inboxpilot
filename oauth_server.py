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

from client_registry import merge_registered_clients
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
                    params = parse_qs(parsed.query)
                    if parsed.path == "/":
                        self._html(200, render_home(server.settings))
                    elif parsed.path == "/login":
                        self._html(200, render_login())
                    elif parsed.path == "/register":
                        self._html(200, render_register())
                    elif parsed.path == "/client":
                        self._html(200, render_auth_required())
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
                        self._html(404, page("Lien introuvable", "Cette page n'existe pas."))
                except Exception as exc:
                    LOG.exception("OAuth onboarding failed")
                    self._html(500, page("Connexion impossible", f"Erreur : {escape(str(exc))}"))

            def do_POST(self):  # noqa: N802 - stdlib API
                try:
                    parsed = urlparse(self.path)
                    length = int(self.headers.get("Content-Length", "0"))
                    self.rfile.read(length)
                    self._html(
                        405,
                        page(
                            "Authentification désactivée ici",
                            f"""
                            <div class="panel">
                              <p class="eyebrow">SPIDR Mail Agent</p>
                              <h1>Utilisez votre espace client.</h1>
                              <p>L'authentification se fait depuis l'interface sécurisée. Ce serveur sert uniquement à finaliser la connexion Gmail ou Outlook.</p>
                              <p><a class="button primary" href="{escape(frontend_url())}">Retour à l'interface</a></p>
                            </div>
                            """,
                        ),
                    )
                except Exception as exc:
                    LOG.exception("OAuth onboarding form failed")
                    self._html(500, page("Action impossible", f"Erreur : {escape(str(exc))}"))

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
        return success_page("Gmail", state["client"], state["account"])

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
        return success_page("Hotmail / Outlook", state["client"], state["account"])

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
    return merge_registered_clients(yaml.safe_load(os.path.expandvars(raw)))


def one(params: dict, key: str) -> str:
    value = params.get(key, [""])[0].strip()
    if not value:
        raise ValueError(f"Paramètre manquant : {key}")
    return value


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def render_home(settings: dict) -> str:
    return page(
        "Authentification SPIDR Mail Agent",
        f"""
        <section class="hero">
          <p class="eyebrow">SPIDR Mail Agent</p>
          <h1>Connectez-vous à votre espace client.</h1>
          <p>Depuis votre espace, vous pourrez connecter Gmail ou Outlook. Ce serveur OAuth ne liste aucun client et ne donne accès à aucun espace privé.</p>
          <div class="actions">
            <a class="button primary" href="{escape(frontend_url())}">Ouvrir mon espace</a>
          </div>
        </section>
        """,
    )


def render_login() -> str:
    return page(
        "Connexion client",
        f"""
        <div class="panel">
          <p class="eyebrow">Connexion</p>
          <h1>Connectez-vous depuis l'interface.</h1>
          <p>Pour protéger les comptes clients, la connexion ne se fait pas sur le serveur OAuth public.</p>
          <p><a class="button primary" href="{escape(frontend_url())}">Aller à mon espace</a></p>
        </div>
        """,
    )


def render_register() -> str:
    return page(
        "Créer un espace client",
        f"""
        <div class="panel">
          <p class="eyebrow">Inscription</p>
          <h1>Créez votre compte depuis l'interface.</h1>
          <p>L'inscription et les mots de passe sont gérés par l'application client sécurisée, pas par ce serveur OAuth public.</p>
          <p><a class="button primary" href="{escape(frontend_url())}">Créer mon espace</a></p>
        </div>
        """,
    )


def render_auth_required() -> str:
    return page(
        "Espace sécurisé",
        f"""
        <div class="panel">
          <p class="eyebrow">Espace sécurisé</p>
          <h1>Retournez à votre espace client.</h1>
          <p>Cette page OAuth publique ne permet pas d'afficher un compte client directement. Connectez-vous depuis l'interface pour voir vos boîtes mail.</p>
          <p><a class="button primary" href="{escape(frontend_url().rstrip('/') + '/dashboard')}">Ouvrir mon espace</a></p>
        </div>
        """,
    )


def success_page(provider: str, client_id: str, account: str) -> str:
    return_url = f"{frontend_url().rstrip('/')}/dashboard"
    return page(
        f"Connexion {escape(provider)} réussie",
        f"""
        <div class="panel success">
          <h2>Le compte est connecté.</h2>
          <p><strong>{escape(provider)} / {escape(account)}</strong></p>
          <p>L'agent peut maintenant classer les nouveaux mails et préparer les brouillons.</p>
          <p><a class="button primary" href="{escape(return_url)}">Retour à mon espace</a></p>
        </div>
        """,
    )


def frontend_url() -> str:
    return os.getenv("FRONTEND_BASE_URL") or os.getenv("FRONTEND_PUBLIC_URL") or "http://localhost:3010"


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700;800&display=swap");

    :root {{
      color-scheme: light;
      --bg: #fbfaf8;
      --surface: #ffffff;
      --surface-tint: #f3f1ec;
      --text: #14141a;
      --muted: rgba(20, 20, 26, 0.62);
      --faint: rgba(20, 20, 26, 0.42);
      --line: rgba(15, 15, 20, 0.08);
      --line-strong: rgba(15, 15, 20, 0.15);
      --brand: #0d9488;
      --brand-deep: #0f766e;
      --brand-soft: rgba(13, 148, 136, 0.1);
      --ok: #16a34a;
      --ok-soft: rgba(22, 163, 74, 0.12);
      --pending: #b45309;
      --blue-soft: #eef4ff;
      --blue-text: #1d4ed8;
      --shadow: 0 30px 60px -34px rgba(20, 20, 26, 0.2);
      --font-display: "Fraunces", ui-serif, Georgia, serif;
      --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, sans-serif;
    }}

    * {{ box-sizing: border-box; }}
    ::selection {{ background: rgba(20, 20, 26, 0.16); color: var(--text); }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font-sans);
      background:
        radial-gradient(900px 460px at 100% 0%, rgba(13, 148, 136, 0.08), transparent 58%),
        radial-gradient(760px 420px at 0% 100%, rgba(244, 162, 97, 0.08), transparent 60%),
        var(--bg);
      color: var(--text);
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.02;
      mix-blend-mode: multiply;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    }}

    main {{
      position: relative;
      width: min(1120px, calc(100% - 32px));
      margin: 42px auto;
    }}

    a {{ color: inherit; text-decoration: none; }}

    h1 {{
      max-width: 17ch;
      margin: 0.45rem 0 1rem;
      font-family: var(--font-display);
      font-size: clamp(2.15rem, 4.6vw, 4.2rem);
      font-weight: 600;
      line-height: 1.04;
      letter-spacing: -0.03em;
    }}

    h2 {{
      margin: 2rem 0 1rem;
      font-family: var(--font-display);
      font-size: clamp(1.35rem, 1vw + 1rem, 1.8rem);
      font-weight: 600;
      letter-spacing: -0.02em;
    }}

    h3 {{
      margin: 0.8rem 0 0.25rem;
      font-family: var(--font-display);
      font-size: 1.35rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}

    p {{
      max-width: 58ch;
      color: var(--muted);
      line-height: 1.7;
    }}

    label {{
      display: block;
      margin: 1rem 0 0.45rem;
      color: var(--faint);
      font-size: 0.85rem;
      font-weight: 600;
    }}

    input {{
      width: 100%;
      min-height: 52px;
      padding: 0.9rem 1rem;
      border: 1px solid var(--line-strong);
      border-radius: 14px;
      background: var(--surface-tint);
      color: var(--text);
      font-size: 0.98rem;
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    }}

    input:focus {{
      border-color: var(--brand);
      background: var(--surface);
      box-shadow: 0 0 0 4px var(--brand-soft);
    }}

    .hero {{
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 32px;
      padding: clamp(2rem, 4vw, 3.2rem);
      margin-bottom: 1.6rem;
      background:
        radial-gradient(120% 120% at 100% 0%, rgba(13, 148, 136, 0.1), transparent 55%),
        radial-gradient(100% 100% at 0% 100%, rgba(244, 162, 97, 0.08), transparent 55%),
        rgba(255, 255, 255, 0.88);
      box-shadow: var(--shadow);
    }}

    .hero.compact h1 {{ font-size: clamp(2rem, 3vw, 2.8rem); }}

    .eyebrow {{
      margin: 0;
      color: var(--brand-deep);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}

    .actions {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-top: 1.55rem;
    }}

    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 0.85rem 1.25rem;
      border: 1px solid var(--line-strong);
      border-radius: 14px;
      background: var(--surface);
      color: var(--text);
      font-size: 0.94rem;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.1s ease, background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }}

    .button:hover {{
      background: var(--surface-tint);
      border-color: rgba(15, 15, 20, 0.24);
    }}

    .button:active {{ transform: translateY(1px); }}

    .button.primary {{
      color: #ffffff;
      background: var(--brand);
      border-color: var(--brand);
      box-shadow: 0 12px 28px -14px rgba(13, 148, 136, 0.62);
    }}

    .button.primary:hover {{
      background: var(--brand-deep);
      border-color: var(--brand-deep);
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }}

    .card,
    .panel {{
      display: block;
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 1.5rem;
      box-shadow: 0 16px 42px -34px rgba(20, 20, 26, 0.28);
    }}

    .panel {{
      width: min(680px, 100%);
      margin-inline: auto;
      padding: clamp(2rem, 4vw, 3rem);
    }}

    .panel.success {{
      width: min(760px, 100%);
      border-color: rgba(22, 163, 74, 0.28);
      box-shadow: 0 28px 70px -44px rgba(22, 163, 74, 0.42);
    }}

    .card.disabled {{ opacity: 0.62; }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: var(--brand-soft);
      color: var(--brand-deep);
      border-radius: 999px;
      padding: 0.42rem 0.72rem;
      font-size: 0.76rem;
      font-weight: 800;
    }}

    .muted {{
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .account-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 1rem 0;
      border-top: 1px solid var(--line);
    }}

    .status {{
      display: block;
      margin-top: 0.3rem;
      font-size: 0.82rem;
      font-weight: 800;
    }}

    .status.ok {{ color: var(--ok); }}
    .status.pending {{ color: var(--pending); }}

    @media (max-width: 640px) {{
      main {{ width: min(100% - 20px, 1120px); margin: 20px auto; }}
      .hero, .panel, .card {{ border-radius: 22px; padding: 1.35rem; }}
      .account-row {{ align-items: flex-start; flex-direction: column; }}
      .button {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <main>{body}</main>
</body>
</html>"""


def escape(value: str) -> str:
    value = "" if value is None else str(value)
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
