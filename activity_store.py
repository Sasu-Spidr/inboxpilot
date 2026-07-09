from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def activity_file() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    return data_dir / "activity" / "events.jsonl"


def record_email_activity(
    *,
    client_id: str,
    connector: str,
    account: str,
    email: dict[str, Any],
    label: str,
    action: str,
    draft_created: bool,
) -> None:
    event = {
        "client_id": client_id,
        "connector": connector,
        "account": account,
        "message_id": str(email.get("id", "")),
        "thread_id": email.get("thread_id"),
        "subject": str(email.get("subject", "")).strip()[:180],
        "sender": str(email.get("sender", "")).strip()[:180],
        "label": label,
        "action": action,
        "draft_created": bool(draft_created),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    path = activity_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
