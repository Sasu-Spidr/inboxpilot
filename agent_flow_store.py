from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FLOW_EVENTS = {
    "email_detected",
    "email_skipped_before_activation",
    "email_classified",
    "label_applied",
    "draft_created",
    "email_trashed",
    "email_archived",
    "email_left_unread",
    "email_moved",
    "unread_expired_deleted",
    "processed_email_label_reconciled",
    "email_already_processed",
    "processing_failed",
    "polling_failed",
    "label_color_sync_failed",
}


def flow_log_file() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    return data_dir / "agent-flow" / "events.jsonl"


def record_agent_flow(event: str, fields: dict[str, Any]) -> None:
    if event not in FLOW_EVENTS:
        return
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": safe_text(fields.get("client_id")),
        "connector": safe_text(fields.get("connector")),
        "account": safe_text(fields.get("account")),
        "message_id": safe_text(fields.get("message_id")),
        "subject": safe_text(fields.get("subject")),
        "sender": safe_text(fields.get("sender")),
        "label": safe_text(fields.get("label")),
        "action": safe_text(fields.get("action")),
        "priority": safe_text(fields.get("priority")),
        "status": safe_text(fields.get("status")),
        "error": safe_text(fields.get("error"), limit=500),
    }
    path = flow_log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def safe_text(value: Any, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]
