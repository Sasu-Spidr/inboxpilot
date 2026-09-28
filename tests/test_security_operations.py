import json
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

from scripts import analyze_openbao_audit as audit_module
from scripts.analyze_openbao_audit import analyze
from scripts.rotate_token_encryption_key import rotate


ROOT = Path(__file__).resolve().parents[1]


def audit_row(kind: str, role: str, path: str, *, error: str = "") -> dict:
    row = {
        "time": datetime.now(timezone.utc).isoformat(),
        "type": kind,
        "auth": {"display_name": role, "metadata": {"role_name": role}},
        "request": {"operation": "read", "path": path},
    }
    if error:
        row["error"] = error
    return row


def test_audit_analyzer_detects_cross_zone_volume_and_denied_bursts():
    rows = [
        audit_row("request", "inboxpilot-frontend", "secret/data/inboxpilot/groq"),
        audit_row("request", "inboxpilot-worker", "secret/data/inboxpilot/frontend"),
    ]
    rows += [
        audit_row("request", "inboxpilot-worker", "secret/data/inboxpilot/groq")
        for _ in range(3)
    ]
    rows += [
        audit_row("response", "inboxpilot-worker", "secret/data/inboxpilot/frontend", error="permission denied")
        for _ in range(2)
    ]

    alerts = analyze(
        rows,
        since=datetime(2000, 1, 1, tzinfo=timezone.utc),
        read_threshold=3,
        denied_threshold=2,
    )

    assert any("cross-zone read attempt" in alert for alert in alerts)
    assert any("high read volume" in alert for alert in alerts)
    assert any("permission-denied burst" in alert for alert in alerts)


def test_token_key_rotation_dry_run_and_apply(tmp_path: Path):
    data_dir = tmp_path / "data"
    token = data_dir / "tokens" / "account.token.enc"
    state = data_dir / "state" / "processed_messages.enc"
    token.parent.mkdir(parents=True)
    state.parent.mkdir(parents=True)

    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    old = Fernet(old_key)
    token.write_bytes(old.encrypt(json.dumps({"access_token": "example"}).encode()))
    state.write_bytes(old.encrypt(json.dumps({"records": {}}).encode()))

    backup = tmp_path / "backup"
    assert rotate(data_dir, old_key, new_key, backup, apply=False) == 2
    assert not backup.exists()
    assert rotate(data_dir, old_key, new_key, backup, apply=True) == 2

    new = Fernet(new_key)
    assert json.loads(new.decrypt(token.read_bytes()))["access_token"] == "example"
    assert json.loads(new.decrypt(state.read_bytes())) == {"records": {}}
    assert old.decrypt((backup / "tokens" / token.name).read_bytes())


def test_audit_alert_webhook_is_read_from_openbao_and_token_revoked(tmp_path: Path):
    calls: list[tuple[str, str]] = []

    def fake_call(url: str, *, body=None, token: str = "", timeout: float = 5.0):
        calls.append((url, token))
        if url.endswith("/auth/approle/login"):
            assert body == {"role_id": "rid", "secret_id": "sid"}
            return {"auth": {"client_token": "s.short-lived"}}
        if url.endswith("/auth/token/revoke-self"):
            return {}
        assert token == "s.short-lived"
        return {"data": {"data": {"webhook_url": "https://hooks.example/abc"}}}

    (tmp_path / "role_id").write_text("rid\n", encoding="utf-8")
    (tmp_path / "secret_id").write_text("sid\n", encoding="utf-8")

    with mock.patch.object(audit_module, "_bao_call", fake_call):
        url = audit_module.webhook_url_from_openbao("http://127.0.0.1:8200/", tmp_path)

    assert url == "https://hooks.example/abc"
    assert calls[0][0] == "http://127.0.0.1:8200/v1/auth/approle/login"
    assert calls[1][0] == "http://127.0.0.1:8200/v1/secret/data/audit/alerting"
    assert calls[2][0] == "http://127.0.0.1:8200/v1/auth/token/revoke-self"


def test_audit_alert_webhook_failure_still_revokes_the_token(tmp_path: Path):
    calls: list[str] = []

    def fake_call(url: str, *, body=None, token: str = "", timeout: float = 5.0):
        calls.append(url)
        if url.endswith("/auth/approle/login"):
            return {"auth": {"client_token": "t"}}
        if url.endswith("/auth/token/revoke-self"):
            return {}
        return {"data": {"data": {}}}

    (tmp_path / "role_id").write_text("rid", encoding="utf-8")
    (tmp_path / "secret_id").write_text("sid", encoding="utf-8")

    with mock.patch.object(audit_module, "_bao_call", fake_call):
        try:
            audit_module.webhook_url_from_openbao("http://127.0.0.1:8200", tmp_path)
        except RuntimeError as exc:
            assert "webhook_url" in str(exc)
        else:
            raise AssertionError("an unusable webhook_url must raise")

    assert any("revoke-self" in url for url in calls)
