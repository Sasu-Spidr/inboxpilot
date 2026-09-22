import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

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


def test_openbao_audit_configuration_keeps_secret_values_hmac_protected():
    config = (ROOT / "deploy/openbao/audit.hcl.example").read_text(encoding="utf-8")
    assert 'file_path = "/var/log/openbao/inboxpilot-audit.jsonl"' in config
    assert 'format    = "json"' in config
    assert 'log_raw  = "false"' in config
    assert 'mode     = "0600"' in config
