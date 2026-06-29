import pytest
from rules_engine import RulesEngine

def test_rule_overrides_ai(tmp_path):
    path = tmp_path / "rules.yaml"; path.write_text("Newsletter:\n  action: trash\n")
    assert RulesEngine(path).action_for("Newsletter", "keep") == "trash"

def test_invalid_action_is_rejected(tmp_path):
    path = tmp_path / "rules.yaml"; path.write_text("Spam:\n  action: send\n")
    with pytest.raises(ValueError): RulesEngine(path)

def test_advanced_actions_and_move_target(tmp_path):
    path = tmp_path / "rules.yaml"; path.write_text("Facture:\n  action: archive\nClient:\n  action: move\n  target: Important\nInfo:\n  action: mark_read\n")
    rules = RulesEngine(path)
    assert rules.action_for("Facture", "keep") == "archive"
    assert rules.action_for("Client", "draft") == "move"
    assert rules.target_for("Client") == "Important"
    assert rules.action_for("Info", "keep") == "mark_read"
