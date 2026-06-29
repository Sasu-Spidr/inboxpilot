"""Encrypted local processing state for idempotent email handling."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from token_store import TokenStore


class ProcessedState:
    """Small encrypted state file used to avoid processing one email twice.

    The state is intentionally file-based to keep the project lightweight and
    VPS-friendly. Records are keyed by client + connector + account + message id.
    """

    def __init__(self, filename: str, token_store: TokenStore):
        self.filename = filename
        self.store = token_store
        self.records: dict[str, dict[str, Any]] = {}
        self.reload()

    @staticmethod
    def key(client_id: str, connector: str, account: str, message_id: str) -> str:
        return f"{client_id}:{connector}:{account}:{message_id}"

    def reload(self) -> None:
        data = self.store.load(self.filename)
        self.records = data.get("records", {}) if data else {}

    def save(self) -> None:
        self.store.save(self.filename, {"records": self.records})

    def is_processed(self, client_id: str, connector: str, account: str, message_id: str) -> bool:
        return self.key(client_id, connector, account, message_id) in self.records

    def get(self, client_id: str, connector: str, account: str, message_id: str) -> dict[str, Any] | None:
        return self.records.get(self.key(client_id, connector, account, message_id))

    def begin(
        self,
        *,
        client_id: str,
        connector: str,
        account: str,
        message_id: str,
        thread_id: str | None,
        label: str,
        action: str,
        draft_created: bool = False,
    ) -> None:
        self.records[self.key(client_id, connector, account, message_id)] = {
            "connector": connector,
            "account": account,
            "message_id": message_id,
            "thread_id": thread_id,
            "label": label,
            "action": action,
            "draft_created": draft_created,
            "processed_at": now_iso(),
            "status": "in_progress",
        }
        self.save()

    def complete(
        self,
        *,
        client_id: str,
        connector: str,
        account: str,
        message_id: str,
        thread_id: str | None,
        label: str,
        action: str,
        draft_created: bool,
    ) -> None:
        self.records[self.key(client_id, connector, account, message_id)] = {
            "connector": connector,
            "account": account,
            "message_id": message_id,
            "thread_id": thread_id,
            "label": label,
            "action": action,
            "draft_created": draft_created,
            "processed_at": now_iso(),
            "status": "completed",
        }
        self.save()

    def remove(self, client_id: str, connector: str, account: str, message_id: str) -> None:
        self.records.pop(self.key(client_id, connector, account, message_id), None)
        self.save()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
