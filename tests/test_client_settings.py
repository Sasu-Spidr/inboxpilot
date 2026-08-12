import json

from client_settings import action_for_client, label_color_for_client, label_name_for_client, managed_label_names_for_client, normalized_labels_for_client


def test_client_settings_keep_canonical_label_names_and_managed_labels(tmp_path, monkeypatch):
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

    assert label_name_for_client("client-a", "À traiter", "À traiter") == "À traiter"
    assert label_color_for_client("client-a", "À traiter") == "#0d9488"
    assert "À traiter" in managed_label_names_for_client("client-a")
    assert "À lire" in managed_label_names_for_client("client-a")
    assert "Commercial" in managed_label_names_for_client("client-a")


def test_client_settings_override_action_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "client-a.json").write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "Commercial", "name": "Commercial", "autoDelete": True, "prepareDraft": False, "autoReply": False},
                    {"key": "À répondre", "name": "À répondre", "autoDelete": False, "prepareDraft": True, "autoReply": False},
                    {"key": "À lire", "name": "À lire", "autoDelete": False, "prepareDraft": False, "autoReply": True},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert action_for_client("client-a", "Commercial", "keep") == "trash"
    assert action_for_client("client-a", "À répondre", "keep") == "draft"
    assert action_for_client("client-a", "Notification", "mark_read") == "mark_read"


def test_client_settings_default_labels_are_added_without_overwriting_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    settings_dir.mkdir()
    (settings_dir / "client-a.json").write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "key": "À répondre",
                        "name": "Réponses prioritaires",
                        "description": "Mon libellé réponse.",
                        "color": "#222222",
                        "prepareDraft": False,
                        "autoReply": False,
                        "autoDelete": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    labels = normalized_labels_for_client("client-a")
    names = [label["name"] for label in labels]

    assert "À répondre" in names
    assert "Réponses prioritaires" not in names
    assert "À traiter" in names
    assert "Commercial" in names
    assert len(labels) == 5


def test_client_settings_can_be_scoped_per_mailbox(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    scoped_dir = settings_dir / "client-a"
    settings_dir.mkdir()
    scoped_dir.mkdir()
    (settings_dir / "client-a.json").write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "Commercial", "name": "Commercial", "color": "#fb7185", "prepareDraft": False, "autoReply": False, "autoDelete": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    (scoped_dir / "gmail--gmail-2.json").write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "Courses", "name": "Courses", "description": "Emails liés aux courses.", "color": "#14b8a6", "prepareDraft": False, "autoReply": False, "autoDelete": False},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert "Courses" not in managed_label_names_for_client("client-a", "gmail", "main")
    assert "Courses" in managed_label_names_for_client("client-a", "gmail", "gmail-2")


def test_label_name_uses_mailbox_scoped_custom_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_dir = tmp_path / "client-settings"
    scoped_dir = settings_dir / "client-a"
    settings_dir.mkdir()
    scoped_dir.mkdir()
    (scoped_dir / "hotmail--main.json").write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "Courses", "name": "Courses perso", "description": "Emails liés aux courses et achats du foyer.", "color": "#3b82f6", "prepareDraft": False, "autoReply": False, "autoDelete": False},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert label_name_for_client("client-a", "Courses", "Courses", "hotmail", "main") == "Courses perso"
    assert label_name_for_client("client-a", "Courses", "Courses", "gmail", "main") == "Courses"
