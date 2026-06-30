from oauth_server import OAuthOnboardingServer


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
