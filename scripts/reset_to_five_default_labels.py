from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from client_settings import DEFAULT_LABELS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("DATA_DIR", "./data"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings_dir = Path(args.data_dir) / "client-settings"
    files = sorted(settings_dir.glob("*.json"))
    changed = 0

    for file in files:
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            payload = {}
        previous = payload.get("labels", [])
        payload["labels"] = [dict(label) for label in DEFAULT_LABELS]
        payload["updatedAt"] = datetime.now(UTC).isoformat()
        payload["labelPreset"] = "five-default-v1"
        if previous != payload["labels"]:
            changed += 1
            if not args.dry_run:
                file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{file.name}: {'would reset' if args.dry_run else 'reset'}")

    print(f"clients={len(files)} changed={changed}")


if __name__ == "__main__":
    main()
