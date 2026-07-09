import json

from activity_store import record_email_activity


def test_record_email_activity_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    record_email_activity(
        client_id="client-1",
        connector="gmail",
        account="main",
        email={"id": "m1", "thread_id": "t1", "subject": "Facture", "sender": "billing@example.com"},
        label="À traiter",
        action="keep",
        draft_created=False,
    )

    path = tmp_path / "activity" / "events.jsonl"
    event = json.loads(path.read_text(encoding="utf-8").strip())
    assert event["client_id"] == "client-1"
    assert event["connector"] == "gmail"
    assert event["subject"] == "Facture"
    assert event["label"] == "À traiter"
    assert event["processed_at"]
