from __future__ import annotations

import json
import os
import re
from pathlib import Path


ENTITLED_STATUSES = {"active", "trialing", "past_due"}
MAILBOX_LIMITS = {"free": 1, "pro": 3, "business": 10}


class MailboxLimitError(ValueError):
    pass


def entitlement_for_client(client_id: str) -> dict[str, str]:
    try:
        payload = json.loads(_entitlement_path(client_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"tier": "free", "status": "active"}
    tier = str(payload.get("tier") or "free").strip().lower()
    status = str(payload.get("status") or "").strip().lower()
    if tier not in MAILBOX_LIMITS:
        tier = "free"
    return {"tier": tier, "status": status}


def effective_tier_for_client(client_id: str) -> str:
    entitlement = entitlement_for_client(client_id)
    tier = entitlement["tier"]
    if tier == "free":
        return "free"
    return tier if entitlement["status"] in ENTITLED_STATUSES else "free"


def mailbox_limit_for_client(client_id: str) -> int:
    return MAILBOX_LIMITS[effective_tier_for_client(client_id)]


def allows_automatic_actions(client_id: str) -> bool:
    return effective_tier_for_client(client_id) in {"pro", "business"}


def allows_advanced_rules(client_id: str) -> bool:
    return effective_tier_for_client(client_id) == "business"


def connected_mailbox_count(client_cfg: dict) -> int:
    count = 0
    for connector_cfg in (client_cfg.get("connectors") or {}).values():
        for account_cfg in (connector_cfg or {}).get("accounts", []) or []:
            token_file = str(account_cfg.get("token_file") or "")
            if token_file and _token_path(token_file).exists():
                count += 1
    return count


def ensure_mailbox_slot(client_id: str, client_cfg: dict, account_cfg: dict) -> None:
    token_file = str(account_cfg.get("token_file") or "")
    if token_file and _token_path(token_file).exists():
        return
    limit = mailbox_limit_for_client(client_id)
    if connected_mailbox_count(client_cfg) >= limit:
        tier = effective_tier_for_client(client_id).capitalize()
        raise MailboxLimitError(
            f"Votre offre {tier} autorise {limit} boîte(s) connectée(s). "
            "Passez à l'offre supérieure depuis votre espace InboxPilot pour en ajouter une autre."
        )


def _entitlement_path(client_id: str) -> Path:
    safe_client_id = re.sub(r"[^a-zA-Z0-9._-]", "-", str(client_id or ""))
    return Path(os.getenv("DATA_DIR", "./data")) / "entitlements" / f"{safe_client_id}.json"


def _token_path(token_file: str) -> Path:
    if token_file.startswith("./data/"):
        return Path(os.getenv("DATA_DIR", "./data")) / token_file.removeprefix("./data/")
    return Path(token_file)
