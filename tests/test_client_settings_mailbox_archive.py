from __future__ import annotations

import json

from client_settings import (
    archive_scoped_settings_for_email,
    email_settings_archive_path,
    restore_scoped_settings_for_email,
    scoped_settings_path,
)


def test_archive_and_restore_scoped_settings_by_email(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    client_id = "client-example"
    original_slot = "gmail-2"
    restored_slot = "gmail-5"
    email = "User@Example.com"
    payload = {
        "labels": [
            {
                "key": "Courses",
                "name": "Courses",
                "description": "Emails liés aux achats alimentaires.",
                "color": "#14b8a6",
                "prepareDraft": True,
                "autoReply": False,
                "autoDelete": False,
            }
        ]
    }

    original_path = scoped_settings_path(client_id, "gmail", original_slot)
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_text(json.dumps(payload), encoding="utf-8")

    assert archive_scoped_settings_for_email(client_id, "gmail", original_slot, email) is True

    archive_path = email_settings_archive_path(client_id, "gmail", "user@example.com")
    assert archive_path.exists()
    assert json.loads(archive_path.read_text(encoding="utf-8")) == payload

    assert restore_scoped_settings_for_email(client_id, "gmail", restored_slot, "user@example.com") is True

    restored_path = scoped_settings_path(client_id, "gmail", restored_slot)
    assert restored_path.exists()
    assert json.loads(restored_path.read_text(encoding="utf-8")) == payload


def test_restore_scoped_settings_returns_false_when_no_archive(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    assert restore_scoped_settings_for_email("client-example", "hotmail", "hotmail-2", "missing@example.com") is False
    assert not scoped_settings_path("client-example", "hotmail", "hotmail-2").exists()
