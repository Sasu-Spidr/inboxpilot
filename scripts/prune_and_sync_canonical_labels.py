from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from client_registry import load_registered_clients
from client_settings import CANONICAL_LABEL_KEYS, DEFAULT_LABELS, canonical_label_key, normalized_labels_for_client
from oauth_server import OAuthOnboardingServer, load_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--base-url", default="https://inboxpilot.mallow-hub.tech")
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--sync-mailboxes", action="store_true")
    args = parser.parse_args()

    os.environ["DATA_DIR"] = args.data_dir

    settings = load_settings(args.config)
    data_dir = Path(args.data_dir)
    settings_dir = data_dir / "client-settings"
    settings_clients = {path.stem for path in settings_dir.glob("*.json")}
    registry_clients = set(load_registered_clients(settings).keys())
    clients = sorted(settings_clients | registry_clients)
    default_names = {str(label["name"]) for label in DEFAULT_LABELS}

    server = OAuthOnboardingServer(settings, args.base_url) if args.sync_mailboxes else None
    results: dict[str, Any] = {}

    for client_id in clients:
        raw_labels = _read_raw_labels(settings_dir / f"{client_id}.json")
        removed_labels = _removed_label_names(raw_labels, default_names)
        normalized = normalized_labels_for_client(client_id)
        _write_settings(settings_dir / f"{client_id}.json", normalized)

        result: dict[str, Any] = {
            "labels_kept": [label["name"] for label in normalized],
            "removed_from_settings": removed_labels,
        }
        if server:
            result["mailbox_sync"] = server.sync_label_settings(client_id, removed_labels)
        results[client_id] = result
        print(f"{client_id}: {json.dumps(result, ensure_ascii=False)}")

    print(json.dumps(results, ensure_ascii=False, indent=2))


def _read_raw_labels(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    labels = payload.get("labels", [])
    return labels if isinstance(labels, list) else []


def _removed_label_names(labels: list[dict[str, Any]], default_names: set[str]) -> list[str]:
    removed: list[str] = []
    for label in labels:
        raw_key = str(label.get("key", "")).strip()
        raw_name = str(label.get("name", "")).strip()
        canonical = canonical_label_key(raw_key or raw_name)
        candidates = [value for value in (raw_name, raw_key) if value]
        should_remove = canonical not in CANONICAL_LABEL_KEYS
        if canonical in CANONICAL_LABEL_KEYS:
            should_remove = any(value not in default_names and canonical_label_key(value) == canonical for value in candidates)
        if should_remove:
            for value in candidates:
                if value not in removed and value not in default_names:
                    removed.append(value)
    return removed


def _write_settings(path: Path, labels: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}
    existing["labels"] = labels
    existing["updatedAt"] = existing.get("updatedAt") or "1970-01-01T00:00:00.000Z"
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
