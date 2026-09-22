#!/usr/bin/env python3
"""Detect a small set of actionable anomalies in OpenBao JSON audit logs."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


FRONTEND_FORBIDDEN_PREFIXES = (
    "secret/data/inboxpilot/crypto",
    "secret/data/inboxpilot/groq",
    "secret/data/inboxpilot/oauth/",
)
WORKER_FORBIDDEN_PREFIXES = (
    "secret/data/inboxpilot/frontend",
    "secret/data/inboxpilot/database",
)


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def identity(record: dict[str, Any]) -> str:
    auth = record.get("auth") if isinstance(record.get("auth"), dict) else {}
    metadata = auth.get("metadata") if isinstance(auth.get("metadata"), dict) else {}
    parts = [auth.get("display_name"), metadata.get("role_name")]
    policies = auth.get("policies")
    if isinstance(policies, list):
        parts.extend(policies)
    return " ".join(str(part) for part in parts if part).lower() or "unknown"


def records(paths: list[Path]) -> Iterable[dict[str, Any]]:
    for path in paths:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Ignoring invalid JSON in {path.name}:{line_number}.", file=sys.stderr)
                    continue
                if isinstance(value, dict):
                    yield value


def is_permission_denied(record: dict[str, Any]) -> bool:
    values: list[object] = [record.get("error")]
    response = record.get("response")
    if isinstance(response, dict):
        values.append(response.get("error"))
        data = response.get("data")
        if isinstance(data, dict):
            values.extend([data.get("error"), data.get("errors")])
    text = " ".join(json.dumps(value) for value in values if value is not None).lower()
    return "permission denied" in text or "status_code\": 403" in text or "code\": 403" in text


def analyze(
    rows: Iterable[dict[str, Any]],
    *,
    since: datetime,
    read_threshold: int,
    denied_threshold: int,
) -> list[str]:
    reads: Counter[tuple[str, str]] = Counter()
    denied: Counter[str] = Counter()
    cross_zone: Counter[tuple[str, str]] = Counter()

    for row in rows:
        timestamp = parse_time(row.get("time"))
        if timestamp is None or timestamp < since:
            continue
        actor = identity(row)
        request = row.get("request") if isinstance(row.get("request"), dict) else {}
        path = str(request.get("path") or "").lstrip("/")
        operation = str(request.get("operation") or "").lower()

        if row.get("type") == "request" and operation in {"read", "list"} and path:
            reads[(actor, path)] += 1
            if "frontend" in actor and path.startswith(FRONTEND_FORBIDDEN_PREFIXES):
                cross_zone[(actor, path)] += 1
            if "worker" in actor and path.startswith(WORKER_FORBIDDEN_PREFIXES):
                cross_zone[(actor, path)] += 1

        if row.get("type") == "response" and is_permission_denied(row):
            denied[actor] += 1

    alerts: list[str] = []
    for (actor, path), count in sorted(reads.items()):
        if count >= read_threshold:
            alerts.append(f"high read volume: identity={actor}, path={path}, count={count}")
    for (actor, path), count in sorted(cross_zone.items()):
        alerts.append(f"cross-zone read attempt: identity={actor}, path={path}, count={count}")
    for actor, count in sorted(denied.items()):
        if count >= denied_threshold:
            alerts.append(f"permission-denied burst: identity={actor}, count={count}")
    return alerts


def send_webhook(url: str, environment: str, alerts: list[str]) -> None:
    body = {
        "text": "InboxPilot OpenBao audit alert "
        f"({environment})\n- " + "\n- ".join(alerts)
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError(f"Alert webhook returned HTTP {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--window-minutes", type=int, default=5)
    parser.add_argument("--read-threshold", type=int, default=60)
    parser.add_argument("--denied-threshold", type=int, default=5)
    parser.add_argument("--webhook-url", default=os.getenv("OPENBAO_ALERT_WEBHOOK_URL", ""))
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    alerts = analyze(
        records(args.logs),
        since=now - timedelta(minutes=max(args.window_minutes, 1)),
        read_threshold=max(args.read_threshold, 1),
        denied_threshold=max(args.denied_threshold, 1),
    )
    if not alerts:
        print(f"OpenBao audit check OK for {args.environment}.")
        return 0

    for alert in alerts:
        print(f"ALERT: {alert}", file=sys.stderr)
    if args.webhook_url:
        try:
            send_webhook(args.webhook_url, args.environment, alerts)
        except Exception:
            # Never include the webhook URL (which may embed a credential) in logs.
            print("Alert webhook delivery failed.", file=sys.stderr)
            return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
