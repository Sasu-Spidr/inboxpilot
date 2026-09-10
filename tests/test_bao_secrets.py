import json

import pytest
import requests

from bao_secrets import BaoSecretError, BaoSecrets, load_yaml_settings, runtime_secret


class FakeResponse:
    def __init__(self, values, status_code=200):
        self.values = values
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"data": {"data": self.values}}


class FakeSession:
    def __init__(self, payloads=None, error=None):
        self.payloads = payloads or {}
        self.error = error
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        if self.error:
            raise self.error
        path = url.split("/v1/", 1)[1]
        return FakeResponse(self.payloads[path])


def required_payloads():
    return {
        "secret/data/inboxpilot/groq": {"api_key": "bao-groq"},
        "secret/data/inboxpilot/crypto": {"token_encryption_key": "bao-token"},
        "secret/data/inboxpilot/oauth/microsoft": {
            "client_id": "bao-client-id",
            "client_secret": "bao-client-secret",
        },
        "secret/data/inboxpilot/oauth/gmail": {
            "client_config": json.dumps({"web": {"client_id": "gmail-id", "client_secret": "gmail-secret"}}),
        },
    }


def test_openbao_is_authoritative_over_secret_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "malicious-environment-value")
    config = tmp_path / "settings.yaml"
    config.write_text("groq_api_key: ${GROQ_API_KEY}\ntoken_encryption_key: ${TOKEN_ENCRYPTION_KEY}\n", encoding="utf-8")
    resolver = BaoSecrets("http://agent:8100", session=FakeSession(required_payloads()))

    settings = load_yaml_settings(str(config), resolver)

    assert settings["groq_api_key"] == "bao-groq"
    assert settings["token_encryption_key"] == "bao-token"
    assert runtime_secret(settings, "GROQ_API_KEY") == "bao-groq"


def test_known_secret_never_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "environment-secret")
    with pytest.raises(BaoSecretError, match="were not loaded"):
        runtime_secret({}, "MICROSOFT_CLIENT_SECRET")


def test_missing_required_secret_fails_settings_load(tmp_path):
    payloads = required_payloads()
    payloads["secret/data/inboxpilot/groq"] = {}
    config = tmp_path / "settings.yaml"
    config.write_text("groq_api_key: ${GROQ_API_KEY}\n", encoding="utf-8")

    with pytest.raises(BaoSecretError, match="GROQ_API_KEY"):
        load_yaml_settings(str(config), BaoSecrets("http://agent:8100", session=FakeSession(payloads)))


def test_unreachable_agent_fails_explicitly(tmp_path):
    config = tmp_path / "settings.yaml"
    config.write_text("groq_api_key: ${GROQ_API_KEY}\n", encoding="utf-8")
    resolver = BaoSecrets(
        "http://agent:8100",
        session=FakeSession(error=requests.ConnectionError("connection refused")),
    )

    with pytest.raises(BaoSecretError, match="Unable to read required OpenBao path"):
        load_yaml_settings(str(config), resolver)


def test_path_payload_is_cached_for_multiple_fields():
    session = FakeSession(required_payloads())
    resolver = BaoSecrets("http://agent:8100", session=session)

    assert resolver.get("MICROSOFT_CLIENT_ID") == "bao-client-id"
    assert resolver.get("MICROSOFT_CLIENT_SECRET") == "bao-client-secret"
    microsoft_calls = [url for url, _ in session.calls if url.endswith("/oauth/microsoft")]
    assert len(microsoft_calls) == 1
