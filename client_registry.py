from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


DEFAULT_REGISTRY_FILE = "./data/clients/clients.yaml"


def registry_file(settings: dict) -> str:
    onboarding = settings.get("onboarding", {}) or {}
    return os.path.expandvars(onboarding.get("registry_file", DEFAULT_REGISTRY_FILE))


def merge_registered_clients(settings: dict) -> dict:
    """Merge registered clients into settings.

    Dynamic clients are refreshed from disk every time this function is called.
    This lets the frontend add new mail accounts while the worker is already
    running; the next polling cycle sees the updated account list.
    """
    path = Path(registry_file(settings))
    if not path.exists():
        return settings
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dynamic_clients = data.get("clients", {}) or {}
    settings.setdefault("clients", {})
    for client_id, client_cfg in dynamic_clients.items():
        settings["clients"][client_id] = client_cfg
    return settings


def load_registered_clients(settings: dict) -> dict[str, Any]:
    path = Path(registry_file(settings))
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("clients", {}) or {}


def save_registered_client(settings: dict, client_id: str, client_cfg: dict) -> None:
    path = Path(registry_file(settings))
    path.parent.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    data.setdefault("clients", {})
    data["clients"][client_id] = client_cfg
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def update_registered_account(settings: dict, client_id: str, connector: str, account: str, fields: dict) -> None:
    path = Path(registry_file(settings))
    if not path.exists():
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    account_rows = (
        data.get("clients", {})
        .get(client_id, {})
        .get("connectors", {})
        .get(connector, {})
        .get("accounts", [])
    )
    for account_cfg in account_rows:
        account_name = account_cfg.get("account") or account_cfg.get("id") or connector
        if account_name == account:
            account_cfg.update({key: value for key, value in fields.items() if value})
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            return


def make_client_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")
    return slug or "client"


def build_registered_client(settings: dict, client_id: str, owner_name: str, email: str = "") -> dict:
    onboarding = settings.get("onboarding", {}) or {}
    gmail_credentials_file = os.path.expandvars(
        os.getenv("GMAIL_OAUTH_CLIENT_FILE") or onboarding.get("gmail_credentials_file", "./secrets/google-oauth-client.json")
    )
    microsoft_client_id_env = onboarding.get("microsoft_client_id_env", "MICROSOFT_CLIENT_ID")
    microsoft_client_secret_env = onboarding.get("microsoft_client_secret_env", "MICROSOFT_CLIENT_SECRET")
    return {
        "enabled": True,
        "owner_name": owner_name,
        "email": email,
        "connectors": {
            "gmail": {
                "enabled": True,
                "accounts": [
                    {
                        "account": "main",
                        "sender_name": owner_name,
                        "credentials_file": gmail_credentials_file,
                        "token_file": f"./data/tokens/{client_id}-gmail-main.token.enc",
                        "connected_at": "",
                    }
                ],
            },
            "hotmail": {
                "enabled": True,
                "accounts": [
                    {
                        "account": "main",
                        "sender_name": owner_name,
                        "client_id_env": microsoft_client_id_env,
                        "client_secret_env": microsoft_client_secret_env,
                        "tenant_id": "consumers",
                        "token_file": f"./data/tokens/{client_id}-hotmail-main.token.enc",
                        "connected_at": "",
                    }
                ],
            },
        },
    }
