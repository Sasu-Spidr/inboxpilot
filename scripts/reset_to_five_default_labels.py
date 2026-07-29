from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from client_registry import load_registered_clients
from client_settings import DEFAULT_LABELS
from main import load_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("DATA_DIR", "./data"))
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings_dir = Path(args.data_dir) / "client-settings"
    registered_clients = sorted(load_registered_clients(load_settings(args.config)).keys())
    file_clients = sorted(path.stem for path in settings_dir.glob("*.json"))
    clients = sorted(set(registered_clients) | set(file_clients))
    changed = 0

    for client_id in clients:
        file = settings_dir / f"{client_id}.json"
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
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{file.name}: {'would reset' if args.dry_run else 'reset'}")

    print(f"clients={len(clients)} changed={changed}")


if __name__ == "__main__":
    main()
