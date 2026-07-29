from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    settings_dir = Path(os.getenv("DATA_DIR", "./data")) / "client-settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    clients_updated = 0
    flags_cleared = 0
    unread_delete_delays_cleared = 0

    for path in sorted(settings_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        labels = payload.get("labels")
        if not isinstance(labels, list):
            continue

        changed = False
        for label in labels:
            if isinstance(label, dict) and label.get("markAsRead") is True:
                label["markAsRead"] = False
                flags_cleared += 1
                changed = True
            if isinstance(label, dict) and label.get("autoDeleteUnreadAfterDays"):
                label["autoDeleteUnreadAfterDays"] = None
                unread_delete_delays_cleared += 1
                changed = True

        if not changed:
            continue

        payload["safeUnreadDefaultsResetAt"] = datetime.now(UTC).isoformat()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        clients_updated += 1

    print(f"clients_updated={clients_updated} mark_as_read_flags_cleared={flags_cleared} unread_delete_delays_cleared={unread_delete_delays_cleared}")


if __name__ == "__main__":
    main()
