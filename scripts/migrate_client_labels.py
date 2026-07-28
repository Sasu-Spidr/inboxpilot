from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from client_settings import DEFAULT_LABELS


def main() -> None:
    settings_dir = Path(os.getenv("DATA_DIR", "./data")) / "client-settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    migrated = 0
    added = 0

    for path in sorted(settings_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        labels = payload.get("labels")
        if not isinstance(labels, list):
            labels = []

        next_labels, added_count = with_missing_defaults(labels)
        if added_count == 0:
            continue

        payload["labels"] = next_labels
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        migrated += 1
        added += added_count

    print(f"clients_migrated={migrated} labels_added={added}")


def with_missing_defaults(labels: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    next_labels = list(labels)
    present = {
        value
        for label in next_labels
        for value in (str(label.get("key", "")).strip(), str(label.get("name", "")).strip())
        if value
    }
    added = 0
    for default_label in DEFAULT_LABELS:
        key = str(default_label.get("key", "")).strip()
        name = str(default_label.get("name", "")).strip()
        if key in present or name in present:
            continue
        next_labels.append(dict(default_label))
        present.add(key)
        present.add(name)
        added += 1
    return next_labels, added


if __name__ == "__main__":
    main()
