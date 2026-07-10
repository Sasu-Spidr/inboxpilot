from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import msal
import requests
import yaml
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

from client_settings import label_color_settings_for_client
from client_registry import merge_registered_clients, update_registered_account
from gmail_connector import GmailConnector, SCOPES as GMAIL_SCOPES, json_credentials
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
                    raw_body = self.rfile.read(length)
                    if parsed.path == "/internal/sync-label-settings":
                        if self.headers.get("X-Internal-Sync-Key") != server.settings["token_encryption_key"]:
                            self._json(403, {"error": "forbidden"})
                            return
                        payload = json.loads(raw_body.decode("utf-8") or "{}")
                        result = server.sync_label_settings(
                            one({"client": [payload.get("client", "")]}, "client"),
                            payload.get("removed_labels", []),
                        )
                        self._json(200, result)
                        return
                    self._html(
                        405,
                        page(
                            "Authentification désactivée ici",
                            f"""
                            <div class="panel">
                              <p class="eyebrow">InboxPilot</p>
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

            def _json(self, status: int, payload: dict):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler

    def sync_label_settings(self, client_id: str, removed_labels: list[str] | None = None) -> dict:
        self.settings = merge_registered_clients(self.settings)
        client = self.settings.get("clients", {}).get(client_id)
        if not client:
            raise ValueError(f"Client inconnu : {client_id}")

        synced = 0
        deleted = 0
        skipped = 0
        errors = []
        labels = label_color_settings_for_client(client_id)
        removed = [str(label).strip() for label in (removed_labels or []) if str(label).strip()]
        accounts = client.get("connectors", {}).get("gmail", {}).get("accounts", []) or []
        for account_cfg in accounts:
            token_file = account_cfg.get("token_file", "")
            if not token_file or not Path(token_file).exists():
                skipped += 1
                continue
            try:
                connector = GmailConnector(account_cfg["credentials_file"], token_file, self.store)
                for label_name in removed:
                    if connector.delete_label(label_name):
                        deleted += 1
                for label in labels:
                    connector.sync_label_color(label["name"], label["color"])
                    synced += 1
            except Exception as exc:
                errors.append({"account": account_cfg.get("account", "main"), "error": str(exc)})
        result = {"synced": synced, "deleted": deleted, "removed_requested": len(removed), "skipped": skipped, "errors": errors}
        LOG.info(
            "Gmail label settings synced client=%s synced=%s deleted=%s removed_requested=%s skipped=%s errors=%s",
            client_id,
            synced,
            deleted,
            len(removed),
            skipped,
            len(errors),
        )
        return result

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
        email = gmail_profile_email(flow.credentials)
        update_registered_account(self.settings, state["client"], "gmail", state["account"], {"email_address": email, "connected_at": now_iso()})
        self.settings = merge_registered_clients(self.settings)
        return success_page("Gmail", state["client"], state["account"], email)

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
        email = microsoft_profile_email(result["access_token"])
        update_registered_account(self.settings, state["client"], "hotmail", state["account"], {"email_address": email, "connected_at": now_iso()})
        self.settings = merge_registered_clients(self.settings)
        return success_page("Hotmail / Outlook", state["client"], state["account"], email)

    def _account(self, query: str, connector: str) -> tuple[str, str, dict]:
        self.settings = merge_registered_clients(self.settings)
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
    client_secret = account_cfg.get("client_secret") or os.getenv(account_cfg.get("client_secret_env", "MICROSOFT_CLIENT_SECRET"), "")
    authority = f"https://login.microsoftonline.com/{account_cfg.get('tenant_id', 'consumers')}"
    if client_secret:
        return msal.ConfidentialClientApplication(client_id, client_credential=client_secret, authority=authority, token_cache=cache)
        return msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)


def gmail_profile_email(credentials) -> str:
    try:
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        LOG.exception("Unable to read Gmail profile email")
        return ""


def microsoft_profile_email(access_token: str) -> str:
    try:
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"$select": "mail,userPrincipalName"},
            timeout=20,
        )
        response.raise_for_status()
        profile = response.json()
        return profile.get("mail") or profile.get("userPrincipalName") or ""
    except Exception:
        LOG.exception("Unable to read Microsoft profile email")
        return ""


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_home(settings: dict) -> str:
    return page(
        "Authentification InboxPilot",
        f"""
        <section class="hero">
          <p class="eyebrow">InboxPilot</p>
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


def provider_logo(provider_class: str) -> str:
    if provider_class == "outlook":
        return """
        <svg viewBox="0 0 64 64" role="img" aria-label="Logo Outlook" focusable="false">
          <rect x="24" y="12" width="30" height="38" rx="6" fill="#28a8ea"/>
          <path d="M24 18h27a5 5 0 0 1 5 5v2L39 37 24 27z" fill="#0078d4"/>
          <path d="M24 27l15 10 17-12v21a5 5 0 0 1-5 5H24z" fill="#50d9ff"/>
          <rect x="8" y="21" width="28" height="28" rx="6" fill="#0a5db3"/>
          <text x="22" y="40" text-anchor="middle" font-size="22" font-weight="800" fill="#fff" font-family="Arial, sans-serif">O</text>
        </svg>
        """
    return """
    <svg viewBox="0 0 64 64" role="img" aria-label="Logo Gmail" focusable="false">
      <rect x="8" y="14" width="48" height="36" rx="8" fill="#fff"/>
      <path d="M13 18l19 15 19-15v8L32 41 13 26z" fill="#ea4335"/>
      <path d="M8 22v22a6 6 0 0 0 6 6h7V32z" fill="#4285f4"/>
      <path d="M56 22v22a6 6 0 0 1-6 6h-7V32z" fill="#34a853"/>
      <path d="M43 32l13-10v-2a6 6 0 0 0-9.6-4.8L32 26z" fill="#fbbc04"/>
      <path d="M21 32L8 22v-2a6 6 0 0 1 9.6-4.8L32 26z" fill="#c5221f"/>
    </svg>
    """


def success_page(provider: str, client_id: str, account: str, email: str = "") -> str:
    return_url = f"{frontend_url().rstrip('/')}/dashboard"
    connected_identity = email or account
    provider_class = "outlook" if "outlook" in provider.lower() or "hotmail" in provider.lower() else "gmail"
    logo = provider_logo(provider_class)
    return page(
        f"Connexion {escape(provider)} réussie",
        f"""
        <section class="success-layout">
          <div class="success-card">
            <div class="success-glow"></div>
            <div class="success-topline">
              <span class="brand-mark">InboxPilot</span>
              <span class="success-badge">Connexion réussie</span>
            </div>
            <div class="success-icon {provider_class}" aria-hidden="true">
              {logo}
            </div>
            <h1>Votre boîte mail est connectée.</h1>
            <p class="success-lead">
              InboxPilot peut maintenant analyser les prochains emails non lus, appliquer vos libellés
              et préparer les brouillons selon vos paramètres.
            </p>
            <div class="connected-account">
              <span>Compte activé</span>
              <strong>{escape(provider)} · {escape(connected_identity)}</strong>
            </div>
            <div class="success-actions">
              <a class="button primary" href="{escape(return_url)}">Retour à mon espace</a>
              <span>Vous pouvez fermer cet onglet si votre espace est déjà ouvert.</span>
            </div>
          </div>
        </section>
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
      position: relative;
      overflow: hidden;
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
      transition: transform 0.16s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
    }}

    .button:hover {{
      background: var(--surface-tint);
      border-color: rgba(15, 15, 20, 0.24);
      transform: translateY(-2px);
    }}

    .button:active {{ transform: translateY(1px); }}

    .button.primary {{
      color: #ffffff;
      background: var(--brand);
      border-color: var(--brand);
      box-shadow: 0 12px 28px -14px rgba(13, 148, 136, 0.62);
    }}

    .button.primary::after {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.18) 38%, transparent 68%);
      transform: translateX(-130%);
      transition: transform 0.45s ease;
    }}

    .button.primary:hover {{
      background: var(--brand-deep);
      border-color: var(--brand-deep);
    }}

    .button.primary:hover::after {{
      transform: translateX(130%);
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

    .success-layout {{
      min-height: min(760px, calc(100vh - 84px));
      display: grid;
      place-items: center;
      padding: clamp(1rem, 3vw, 2rem) 0;
    }}

    .success-card {{
      position: relative;
      isolation: isolate;
      width: min(780px, 100%);
      overflow: hidden;
      padding: clamp(1.6rem, 4vw, 3rem);
      border: 1px solid rgba(53, 137, 233, 0.16);
      border-radius: 32px;
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.82)),
        radial-gradient(110% 120% at 100% 0%, rgba(53, 137, 233, 0.12), transparent 55%),
        radial-gradient(110% 120% at 0% 100%, rgba(13, 148, 136, 0.12), transparent 58%);
      box-shadow: 0 34px 90px -54px rgba(20, 20, 26, 0.34);
    }}

    .success-glow {{
      position: absolute;
      right: -120px;
      top: -120px;
      z-index: -1;
      width: 310px;
      height: 310px;
      border-radius: 999px;
      background: rgba(53, 137, 233, 0.16);
      filter: blur(10px);
    }}

    .success-topline {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: clamp(1.4rem, 3vw, 2.2rem);
    }}

    .brand-mark {{
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
      color: var(--text);
      font-size: 0.95rem;
      font-weight: 900;
      letter-spacing: -0.02em;
    }}

    .brand-mark::before {{
      content: "";
      width: 0.58rem;
      height: 0.58rem;
      border-radius: 999px;
      background: #0d9488;
      box-shadow: 0 0 0 5px rgba(13, 148, 136, 0.12);
    }}

    .success-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.48rem 0.78rem;
      border-radius: 999px;
      background: rgba(22, 163, 74, 0.1);
      color: #15803d;
      font-size: 0.78rem;
      font-weight: 900;
      white-space: nowrap;
    }}

    .success-icon {{
      display: grid;
      place-items: center;
      width: 68px;
      height: 68px;
      margin-bottom: 1.35rem;
      border: 1px solid rgba(15, 15, 20, 0.08);
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.88);
      box-shadow: 0 18px 38px -24px rgba(20, 20, 26, 0.5);
    }}

    .success-icon svg {{
      width: 52px;
      height: 52px;
      display: block;
    }}

    .success-icon.gmail {{
      box-shadow: 0 18px 38px -24px rgba(234, 67, 53, 0.55);
    }}

    .success-icon.outlook {{
      box-shadow: 0 18px 38px -24px rgba(0, 120, 212, 0.55);
    }}

    .success-card h1 {{
      max-width: 14ch;
      margin: 0 0 1rem;
      font-family: var(--font-display);
      font-size: clamp(2.1rem, 4vw, 4.2rem);
      line-height: 1.02;
      letter-spacing: -0.04em;
    }}

    .success-lead {{
      max-width: 620px;
      margin: 0;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.75;
    }}

    .connected-account {{
      display: grid;
      gap: 0.25rem;
      margin: 1.6rem 0 1.8rem;
      padding: 1rem 1.1rem;
      border: 1px solid rgba(15, 15, 20, 0.08);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
    }}

    .connected-account span {{
      color: var(--faint);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .connected-account strong {{
      overflow-wrap: anywhere;
      color: var(--text);
      font-size: 1rem;
    }}

    .success-actions {{
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }}

    .success-actions .button.primary {{
      background: #0d9488;
      border-color: #0d9488;
      box-shadow: 0 16px 34px -18px rgba(13, 148, 136, 0.72);
    }}

    .success-actions .button.primary:hover {{
      background: #0f766e;
      border-color: #0f766e;
      box-shadow: 0 18px 38px -18px rgba(13, 148, 136, 0.8);
    }}

    .success-actions span {{
      max-width: 320px;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.5;
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
      .success-card {{ border-radius: 24px; padding: 1.35rem; }}
      .success-topline {{ align-items: flex-start; flex-direction: column; }}
      .success-actions {{ align-items: stretch; flex-direction: column; }}
      .success-actions span {{ max-width: none; }}
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
