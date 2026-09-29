import json
from pathlib import Path

import pytest

from classifier import EmailClassifier
from evals.run_eval import (
    ReplayClient,
    evaluate_cases,
    load_cases,
    load_label_settings,
    validate_recordings,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "dataset"
LABEL_SETTINGS = ROOT / "evals" / "label_settings.yaml"
RECORDINGS = ROOT / "evals" / "recordings"
BASELINE = ROOT / "evals" / "baseline" / "report.json"
COMPARABLE_FIELDS = (
    "id",
    "expected",
    "predicted",
    "raw_model_label",
    "path",
    "status",
    "correct",
    "confidence",
    "reason",
    "technical_error",
)


def comparable(row):
    return {field: row.get(field) for field in COMPARABLE_FIELDS}


def test_committed_recordings_replay_exactly_like_the_reviewed_baseline():
    cases = load_cases(DATASET)
    validate_recordings(cases, RECORDINGS)
    settings = load_label_settings(LABEL_SETTINGS)
    classifier = EmailClassifier("", client=ReplayClient(RECORDINGS))

    actual = evaluate_cases(cases, settings, classifier)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["cases"]

    assert [comparable(row) for row in actual] == [
        comparable(row) for row in baseline
    ], (
        "Offline evaluation changed. Review the regression; if it is intentional, "
        "run a live evaluation, review its report, and update recordings/baseline "
        "in a dedicated pull request with a justification."
    )


def test_missing_recording_fails_with_the_command_to_regenerate_it(tmp_path):
    cases = load_cases(DATASET)
    first = cases[0]
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_recordings([first], tmp_path)

    message = str(exc_info.value)
    assert str(first["id"]) in message
    assert "python evals/run_eval.py --record evals/recordings" in message


def test_deterministic_rule_regression_is_detected_before_model_replay(monkeypatch):
    cases = load_cases(DATASET)
    model_case = next(
        case
        for case in cases
        if json.loads(
            (RECORDINGS / f"{case['id']}.json").read_text(encoding="utf-8")
        )["path"] == "model"
    )
    settings = load_label_settings(LABEL_SETTINGS)
    classifier = EmailClassifier("", client=ReplayClient(RECORDINGS))
    monkeypatch.setattr(
        "evals.run_eval.deterministic_classify",
        lambda subject, sender, body: {"label": settings[0]["key"]},
    )

    with pytest.raises(ValueError, match="Recorded path changed"):
        evaluate_cases([model_case], settings, classifier)
