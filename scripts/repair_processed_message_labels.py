from __future__ import annotations

import argparse
import logging
from typing import Any

from main import LEGACY_LABEL_CLEANUP_VERSION, MailWorker, current_utc_iso, load_settings, normalize_active_label


def main() -> None:
    parser = argparse.ArgumentParser(description="Réapplique les libellés officiels aux emails déjà traités.")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--client", default="")
    parser.add_argument("--connector", choices=["gmail", "hotmail"], default=None)
    parser.add_argument("--account", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
    worker = MailWorker(load_settings(args.config))
    records = list(worker.state.records.items())

    checked = repaired = skipped = failed = 0
    for key, record in records:
        if args.limit and checked >= args.limit:
            break
        client_id, connector_name, account, message_id = _record_identity(key, record)
        if not client_id or not connector_name or not account or not message_id:
            skipped += 1
            continue
        if args.client and client_id != args.client:
            continue
        if args.connector and connector_name != args.connector:
            continue
        if args.account and account != args.account:
            continue
        checked += 1
        original_label = str(record.get("label") or "")
        label = normalize_active_label(client_id, original_label)
        action = str(record.get("action") or "keep")
        is_legacy_record = bool(original_label and original_label != label)
        repaired_version = max(
            int(record.get("label_repaired_version") or 0),
            int(record.get("legacy_labels_cleanup_version") or 0),
        )
        if repaired_version >= LEGACY_LABEL_CLEANUP_VERSION or not _should_repair(label, action, is_legacy_record):
            skipped += 1
            continue
        try:
            entry = _entry_or_none(worker, client_id, connector_name, account)
            if not entry:
                if is_legacy_record and not args.dry_run:
                    worker.state.complete(
                        client_id=client_id,
                        connector=connector_name,
                        account=account,
                        message_id=message_id,
                        thread_id=record.get("thread_id"),
                        label=label,
                        action=action,
                        draft_created=bool(record.get("draft_created")),
                        received_at=record.get("received_at"),
                        label_repaired_at=current_utc_iso(),
                        label_repaired_version=LEGACY_LABEL_CLEANUP_VERSION,
                        label_repair_skipped_reason="connector_not_connected",
                        legacy_labels_cleanup_version=LEGACY_LABEL_CLEANUP_VERSION,
                    )
                    repaired += 1
                    continue
                skipped += 1
                continue
            if action in {"trash", "trash_unread_expired"}:
                if not args.dry_run:
                    worker.state.complete(
                        client_id=client_id,
                        connector=connector_name,
                        account=account,
                        message_id=message_id,
                        thread_id=record.get("thread_id"),
                        label=label,
                        action=action,
                        draft_created=bool(record.get("draft_created")),
                        received_at=record.get("received_at"),
                        label_repaired_at=current_utc_iso(),
                        label_repaired_version=LEGACY_LABEL_CLEANUP_VERSION,
                        legacy_labels_cleanup_version=LEGACY_LABEL_CLEANUP_VERSION,
                    )
                repaired += 1
                continue
            if not args.dry_run:
                worker._apply_label(  # noqa: SLF001 - maintenance script
                    entry["connector"],
                    connector_name,
                    message_id,
                    label,
                    client_id,
                    account,
                    action,
                    str(record.get("priority") or "medium"),
                )
                worker.state.complete(
                    client_id=client_id,
                    connector=connector_name,
                    account=account,
                    message_id=message_id,
                    thread_id=record.get("thread_id"),
                    label=label,
                    action=action,
                    draft_created=bool(record.get("draft_created")),
                    received_at=record.get("received_at"),
                    label_repaired_at=current_utc_iso(),
                    label_repaired_version=LEGACY_LABEL_CLEANUP_VERSION,
                    legacy_labels_cleanup_version=LEGACY_LABEL_CLEANUP_VERSION,
                )
            repaired += 1
        except Exception as exc:  # pragma: no cover - used operationally
            if "404 Client Error" in str(exc):
                if not args.dry_run:
                    worker.state.complete(
                        client_id=client_id,
                        connector=connector_name,
                        account=account,
                        message_id=message_id,
                        thread_id=record.get("thread_id"),
                        label=label,
                        action=action,
                        draft_created=bool(record.get("draft_created")),
                        received_at=record.get("received_at"),
                        label_repaired_at=current_utc_iso(),
                        label_repaired_version=LEGACY_LABEL_CLEANUP_VERSION,
                        label_repair_skipped_reason="message_not_found",
                        legacy_labels_cleanup_version=LEGACY_LABEL_CLEANUP_VERSION,
                    )
                skipped += 1
                continue
            failed += 1
            print(f"FAILED client={client_id} connector={connector_name} account={account} message={message_id} label={label}: {exc}")

    print(f"checked={checked} repaired={repaired} skipped={skipped} failed={failed} dry_run={args.dry_run}")


def _record_identity(key: str, record: dict[str, Any]) -> tuple[str, str, str, str]:
    client_id = str(record.get("client_id") or "")
    connector = str(record.get("connector") or "")
    account = str(record.get("account") or "")
    message_id = str(record.get("message_id") or "")
    if key and not client_id:
        parts = key.split(":", 3)
        if len(parts) == 4:
            client_id, connector, account, message_id = parts
    return client_id, connector, account, message_id


def _entry_or_none(worker: MailWorker, client_id: str, connector_name: str, account: str) -> dict[str, Any] | None:
    return (worker.connectors.get(client_id) or {}).get(f"{connector_name}:{account}")


def _should_repair(label: str, action: str, is_legacy_record: bool = False) -> bool:
    if not label or label == "pre_activation":
        return False
    if not is_legacy_record:
        return False
    if action in {"trash", "trash_unread_expired"}:
        return True
    return label in {"À répondre", "À traiter", "À lire", "Notification", "Commercial"}


if __name__ == "__main__":
    main()

