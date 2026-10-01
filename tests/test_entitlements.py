import json
from pathlib import Path

import pytest

from client_settings import label_settings_for_classifier, scoped_settings_path
from entitlements import (
    MailboxLimitError,
    allows_advanced_rules,
    allows_automatic_actions,
    effective_tier_for_client,
    ensure_mailbox_slot,
    mailbox_limit_for_client,
)
from main import MailWorker


def write_entitlement(data_dir: Path, client_id: str, tier: str, status: str) -> None:
    directory = data_dir / "entitlements"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{client_id}.json").write_text(
        json.dumps({"tier": tier, "status": status}),
        encoding="utf-8",
    )


@pytest.mark.parametrize("tier,limit", [("free", 1), ("pro", 3), ("business", 10)])
@pytest.mark.parametrize("status", ["active", "trialing", "past_due"])
def test_entitled_statuses_keep_tier_rights(monkeypatch, tmp_path, tier, limit, status):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    write_entitlement(tmp_path, "client", tier, status)

    assert effective_tier_for_client("client") == tier
    assert mailbox_limit_for_client("client") == limit
    assert allows_automatic_actions("client") is (tier in {"pro", "business"})
    assert allows_advanced_rules("client") is (tier == "business")


@pytest.mark.parametrize("tier", ["free", "pro", "business"])
@pytest.mark.parametrize("status", ["canceled", "unpaid", "incomplete", "incomplete_expired", "paused"])
def test_non_entitled_statuses_fall_back_to_free(monkeypatch, tmp_path, tier, status):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    write_entitlement(tmp_path, "client", tier, status)

    assert effective_tier_for_client("client") == "free"
    assert mailbox_limit_for_client("client") == 1
    assert not allows_automatic_actions("client")
    assert not allows_advanced_rules("client")


def test_missing_entitlement_is_free_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert effective_tier_for_client("unknown") == "free"
    assert mailbox_limit_for_client("unknown") == 1


def test_mailbox_limit_counts_connected_tokens_across_providers(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    write_entitlement(tmp_path, "client", "free", "active")
    token = tmp_path / "tokens" / "gmail.token"
    token.parent.mkdir(parents=True)
    token.write_text("encrypted", encoding="utf-8")
    pending = {"token_file": "./data/tokens/hotmail.token"}
    client_cfg = {
        "connectors": {
            "gmail": {"accounts": [{"token_file": "./data/tokens/gmail.token"}]},
            "hotmail": {"accounts": [pending]},
        }
    }

    with pytest.raises(MailboxLimitError, match="offre Free"):
        ensure_mailbox_slot("client", client_cfg, pending)


def test_non_business_classifier_ignores_custom_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_file = scoped_settings_path("client", "gmail", "main")
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps(
            {
                "labels": [
                    {"key": "À lire", "name": "À lire", "description": "Information", "priority": 10},
                    {"key": "Courses", "name": "Courses", "description": "Achats", "priority": 5},
                ]
            }
        ),
        encoding="utf-8",
    )

    basic = label_settings_for_classifier("client", "gmail", "main", include_advanced=False)
    advanced = label_settings_for_classifier("client", "gmail", "main", include_advanced=True)
    assert "Courses" not in {label["key"] for label in basic}
    assert "Courses" in {label["key"] for label in advanced}


class FakeConnector:
    def __init__(self):
        self.trashed = []

    def trash(self, message_id):
        self.trashed.append(message_id)


def test_free_agent_blocks_automatic_actions(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    write_entitlement(tmp_path, "client", "free", "active")
    connector = FakeConnector()
    agent = object.__new__(MailWorker)

    created = agent._apply_action(
        connector,
        "gmail",
        "main",
        {"id": "message-1", "subject": "Promo", "sender": "shop@example.com", "body": "Sale"},
        "Commercial",
        "trash",
        "low",
        None,
        "client",
    )

    assert created is False
    assert connector.trashed == []


def test_pro_agent_allows_automatic_actions(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    write_entitlement(tmp_path, "client", "pro", "trialing")
    connector = FakeConnector()
    agent = object.__new__(MailWorker)

    agent._apply_action(
        connector,
        "gmail",
        "main",
        {"id": "message-1", "subject": "Promo", "sender": "shop@example.com", "body": "Sale"},
        "Commercial",
        "trash",
        "low",
        None,
        "client",
    )

    assert connector.trashed == ["message-1"]
