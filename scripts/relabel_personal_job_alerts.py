from __future__ import annotations

import argparse
import logging

from main import MailWorker, account_specific_classification_override, load_settings


CLIENT_ID = "ilyesseeladaoui2-gmail-com"
CONNECTOR = "gmail"
ACCOUNT = "gmail-2"


def main() -> None:
    parser = argparse.ArgumentParser(description="Relabellise les alertes emploi de la boîte Gmail personnelle en Commercial.")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
    worker = MailWorker(load_settings(args.config))
    entry = (worker.connectors.get(CLIENT_ID) or {}).get(f"{CONNECTOR}:{ACCOUNT}")
    if not entry:
        raise SystemExit(f"Boîte introuvable ou non connectée: {CLIENT_ID}/{CONNECTOR}/{ACCOUNT}")

    connector = entry["connector"]
    checked = relabeled = skipped = 0
    for email in connector.unread_emails(args.limit):
        checked += 1
        decision = account_specific_classification_override(CLIENT_ID, CONNECTOR, ACCOUNT, email)
        if not decision:
            skipped += 1
            continue
        if not args.dry_run:
            worker._apply_label(  # noqa: SLF001 - maintenance script ciblé
                connector,
                CONNECTOR,
                email["id"],
                decision["label"],
                CLIENT_ID,
                ACCOUNT,
                decision["action"],
                decision["priority"],
            )
            worker.state.complete(
                client_id=CLIENT_ID,
                connector=CONNECTOR,
                account=ACCOUNT,
                message_id=email["id"],
                thread_id=email.get("thread_id"),
                label=decision["label"],
                action=decision["action"],
                draft_created=False,
                received_at=email.get("received_at"),
            )
        relabeled += 1
    print(f"checked={checked} relabeled={relabeled} skipped={skipped} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
