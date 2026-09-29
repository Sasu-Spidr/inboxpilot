from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "evals" / "dataset"
ALLOWED_LABELS = {"À répondre", "À traiter", "À lire", "Notification", "Commercial"}
HISTORICAL_RULES = {
    "rule-boohooman": "boohooman",
    "rule-uber-eats": "uber eats",
    "rule-product-hunt-daily": "product hunt daily",
    "rule-25-ans-aupres": "25 ans auprès",
    "rule-paper-heavy-window": "paper-heavy window",
}


def load_cases() -> list[dict]:
    cases: list[dict] = []
    for path in sorted(DATASET_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(payload, list), f"{path} must contain a YAML list"
        cases.extend(payload)
    return cases


def test_reference_dataset_is_complete_balanced_and_synthetic():
    cases = load_cases()
    assert 60 <= len(cases) <= 80

    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))

    counts = Counter(case["expected"] for case in cases)
    assert set(counts) == ALLOWED_LABELS
    assert all(counts[label] >= 10 for label in ALLOWED_LABELS)

    for case in cases:
        assert set(case) == {"id", "subject", "sender", "body", "expected", "tags", "note"}
        assert case["id"] and case["body"] and case["note"]
        assert case["expected"] in ALLOWED_LABELS
        assert case["sender"].lower().endswith(".example")
        assert isinstance(case["tags"], list) and case["tags"]


def test_each_historical_rule_has_a_positive_and_negative_control():
    cases = load_cases()
    for rule_tag, phrase in HISTORICAL_RULES.items():
        positives = [case for case in cases if rule_tag in case["tags"] and "hardcoded-positive" in case["tags"]]
        negatives = [case for case in cases if rule_tag in case["tags"] and "hardcoded-negative" in case["tags"]]
        assert len(positives) == 1, rule_tag
        assert len(negatives) == 1, rule_tag

        positive_text = "\n".join(str(positives[0][field]) for field in ("subject", "sender", "body")).lower()
        negative_text = "\n".join(str(negatives[0][field]) for field in ("subject", "sender", "body")).lower()
        assert phrase in positive_text
        assert phrase not in negative_text


def test_frozen_label_settings_match_the_dataset_labels():
    payload = yaml.safe_load((ROOT / "evals" / "label_settings.yaml").read_text(encoding="utf-8"))
    labels = payload["labels"]
    assert {label["key"] for label in labels} == ALLOWED_LABELS
    assert len(labels) == 5
    assert all(label["autoReply"] is False for label in labels)
    assert all(label["autoDelete"] is False for label in labels)
