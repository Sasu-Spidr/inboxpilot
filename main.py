from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from activity_store import record_email_activity
from client_settings import active_label_keys_for_client, action_for_client, label_color_for_client, label_color_settings_for_client, label_name_for_client, label_settings_for_classifier, managed_label_names_for_client, mark_as_read_for_client, unread_delete_after_days_for_client
from client_registry import merge_registered_clients, update_registered_account
from classifier import EmailClassifier
from draft_generator import DraftGenerator
from gmail_connector import GmailConnector
from hotmail_connector import HotmailConnector
from json_logging import configure_logging
from rules_engine import RulesEngine
from state_store import ProcessedState
from token_store import TokenStore

LOG = logging.getLogger("spidr_mail")


def load_settings(path: str = "config/settings.yaml") -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    return merge_registered_clients(yaml.safe_load(os.path.expandvars(raw)))


def filter_settings(settings: dict, client: str | None = None, connector: str | None = None, account: str | None = None) -> dict:
    if not any((client, connector, account)):
        return settings
    clients = settings.get("clients", {})
    for client_id, client_cfg in clients.items():
        client_cfg["enabled"] = client_id == client if client else bool(client_cfg.get("enabled", True))
        for connector_name, connector_cfg in client_cfg.get("connectors", {}).items():
            connector_cfg["enabled"] = connector_name == connector if connector else bool(connector_cfg.get("enabled", False))
            for account_cfg in connector_cfg.get("accounts", []):
                account_name = account_cfg.get("account") or account_cfg.get("id") or connector_name
                account_cfg["enabled"] = account_name == account if account else bool(account_cfg.get("enabled", True))
    return settings


class MailWorker:
    def __init__(self, settings, connectors=None, classifier=None, drafts=None, rules=None, state=None):
        self.settings = settings
        self._connectors_injected = connectors is not None
        self.labels = yaml.safe_load(Path("config/labels.yaml").read_text(encoding="utf-8"))
        self.rules = rules or RulesEngine("config/rules.yaml")
        self.classifier = classifier or EmailClassifier(settings["groq_api_key"], settings.get("groq_model", "qwen/qwen3-32b"))
        self.drafts = drafts or DraftGenerator(settings["groq_api_key"], settings.get("groq_model", "qwen/qwen3-32b"))
        self.connectors = connectors if connectors is not None else self._build_connectors()
        self.state = state or ProcessedState(settings.get("state_file", "./data/state/processed_messages.enc"), TokenStore(settings["token_encryption_key"]))

    def _build_connectors(self) -> dict[str, dict[str, dict[str, Any]]]:
        store = TokenStore(self.settings["token_encryption_key"])
        built: dict[str, dict[str, dict[str, Any]]] = {}
        for client_id, client_cfg in self._clients().items():
            if not client_cfg.get("enabled", True):
                continue
            built[client_id] = {}
            for connector_name, connector_cfg in client_cfg.get("connectors", {}).items():
                accounts = normalize_accounts(connector_name, connector_cfg)
                for account_cfg in accounts:
                    if not account_cfg.get("enabled", True):
                        continue
                    token_file = account_cfg.get("token_file")
                    if token_file and not Path(token_file).exists():
                        LOG.info("Connector skipped because token is missing: client=%s connector=%s account=%s", client_id, connector_name, account_cfg.get("account") or account_cfg.get("id") or connector_name)
                        continue
                    account = account_cfg.get("account") or account_cfg.get("id") or connector_name
                    connected_at = account_cfg.get("connected_at") or current_utc_iso()
                    if not account_cfg.get("connected_at"):
                        account_cfg["connected_at"] = connected_at
                        update_registered_account(self.settings, client_id, connector_name, account, {"connected_at": connected_at})
                        LOG.info("Connector activation timestamp initialized: client=%s connector=%s account=%s", client_id, connector_name, account)
                    key = f"{connector_name}:{account}"
                    if connector_name == "gmail":
                        connector = GmailConnector(account_cfg["credentials_file"], account_cfg["token_file"], store)
                    elif connector_name == "hotmail":
                        client_id_value = account_cfg.get("client_id") or os.getenv(account_cfg.get("client_id_env", "MICROSOFT_CLIENT_ID"), "")
                        if not client_id_value:
                            LOG.warning("Hotmail connector skipped because Microsoft client id is missing: client=%s account=%s", client_id, account)
                            continue
                        client_secret = account_cfg.get("client_secret") or os.getenv(account_cfg.get("client_secret_env", "MICROSOFT_CLIENT_SECRET"), "")
                        connector = HotmailConnector(client_id_value, account_cfg.get("tenant_id", "consumers"), account_cfg["token_file"], store, client_secret=client_secret)
                    else:
                        LOG.warning("Unknown connector ignored: %s", connector_name)
                        continue
                    sender_name = account_cfg.get("sender_name") or client_cfg.get("sender_name") or client_cfg.get("owner_name") or ""
                    built[client_id][key] = {
                        "name": connector_name,
                        "account": account,
                        "connector": connector,
                        "sender_name": sender_name,
                        "connected_at": connected_at,
                    }
        return built

    def _clients(self) -> dict:
        if "clients" in self.settings:
            return self.settings["clients"] or {}
        return {"default": {"enabled": True, "connectors": self.settings.get("connectors", {})}}

    def reload_dynamic_clients(self) -> None:
        if self._connectors_injected:
            return
        self.settings = merge_registered_clients(self.settings)
        self.connectors = self._build_connectors()

    def run_cycle(self) -> None:
        self.reload_dynamic_clients()
        self.rules.reload()
        for client_id, entries in self.connectors.items():
            for entry in entries.values():
                self._poll_account(client_id, entry["name"], entry["account"], entry["connector"])

    def _poll_account(self, client_id: str, connector_name: str, account: str, connector) -> None:
        try:
            self._sync_account_settings(client_id, connector_name, account, connector)
            emails = connector.unread_emails(self.settings["max_emails_per_cycle"])
        except Exception as exc:
            log_event("polling_failed", logging.ERROR, client_id=client_id, connector=connector_name, account=account, status="failed", error=str(exc), exc_info=True)
            return
        for email in emails:
            self.process_email(client_id, connector_name, account, email["id"], email=email)

    def _sync_account_settings(self, client_id: str, connector_name: str, account: str, connector) -> None:
        if connector_name not in {"gmail", "hotmail"} or not hasattr(connector, "sync_label_color"):
            return
        connector_labels = self.labels.get(connector_name, {})
        for setting in label_color_settings_for_client(client_id):
            label_name = setting["name"] or connector_labels.get(setting["key"], setting["key"])
            try:
                connector.sync_label_color(label_name, setting["color"])
            except Exception as exc:
                log_event("label_color_sync_failed", logging.WARNING, client_id=client_id, connector=connector_name, account=account, label=setting["key"], status="warning", error=str(exc))

    def process_email(self, client_id: str, connector_name: str, account: str, message_id: str, email: dict | None = None) -> bool:
        """Process one email.

        This method is the future webhook entrypoint: webhook handlers can call
        it with only the ids, while polling passes the already fetched email.
        """
        entry = self._entry(client_id, connector_name, account)
        connector = entry["connector"]
        if self.state.is_processed(client_id, connector_name, account, message_id):
            record = self.state.get(client_id, connector_name, account, message_id) or {}
            email = email or connector.get_email(message_id)
            if self._delete_processed_unread_if_expired(connector, client_id, connector_name, account, message_id, email, record):
                return True
            log_event("email_already_processed", client_id=client_id, connector=connector_name, account=account, message_id=message_id, status="skipped")
            return False
        try:
            email = email or connector.get_email(message_id)
            log_event("email_detected", client_id=client_id, connector=connector_name, account=account, message_id=message_id, status="started")
            if is_before_activation(email, entry.get("connected_at")):
                self.state.complete(
                    client_id=client_id,
                    connector=connector_name,
                    account=account,
                    message_id=message_id,
                    thread_id=email.get("thread_id"),
                    label="pre_activation",
                    action="skip",
                    draft_created=False,
                    received_at=email.get("received_at"),
                )
                log_event("email_skipped_before_activation", client_id=client_id, connector=connector_name, account=account, message_id=message_id, status="skipped")
                return False
            client_label_settings = label_settings_for_classifier(client_id)
            result = self.classifier.safe_classify(email["subject"], email["sender"], email["body"], client_label_settings or None)
            original_label = result["label"]
            label = normalize_active_label(client_id, original_label)
            if label != original_label:
                result["action"] = "keep"
            action = self.rules.action_for(label, result["action"])
            action = action_for_client(client_id, label, action)
            if action != "trash" and unread_delete_due(client_id, label, email):
                action = "trash"
            if action == "trash" and not auto_delete_allowed(result, email):
                if unread_delete_due(client_id, label, email):
                    log_event("unread_expired_delete_allowed", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action="trash", status="ok")
                else:
                    log_event("auto_delete_guarded", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action="keep", status="guarded")
                    action = "keep"
            priority = result.get("priority", "medium")
            target = self.rules.target_for(label)
            log_event("email_classified", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")

            self.state.begin(client_id=client_id, connector=connector_name, account=account, message_id=message_id, thread_id=email.get("thread_id"), label=label, action=action, draft_created=False, received_at=email.get("received_at"))
            self._apply_label(connector, connector_name, message_id, label, client_id, account, action, priority)
            draft_created = self._apply_action(connector, connector_name, account, email, label, action, priority, target, client_id, entry.get("sender_name", ""))
            if action != "trash" and mark_as_read_for_client(client_id, label):
                connector.mark_read(message_id)
                log_event("email_marked_read", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
            self.state.complete(client_id=client_id, connector=connector_name, account=account, message_id=message_id, thread_id=email.get("thread_id"), label=label, action=action, draft_created=draft_created, received_at=email.get("received_at"))
            record_email_activity(client_id=client_id, connector=connector_name, account=account, email=email, label=label, action=action, draft_created=draft_created)
            return True
        except Exception as exc:
            self.state.remove(client_id, connector_name, account, message_id)
            log_event("processing_failed", logging.ERROR, client_id=client_id, connector=connector_name, account=account, message_id=message_id, status="failed", error=str(exc), exc_info=True)
            return False

    def _delete_processed_unread_if_expired(self, connector, client_id: str, connector_name: str, account: str, message_id: str, email: dict, record: dict) -> bool:
        label = str(record.get("label") or "")
        if not label or not unread_delete_due(client_id, label, email):
            return False
        connector.trash(message_id)
        self.state.complete(
            client_id=client_id,
            connector=connector_name,
            account=account,
            message_id=message_id,
            thread_id=email.get("thread_id") or record.get("thread_id"),
            label=label,
            action="trash_unread_expired",
            draft_created=bool(record.get("draft_created")),
            received_at=email.get("received_at") or record.get("received_at"),
        )
        record_email_activity(client_id=client_id, connector=connector_name, account=account, email=email, label=label, action="trash_unread_expired", draft_created=bool(record.get("draft_created")))
        log_event("unread_expired_deleted", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action="trash_unread_expired", status="ok")
        return True

    def _entry(self, client_id: str, connector_name: str, account: str) -> dict:
        key = f"{connector_name}:{account}"
        return self.connectors[client_id][key]

    def _apply_label(self, connector, connector_name: str, message_id: str, label: str, client_id: str, account: str, action: str, priority: str) -> None:
        connector_labels = self.labels.get(connector_name, {})
        label_name = label_name_for_client(client_id, label, connector_labels.get(label, label))
        managed_labels = list(dict.fromkeys([*connector_labels.values(), *managed_label_names_for_client(client_id)]))
        if hasattr(connector, "replace_label"):
            connector.replace_label(message_id, label_name, managed_labels)
        else:
            connector.apply_label(message_id, label_name)
        if connector_name in {"gmail", "hotmail"} and hasattr(connector, "sync_label_color"):
            label_color = label_color_for_client(client_id, label)
            if label_color:
                try:
                    connector.sync_label_color(label_name, label_color)
                except Exception as exc:
                    log_event("label_color_sync_failed", logging.WARNING, client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, status="warning", error=str(exc))
        log_event("label_applied", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")

    def _apply_action(self, connector, connector_name: str, account: str, email: dict, label: str, action: str, priority: str, target: str | None, client_id: str, sender_name: str = "") -> bool:
        message_id = email["id"]
        if action == "trash":
            connector.trash(message_id)
            log_event("email_trashed", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
        elif action == "draft":
            if hasattr(self.drafts, "safe_generate"):
                draft = self.drafts.safe_generate(email["subject"], email["sender"], email["body"], signature_name=sender_name)
            else:
                draft = self.drafts.generate(email["subject"], email["sender"], email["body"], signature_name=sender_name)
            connector.create_draft(email, draft)
            log_event("draft_created", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
            return True
        elif action == "archive":
            connector.archive(message_id)
            log_event("email_archived", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
        elif action == "mark_read":
            log_event("email_left_unread", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
        elif action == "move":
            if not target:
                raise ValueError(f"Rule for label {label} uses move but has no target")
            connector.move(message_id, target)
            log_event("email_moved", client_id=client_id, connector=connector_name, account=account, message_id=message_id, label=label, action=action, priority=priority, status="ok")
        return False

    def authenticate(self) -> None:
        for client_id, entries in self.connectors.items():
            for entry in entries.values():
                log_event("authenticating", client_id=client_id, connector=entry["name"], account=entry["account"], status="started")
                entry["connector"].authenticate()
                log_event("authenticated", client_id=client_id, connector=entry["name"], account=entry["account"], status="ok")

    def run_forever(self) -> None:
        while True:
            try:
                self.run_cycle()
            except Exception:
                LOG.exception("Cycle failed")
            time.sleep(self.settings["polling_interval_seconds"])


def normalize_accounts(connector_name: str, connector_cfg: dict) -> list[dict]:
    if not connector_cfg or not connector_cfg.get("enabled", False):
        return []
    if "accounts" in connector_cfg:
        return connector_cfg["accounts"] or []
    account_cfg = dict(connector_cfg)
    account_cfg.setdefault("account", connector_name)
    return [account_cfg]


def normalize_active_label(client_id: str, label: str) -> str:
    active_keys = active_label_keys_for_client(client_id)
    if not active_keys or label in active_keys:
        return label
    if "À lire" in active_keys:
        return "À lire"
    return active_keys[0]


def auto_delete_allowed(result: dict, email: dict) -> bool:
    try:
        confidence = float(result.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence < 0.85:
        return False
    text = f"{email.get('subject', '')}\n{email.get('sender', '')}\n{email.get('body', '')}".lower()
    return any(
        signal in text
        for signal in (
            "unsubscribe",
            "désabonner",
            "desabonner",
            "newsletter",
            "marketing",
            "promotion",
            "offre commerciale",
            "se désinscrire",
            "se desinscrire",
        )
    )


def unread_delete_due(client_id: str, label: str, email: dict, now: datetime | None = None) -> bool:
    days = unread_delete_after_days_for_client(client_id, label)
    if not days:
        return False
    received_at = email.get("received_at")
    if not received_at:
        return False
    try:
        received = parse_datetime_or_timestamp(received_at)
    except (TypeError, ValueError):
        return False
    current = now or datetime.now(timezone.utc)
    return received + timedelta(days=days) <= current


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    exc_info = fields.pop("exc_info", None)
    LOG.log(level, event, extra={"event": event, **fields}, exc_info=exc_info)


def is_before_activation(email: dict, connected_at: str | None) -> bool:
    if not connected_at:
        return False
    received_at = email.get("received_at")
    if not received_at:
        return False
    try:
        connected = parse_datetime_or_timestamp(connected_at)
        received = parse_datetime_or_timestamp(received_at)
    except (TypeError, ValueError):
        return False
    return received < connected


def parse_datetime_or_timestamp(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        timestamp = int(text)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, timezone.utc)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--authenticate", action="store_true", help="Connect enabled accounts without processing messages")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--client", help="Only process/authenticate one configured client id")
    parser.add_argument("--connector", choices=["gmail", "hotmail"], help="Only process/authenticate one connector")
    parser.add_argument("--account", help="Only process/authenticate one account name")
    args = parser.parse_args()
    settings = filter_settings(load_settings(args.config), args.client, args.connector, args.account)
    configure_logging(settings.get("log_level", "INFO"), settings.get("json_logs", True))
    worker = MailWorker(settings)
    if args.authenticate:
        worker.authenticate()
        log_event("authentication_completed", status="ok")
    elif args.once:
        worker.run_cycle()
    else:
        worker.run_forever()


if __name__ == "__main__":
    main()
