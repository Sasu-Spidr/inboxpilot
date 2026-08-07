from __future__ import annotations

import json
import os
from pathlib import Path

from client_settings import DEFAULT_LABELS, canonical_label_key


def main() -> None:
    settings_dir = Path(os.getenv("DATA_DIR", "./data")) / "client-settings"
    defaults = {label["key"]: label["description"] for label in DEFAULT_LABELS}
    updated_files = 0
    updated_labels = 0

    for path in sorted(settings_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue

        labels = payload.get("labels")
        if not isinstance(labels, list):
            continue

        changed = False
        for label in labels:
            if not isinstance(label, dict):
                continue
            key = canonical_label_key(str(label.get("key") or label.get("name") or ""))
            default_description = defaults.get(key)
            if not default_description:
                continue
            if label.get("description") != default_description:
                label["description"] = default_description
                changed = True
                updated_labels += 1

        if changed:
            payload["labels"] = labels
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            updated_files += 1

    print(f"files_updated={updated_files} labels_updated={updated_labels}")


if __name__ == "__main__":
    main()
