from __future__ import annotations

import argparse
import logging
from pathlib import Path

from client_settings import LEGACY_LABEL_NAMES
from main import load_settings
from oauth_server import OAuthOnboardingServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Supprime uniquement les anciens libellés InboxPilot connus dans Gmail/Outlook.")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--client", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
    settings = load_settings(args.config)
    server = OAuthOnboardingServer(settings, settings.get("oauth_base_url", "http://localhost:8080"))

    deleted = skipped = failed = 0
    for client_id, client in (settings.get("clients") or {}).items():
        if args.client and client_id != args.client:
            continue
        for provider, accounts in (
            ("gmail", client.get("connectors", {}).get("gmail", {}).get("accounts", []) or []),
            ("hotmail", client.get("connectors", {}).get("hotmail", {}).get("accounts", []) or []),
        ):
            for account_cfg in accounts:
                token_file = account_cfg.get("token_file", "")
                account = account_cfg.get("account") or account_cfg.get("id") or "main"
                if not token_file or not Path(token_file).exists():
                    skipped += 1
                    continue
                try:
                    connector = server._label_sync_connector(provider, account_cfg, token_file)  # noqa: SLF001 - maintenance script
                    existing = connector.list_user_labels() if provider == "gmail" else connector.list_categories()
                    legacy_existing = [label for label in existing if label in LEGACY_LABEL_NAMES]
                    for label in legacy_existing:
                        if not args.dry_run and connector.delete_label(label):
                            deleted += 1
                        elif args.dry_run:
                            deleted += 1
                    print(f"client={client_id} provider={provider} account={account} legacy_found={legacy_existing}")
                except Exception as exc:  # pragma: no cover - operational script
                    failed += 1
                    print(f"FAILED client={client_id} provider={provider} account={account}: {exc}")
    print(f"deleted={deleted} skipped={skipped} failed={failed} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
