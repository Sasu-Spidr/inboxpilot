from __future__ import annotations

import argparse
import json
from pathlib import Path

from client_registry import load_registered_clients
from oauth_server import OAuthOnboardingServer, load_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--base-url", default="https://inboxpilot.mallow-hub.tech")
    parser.add_argument("--data-dir", default="./data")
    args = parser.parse_args()

    settings = load_settings(args.config)
    server = OAuthOnboardingServer(settings, args.base_url)
    settings_clients = {path.stem for path in (Path(args.data_dir) / "client-settings").glob("*.json")}
    registry_clients = set(load_registered_clients(settings).keys())
    clients = sorted(settings_clients | registry_clients)
    results = {}
    for client_id in clients:
        try:
            results[client_id] = server.sync_label_settings(client_id, [])
        except Exception as exc:
            results[client_id] = {"error": str(exc)}
        print(f"{client_id}: {results[client_id]}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
