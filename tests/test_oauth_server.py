from pathlib import Path

from client_registry import build_registered_client, merge_registered_clients, save_registered_client
from oauth_server import OAuthOnboardingServer, render_auth_required, render_home


def settings():
    return {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "clients": {
            "collegue": {
                "connectors": {
                    "gmail": {
                        "accounts": [
                            {
                                "account": "main",
                                "credentials_file": "secrets/collegue/gmail-client-secret.json",
                                "token_file": "data/tokens/collegue-gmail-main.token.enc",
                            }
                        ]
                    }
                }
            }
        },
    }


def test_signed_state_roundtrip():
    server = OAuthOnboardingServer(settings(), "http://localhost:8080")
    state = server._sign_state("gmail", "collegue", "main")
    payload = server._verify_state(state, "gmail")
    assert payload["client"] == "collegue"
    assert payload["account"] == "main"


def test_account_lookup():
    server = OAuthOnboardingServer(settings(), "http://localhost:8080")
    client, account, cfg = server._account("client=collegue&account=main", "gmail")
    assert client == "collegue"
    assert account == "main"
    assert cfg["token_file"] == "data/tokens/collegue-gmail-main.token.enc"


def test_onboarding_home_does_not_expose_clients():
    html = render_home(settings())
    assert "/client?client=collegue" not in html
    assert "Clients configurés" not in html
    assert "Ouvrir mon espace" in html


def test_client_page_requires_frontend_auth():
    html = render_auth_required()
    assert "Espace sécurisé" in html
    assert "Gmail" not in html


def test_registered_client_is_merged(tmp_path):
    cfg = {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "onboarding": {"registry_file": str(tmp_path / "clients.yaml"), "gmail_credentials_file": "./secrets/google-oauth-client.json"},
        "clients": {},
    }
    client = build_registered_client(cfg, "demo-client", "Jean Martin", "jean@example.com")
    save_registered_client(cfg, "demo-client", client)
    merged = merge_registered_clients(cfg)
    assert merged["clients"]["demo-client"]["owner_name"] == "Jean Martin"
    assert Path(tmp_path / "clients.yaml").exists()


def test_sync_label_settings_syncs_defaults_without_pruning_existing_labels(tmp_path):
    gmail_token = tmp_path / "gmail.token.enc"
    hotmail_token = tmp_path / "hotmail.token.enc"
    gmail_token.write_text("token", encoding="utf-8")
    hotmail_token.write_text("token", encoding="utf-8")

    settings_payload = {
        "token_encryption_key": "Hi2vSxtb4LWWU0Anf0MkDr3eQsfcwoS1bOVsfehfe-A=",
        "clients": {
            "client-a": {
                "connectors": {
                    "gmail": {"accounts": [{"account": "main", "credentials_file": "secrets/google-oauth-client.json", "token_file": str(gmail_token)}]},
                    "hotmail": {"accounts": [{"account": "main", "tenant_id": "consumers", "token_file": str(hotmail_token), "client_id": "id"}]},
                }
            }
        },
    }

    class FakeConnector:
        def __init__(self, existing):
            self.existing = existing
            self.deleted = []
            self.synced = []

        def list_user_labels(self):
            return self.existing

        def list_categories(self):
            return self.existing

        def delete_label(self, label_name):
            self.deleted.append(label_name)
            return True

        def sync_label_color(self, label_name, color):
            self.synced.append((label_name, color))

    gmail = FakeConnector(["À répondre", "Custom"])
    hotmail = FakeConnector(["À traiter", "Custom"])

    server = OAuthOnboardingServer(settings_payload, "http://localhost:8080")

    def fake_label_sync_connector(provider, account_cfg, token_file):
        return gmail if provider == "gmail" else hotmail

    server._label_sync_connector = fake_label_sync_connector  # type: ignore[method-assign]

    result = server.sync_label_settings("client-a")

    assert gmail.deleted == ["Custom"]
    assert hotmail.deleted == ["Custom"]
    assert any(name == "À répondre" for name, _ in gmail.synced)
    assert any(name == "À traiter" for name, _ in hotmail.synced)
    assert result["deleted"] == 2
