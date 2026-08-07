from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client_settings import load_client_settings, normalized_labels_for_client
from main import MailWorker, load_settings
from oauth_server import OAuthOnboardingServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Affiche les libellés SaaS, boîte mail et historique agent d'un client.")
    parser.add_argument("client")
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)
    server = OAuthOnboardingServer(settings, settings.get("oauth_base_url", "http://localhost:8080"))
    client = (settings.get("clients") or {}).get(args.client) or {}

    print("CLIENT", args.client)
    print("SAAS_RAW")
    print(json.dumps(load_client_settings(args.client), ensure_ascii=False, indent=2))
    print("SAAS_NORMALIZED")
    print(json.dumps(normalized_labels_for_client(args.client), ensure_ascii=False, indent=2))
    print("MAILBOX_LABELS")
    for provider, accounts in (
        ("gmail", client.get("connectors", {}).get("gmail", {}).get("accounts", []) or []),
        ("hotmail", client.get("connectors", {}).get("hotmail", {}).get("accounts", []) or []),
    ):
        for account_cfg in accounts:
            token_file = account_cfg.get("token_file", "")
            account = account_cfg.get("account") or account_cfg.get("id") or "main"
            if not token_file or not Path(token_file).exists():
                print(json.dumps({"provider": provider, "account": account, "connected": False}, ensure_ascii=False))
                continue
            try:
                connector = server._label_sync_connector(provider, account_cfg, token_file)  # noqa: SLF001 - operational audit
                existing = connector.list_user_labels() if provider == "gmail" else connector.list_categories()
                print(json.dumps({"provider": provider, "account": account, "connected": True, "labels": existing}, ensure_ascii=False))
            except Exception as exc:  # pragma: no cover - operational audit
                print(json.dumps({"provider": provider, "account": account, "connected": True, "error": str(exc)}, ensure_ascii=False))

    print("STATE_LABELS")
    worker = MailWorker(settings)
    counts: dict[str, int] = {}
    for key, record in worker.state.records.items():
        if str(record.get("client_id") or key.split(":", 1)[0]) != args.client:
            continue
        label = str(record.get("label") or "")
        counts[label] = counts.get(label, 0) + 1
    print(json.dumps({"counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
