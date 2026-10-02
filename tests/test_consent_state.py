import json

from consent_state import ai_processing_consent_granted


def test_consent_state_fails_closed_when_missing(tmp_path):
    assert ai_processing_consent_granted("client", str(tmp_path)) is False


def test_consent_state_requires_timestamp_and_version(tmp_path):
    directory = tmp_path / "consents"
    directory.mkdir()
    (directory / "client.json").write_text(json.dumps({"granted": True}), encoding="utf-8")
    assert ai_processing_consent_granted("client", str(tmp_path)) is False


def test_consent_state_accepts_explicit_record(tmp_path):
    directory = tmp_path / "consents"
    directory.mkdir()
    (directory / "client.json").write_text(
        json.dumps({"granted": True, "version": "2026-10-02", "granted_at": "2026-10-02T10:00:00Z"}),
        encoding="utf-8",
    )
    assert ai_processing_consent_granted("client", str(tmp_path)) is True
