from __future__ import annotations

import json
import os
from pathlib import Path

from client_settings import normalized_labels_for_client


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

        next_labels = normalized_labels_for_client(path.stem)
        if labels == next_labels:
            continue

        payload["labels"] = next_labels
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        migrated += 1
        added += len(next_labels)

    print(f"clients_migrated={migrated} canonical_labels_written={added}")


if __name__ == "__main__":
    main()
