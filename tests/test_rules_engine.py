import pytest

from rules_engine import RulesEngine


def test_rule_overrides_ai(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("Newsletter:\n  action: trash\n", encoding="utf-8")
    assert RulesEngine(path).action_for("Newsletter", "keep") == "trash"


def test_invalid_action_is_rejected(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("Spam:\n  action: send\n", encoding="utf-8")
    with pytest.raises(ValueError):
        RulesEngine(path)


def test_advanced_actions_and_move_target(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("Traité:\n  action: archive\nRelance:\n  action: move\n  target: Important\nFYI:\n  action: mark_read\n", encoding="utf-8")
    rules = RulesEngine(path)
    assert rules.action_for("Traité", "keep") == "archive"
    assert rules.action_for("Relance", "draft") == "move"
    assert rules.target_for("Relance") == "Important"
    assert rules.action_for("FYI", "keep") == "mark_read"
