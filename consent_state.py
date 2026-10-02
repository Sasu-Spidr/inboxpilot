"""Fail-closed AI processing consent state shared with the frontend."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def ai_processing_consent_granted(client_id: str, data_dir: str | None = None) -> bool:
    safe_id = re.sub(r"[^a-zA-Z0-9._-]", "_", str(client_id))
    root = Path(data_dir or os.getenv("DATA_DIR", "./data"))
    try:
        payload = json.loads((root / "consents" / f"{safe_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    return payload.get("granted") is True and bool(payload.get("version")) and bool(payload.get("granted_at"))

