from oauth_server import OAuthOnboardingServer


def test_sync_label_settings_deletes_only_explicitly_removed_labels(tmp_path):
    gmail_token = tmp_path / "gmail.token.enc"
    gmail_token.write_text("token", encoding="utf-8")
    settings_payload = {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "clients": {
            "client-a": {
                "connectors": {
                    "gmail": {"accounts": [{"account": "main", "credentials_file": "secrets/google-oauth-client.json", "token_file": str(gmail_token)}]},
                }
            }
        },
    }

    class FakeConnector:
        def __init__(self):
            self.deleted = []
            self.synced = []

        def list_user_labels(self):
            return ["À répondre"]

        def delete_label(self, label_name):
            self.deleted.append(label_name)
            return True

        def sync_label_color(self, label_name, color):
            self.synced.append((label_name, color))

    gmail = FakeConnector()
    server = OAuthOnboardingServer(settings_payload, "http://localhost:8080")
    server._label_sync_connector = lambda provider, account_cfg, token_file: gmail  # type: ignore[method-assign]

    result = server.sync_label_settings("client-a", ["Ancien label"])

    assert gmail.deleted == ["Ancien label"]
    assert result["deleted"] == 1


def test_sync_label_settings_deletes_stale_processed_labels(tmp_path):
    gmail_token = tmp_path / "gmail.token.enc"
    gmail_token.write_text("token", encoding="utf-8")
    state_file = tmp_path / "processed.enc"
    settings_payload = {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "state_file": str(state_file),
        "clients": {
            "client-a": {
                "connectors": {
                    "gmail": {"accounts": [{"account": "main", "credentials_file": "secrets/google-oauth-client.json", "token_file": str(gmail_token)}]},
                }
            }
        },
    }

    class FakeConnector:
        def __init__(self):
            self.deleted = []
            self.synced = []

        def list_user_labels(self):
            return ["À lire", "Ancien label"]

        def delete_label(self, label_name):
            self.deleted.append(label_name)
            return True

        def sync_label_color(self, label_name, color):
            self.synced.append((label_name, color))

    gmail = FakeConnector()
    server = OAuthOnboardingServer(settings_payload, "http://localhost:8080")
    server.store.save(
        str(state_file),
        {
            "records": {
                "client-a:gmail:main:msg-1": {"label": "Ancien label"},
                "client-a:gmail:main:msg-2": {"label": "À lire"},
                "client-a:gmail:other:msg-3": {"label": "Autre compte"},
            }
        },
    )
    server._label_sync_connector = lambda provider, account_cfg, token_file: gmail  # type: ignore[method-assign]

    result = server.sync_label_settings("client-a", [])

    assert gmail.deleted == ["Ancien label"]
    assert result["deleted"] == 1


def test_sync_label_settings_deletes_disallowed_existing_mailbox_labels(tmp_path):
    gmail_token = tmp_path / "gmail.token.enc"
    gmail_token.write_text("token", encoding="utf-8")
    settings_payload = {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "clients": {
            "client-a": {
                "connectors": {
                    "gmail": {"accounts": [{"account": "main", "credentials_file": "secrets/google-oauth-client.json", "token_file": str(gmail_token)}]},
                }
            }
        },
    }

    class FakeConnector:
        def __init__(self):
            self.deleted = []
            self.synced = []

        def list_user_labels(self):
            return ["À répondre", "Marketing", "Perso"]

        def delete_label(self, label_name):
            self.deleted.append(label_name)
            return True

        def sync_label_color(self, label_name, color):
            self.synced.append((label_name, color))

    gmail = FakeConnector()
    server = OAuthOnboardingServer(settings_payload, "http://localhost:8080")
    server._label_sync_connector = lambda provider, account_cfg, token_file: gmail  # type: ignore[method-assign]

    result = server.sync_label_settings("client-a", [])

    assert gmail.deleted == ["Marketing", "Perso"]
    assert result["deleted"] == 2
