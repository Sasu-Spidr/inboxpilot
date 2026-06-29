from __future__ import annotations
from pathlib import Path
import yaml

VALID_ACTIONS = {"keep", "trash", "draft", "archive", "mark_read", "move"}


class RulesEngine:
    def __init__(self, rules_file: str):
        self.rules_file = Path(rules_file)
        self.reload()

    def reload(self) -> None:
        with self.rules_file.open(encoding="utf-8") as fh:
            self.rules = yaml.safe_load(fh) or {}
        for label, rule in self.rules.items():
            if not isinstance(rule, dict) or rule.get("action") not in VALID_ACTIONS:
                raise ValueError(f"Invalid rule for {label}; action must be one of {sorted(VALID_ACTIONS)}")

    def action_for(self, label: str, suggested_action: str = "keep") -> str:
        return self.rules.get(label, {}).get("action", suggested_action if suggested_action in VALID_ACTIONS else "keep")

    def target_for(self, label: str) -> str | None:
        target = self.rules.get(label, {}).get("target")
        return str(target) if target else None
