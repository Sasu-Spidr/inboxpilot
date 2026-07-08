import json

from client_settings import action_for_client, label_color_for_client, label_name_for_client, managed_label_names_for_client


def test_client_settings_override_label_name_and_managed_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "client-a.json").write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "key": "À traiter",
                        "name": "Factures",
                        "color": "#0d9488",
                        "prepareDraft": False,
                        "autoReply": False,
                        "autoDelete": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert label_name_for_client("client-a", "À traiter", "À traiter") == "Factures"
    assert label_color_for_client("client-a", "À traiter") == "#0d9488"
    assert "Factures" in managed_label_names_for_client("client-a")


def test_client_settings_override_action_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "client-a.json").write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "Newsletter", "name": "Newsletter", "autoDelete": True, "prepareDraft": True, "autoReply": True},
                    {"key": "Relance", "name": "Relance", "autoDelete": False, "prepareDraft": True, "autoReply": False},
                    {"key": "FYI", "name": "FYI", "autoDelete": False, "prepareDraft": False, "autoReply": True},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert action_for_client("client-a", "Newsletter", "keep") == "trash"
    assert action_for_client("client-a", "Relance", "keep") == "draft"
    assert action_for_client("client-a", "FYI", "mark_read") == "draft"
    assert action_for_client("client-a", "Notification", "mark_read") == "mark_read"
