from __future__ import annotations

import argparse
import json
from pathlib import Path

from oauth_server import OAuthOnboardingServer, load_settings

REMOVED_LEGACY_LABELS = [
    "Relance",
    "Commentaire",
    "FYI",
    "Mise à jour de réunion",
    "Newsletter",
    "Marketing",
    "Traité",
    "En attente de réponse",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--base-url", default="https://inboxpilot.mallow-hub.tech")
    parser.add_argument("--data-dir", default="./data")
    args = parser.parse_args()

    server = OAuthOnboardingServer(load_settings(args.config), args.base_url)
    clients = sorted(path.stem for path in (Path(args.data_dir) / "client-settings").glob("*.json"))
    results = {}
    for client_id in clients:
        try:
            results[client_id] = server.sync_label_settings(client_id, REMOVED_LEGACY_LABELS)
        except Exception as exc:
            results[client_id] = {"error": str(exc)}
        print(f"{client_id}: {results[client_id]}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
