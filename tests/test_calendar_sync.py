from __future__ import annotations

from datetime import datetime

from calendar_sync import CalendarAvailabilitySync


class FakeCalendarConnector:
    def __init__(self, events=None, blocks=None):
        self.events = events or []
        self.blocks = blocks or []
        self.upserts = []
        self.deletes = []

    def list_calendar_events(self, start_iso, end_iso):
        return self.events

    def list_inboxpilot_calendar_blocks(self, start_iso, end_iso):
        return self.blocks

    def upsert_calendar_block(self, uid, start_iso, end_iso, existing_event_id=None):
        self.upserts.append(
            {
                "uid": uid,
                "start": start_iso,
                "end": end_iso,
                "existing_event_id": existing_event_id,
            }
        )

    def delete_calendar_event(self, event_id):
        self.deletes.append(event_id)


def entry(name, account, connector):
    return {"name": name, "account": account, "connector": connector}


def test_sync_creates_busy_blocks_on_other_connected_calendars(tmp_path):
    gmail = FakeCalendarConnector(events=[{"id": "evt-1", "start": "2026-08-12T08:00:00+00:00", "end": "2026-08-12T08:30:00+00:00"}])
    outlook = FakeCalendarConnector()
    sync = CalendarAvailabilitySync({"calendar_sync": {"state_file": str(tmp_path / "state.json")}})

    sync.run_once({"client-a": {"gmail:main": entry("gmail", "main", gmail), "hotmail:main": entry("hotmail", "main", outlook)}}, now=datetime.fromisoformat("2026-08-12T00:10:00+02:00"))

    assert gmail.upserts == []
    assert len(outlook.upserts) == 1
    assert outlook.upserts[0]["start"] == "2026-08-12T08:00:00+00:00"
    assert outlook.upserts[0]["end"] == "2026-08-12T08:30:00+00:00"


def test_sync_updates_existing_block_and_deletes_stale_blocks(tmp_path):
    gmail = FakeCalendarConnector(events=[{"id": "evt-1", "start": "2026-08-12T08:00:00+00:00", "end": "2026-08-12T08:30:00+00:00"}])
    outlook = FakeCalendarConnector(blocks=[{"id": "old", "uid": "stale"}])
    sync = CalendarAvailabilitySync({"calendar_sync": {"state_file": str(tmp_path / "state.json")}})

    sync.run_once({"client-a": {"gmail:main": entry("gmail", "main", gmail), "hotmail:main": entry("hotmail", "main", outlook)}}, now=datetime.fromisoformat("2026-08-12T00:10:00+02:00"))

    assert outlook.deletes == ["old"]
    assert len(outlook.upserts) == 1


def test_single_connected_calendar_does_nothing(tmp_path):
    gmail = FakeCalendarConnector(events=[{"id": "evt-1", "start": "2026-08-12T08:00:00+00:00", "end": "2026-08-12T08:30:00+00:00"}])
    sync = CalendarAvailabilitySync({"calendar_sync": {"state_file": str(tmp_path / "state.json")}})

    sync.run_once({"client-a": {"gmail:main": entry("gmail", "main", gmail)}}, now=datetime.fromisoformat("2026-08-12T00:10:00+02:00"))

    assert gmail.upserts == []
    assert gmail.deletes == []
