from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

LOG = logging.getLogger(__name__)

INBOXPILOT_CALENDAR_MARKER = "INBOXPILOT_AVAILABILITY_BLOCK"


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    start: str
    end: str


@dataclass(frozen=True)
class CalendarBlock:
    id: str
    uid: str


class CalendarAvailabilitySync:
    """Daily availability harmonisation across connected mail calendars.

    This is intentionally not a full calendar sync. It creates private busy
    blocks for one day only, so each connected mailbox reflects the user's
    availability without copying event details.
    """

    def __init__(self, settings: dict):
        cfg = settings.get("calendar_sync", {}) or {}
        self.enabled = _bool_env("CALENDAR_SYNC_ENABLED", cfg.get("enabled", True))
        self.run_hour = _int_env("CALENDAR_SYNC_RUN_HOUR", cfg.get("run_hour", 0), minimum=0, maximum=23)
        self.days = _int_env("CALENDAR_SYNC_DAYS", cfg.get("days", 1), minimum=1, maximum=3)
        self.timezone_name = os.getenv("CALENDAR_SYNC_TIMEZONE") or str(cfg.get("timezone") or "Europe/Paris")
        self.state_file = Path(cfg.get("state_file") or os.getenv("CALENDAR_SYNC_STATE_FILE") or "./data/state/calendar_sync.json")

    def run_if_due(self, connectors: dict[str, dict[str, dict[str, Any]]]) -> None:
        if not self.enabled:
            return
        now = datetime.now(ZoneInfo(self.timezone_name))
        if now.hour < self.run_hour:
            return
        key = now.strftime("%Y-%m-%d")
        state = self._load_state()
        if state.get("last_run_key") == key:
            return
        self.run_once(connectors, now=now)
        state["last_run_key"] = key
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state(state)

    def run_once(self, connectors: dict[str, dict[str, dict[str, Any]]], now: datetime | None = None) -> None:
        if not self.enabled:
            log_event("calendar_sync_skipped", status="disabled")
            return
        now = now or datetime.now(ZoneInfo(self.timezone_name))
        start_utc, end_utc = self._window(now)
        for client_id, entries in connectors.items():
            calendar_entries = [
                entry
                for entry in entries.values()
                if hasattr(entry.get("connector"), "list_calendar_events")
                and hasattr(entry.get("connector"), "list_inboxpilot_calendar_blocks")
                and hasattr(entry.get("connector"), "upsert_calendar_block")
                and hasattr(entry.get("connector"), "delete_calendar_event")
            ]
            if len(calendar_entries) < 2:
                continue
            self._sync_client(client_id, calendar_entries, start_utc, end_utc)

    def _sync_client(self, client_id: str, entries: list[dict[str, Any]], start_utc: str, end_utc: str) -> None:
        source_events: dict[str, list[CalendarEvent]] = {}
        for entry in entries:
            key = calendar_entry_key(entry)
            try:
                raw_events = entry["connector"].list_calendar_events(start_utc, end_utc)
                source_events[key] = [
                    CalendarEvent(id=str(event["id"]), start=str(event["start"]), end=str(event["end"]))
                    for event in raw_events
                    if event.get("id") and event.get("start") and event.get("end")
                ]
                log_event(
                    "calendar_events_listed",
                    client_id=client_id,
                    connector=entry["name"],
                    account=entry["account"],
                    status="ok",
                    count=len(source_events[key]),
                )
            except Exception as exc:
                source_events[key] = []
                log_event(
                    "calendar_events_listing_failed",
                    logging.WARNING,
                    client_id=client_id,
                    connector=entry["name"],
                    account=entry["account"],
                    status="warning",
                    error=str(exc),
                )

        for target in entries:
            target_key = calendar_entry_key(target)
            desired: dict[str, CalendarEvent] = {}
            for source in entries:
                source_key = calendar_entry_key(source)
                if source_key == target_key:
                    continue
                for event in source_events.get(source_key, []):
                    uid = calendar_block_uid(client_id, source_key, target_key, event.id, event.start, event.end)
                    desired[uid] = event

            try:
                existing = [
                    CalendarBlock(id=str(block["id"]), uid=str(block["uid"]))
                    for block in target["connector"].list_inboxpilot_calendar_blocks(start_utc, end_utc)
                    if block.get("id") and block.get("uid")
                ]
                existing_by_uid = {block.uid: block.id for block in existing}
                for uid, event in desired.items():
                    target["connector"].upsert_calendar_block(uid, event.start, event.end, existing_event_id=existing_by_uid.get(uid))
                stale_uids = set(existing_by_uid) - set(desired)
                for uid in stale_uids:
                    target["connector"].delete_calendar_event(existing_by_uid[uid])
                log_event(
                    "calendar_availability_synced",
                    client_id=client_id,
                    connector=target["name"],
                    account=target["account"],
                    status="ok",
                    created_or_updated=len(desired),
                    deleted=len(stale_uids),
                )
            except Exception as exc:
                log_event(
                    "calendar_availability_sync_failed",
                    logging.WARNING,
                    client_id=client_id,
                    connector=target["name"],
                    account=target["account"],
                    status="warning",
                    error=str(exc),
                )

    def _window(self, now: datetime) -> tuple[str, str]:
        tz = ZoneInfo(self.timezone_name)
        local = now.astimezone(tz)
        start_local = datetime.combine(local.date(), time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=self.days)
        return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()

    def _load_state(self) -> dict:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as exc:
            LOG.warning("Calendar sync state ignored: %s", exc)
            return {}

    def _save_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def calendar_entry_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('name')}:{entry.get('account')}"


def calendar_block_uid(client_id: str, source_key: str, target_key: str, event_id: str, start: str, end: str) -> str:
    raw = "|".join([client_id, source_key, target_key, event_id, start, end])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _bool_env(name: str, default) -> bool:
    raw = os.getenv(name)
    if raw is None:
        raw = default
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def _int_env(name: str, default, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    value = default if raw is None else raw
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = int(default)
    return max(minimum, min(maximum, number))


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    LOG.log(level, event, extra={"event": event, **fields})
