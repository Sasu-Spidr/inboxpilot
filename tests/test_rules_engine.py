import pytest

from rules_engine import RulesEngine


def test_rule_overrides_ai(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("Commercial:\n  action: trash\n", encoding="utf-8")
    assert RulesEngine(path).action_for("Commercial", "keep") == "trash"


def test_invalid_action_is_rejected(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("Spam:\n  action: send\n", encoding="utf-8")
    with pytest.raises(ValueError):
        RulesEngine(path)


def test_advanced_actions_and_move_target(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("À lire:\n  action: archive\nÀ répondre:\n  action: move\n  target: Important\nNotification:\n  action: mark_read\n", encoding="utf-8")
    rules = RulesEngine(path)
    assert rules.action_for("À lire", "keep") == "archive"
    assert rules.action_for("À répondre", "draft") == "move"
    assert rules.target_for("À répondre") == "Important"
    assert rules.action_for("Notification", "keep") == "mark_read"
