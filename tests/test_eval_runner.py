import json
from pathlib import Path
from types import SimpleNamespace

from classifier import EmailClassifier
from evals.run_eval import (
    ReplayClient,
    build_report,
    compute_metrics,
    deterministic_classify,
    evaluate_cases,
    load_cases,
    main,
    render_markdown,
    write_recording,
)


LABEL_SETTINGS = [
    {"key": "À répondre", "name": "À répondre", "priority": 100},
    {"key": "À traiter", "name": "À traiter", "priority": 90},
    {"key": "À lire", "name": "À lire", "priority": 70},
    {"key": "Notification", "name": "Notification", "priority": 50},
    {"key": "Commercial", "name": "Commercial", "priority": 30},
]


def raw(label="À lire", confidence=0.9, reason="Synthetic reason"):
    return json.dumps(
        {
            "libelle": label,
            "urgence": "normale",
            "confiance": confidence,
            "raison": reason,
            "expediteur_automatique": False,
        },
        ensure_ascii=False,
    )


class CaseCompletions:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        value = self.owner.responses[self.owner.case_id]
        if isinstance(value, Exception):
            raise value
        self.owner.last_raw_response = value
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=value))])


class CaseClient:
    def __init__(self, responses):
        self.responses = responses
        self.case_id = ""
        self.last_raw_response = None
        self.chat = SimpleNamespace(completions=CaseCompletions(self))

    def prepare_case(self, case, path):
        self.case_id = case["id"]
        self.last_raw_response = None


def case(case_id, expected, subject="Neutral subject", body="Neutral synthetic body"):
    return {
        "id": case_id,
        "subject": subject,
        "sender": "sender@sample.example",
        "body": body,
        "expected": expected,
        "tags": ["test"],
        "note": "Controlled test case",
    }


def test_runner_separates_paths_abstentions_and_technical_errors(tmp_path):
    cases = [
        case("rule", "À traiter", subject="Facture à régler"),
        case("correct", "À lire"),
        case("abstain", "À répondre"),
        case("unknown", "Commercial"),
        case("invalid", "Notification"),
    ]
    client = CaseClient(
        {
            "correct": raw("À lire", 0.95),
            "abstain": raw("À répondre", 0.4, "Uncertain"),
            "unknown": raw("Ancien libellé", 0.95),
            "invalid": "not-json",
        }
    )
    classifier = EmailClassifier("", client=client)
    results = evaluate_cases(cases, LABEL_SETTINGS, classifier, recordings_dir=tmp_path)

    by_id = {row["id"]: row for row in results}
    assert by_id["rule"]["path"] == "deterministic"
    assert by_id["rule"]["correct"] is True
    assert by_id["correct"]["status"] == "classified"
    assert by_id["abstain"]["status"] == "abstention"
    assert by_id["abstain"]["predicted"] == "À lire"
    assert by_id["abstain"]["raw_model_label"] == "À répondre"
    assert by_id["abstain"]["confidence"] == 0.4
    assert by_id["unknown"]["technical_error"]["kind"] == "unknown_label"
    assert by_id["invalid"]["technical_error"]["kind"] == "invalid_json"
    assert len(list(tmp_path.glob("*.json"))) == len(cases)

    metrics = compute_metrics(results)
    assert metrics["per_path"]["deterministic"]["total"] == 1
    assert metrics["per_path"]["model"]["total"] == 4
    assert metrics["summary"]["abstentions"] == 1
    assert metrics["summary"]["technical_errors"] == 2


def test_confusion_matrix_and_per_label_scores_are_correct():
    rows = [
        {"expected": "À répondre", "predicted": "À répondre", "status": "classified", "correct": True, "path": "model", "technical_error": None},
        {"expected": "À répondre", "predicted": "À lire", "status": "classified", "correct": False, "path": "model", "technical_error": None},
        {"expected": "À lire", "predicted": "À lire", "status": "classified", "correct": True, "path": "deterministic", "technical_error": None},
        {"expected": "À lire", "predicted": "À répondre", "status": "classified", "correct": False, "path": "model", "technical_error": None},
        {"expected": "Notification", "predicted": "À lire", "status": "abstention", "correct": False, "path": "model", "technical_error": None},
    ]
    metrics = compute_metrics(rows)

    assert metrics["confusion_matrix"]["À répondre"]["À répondre"] == 1
    assert metrics["confusion_matrix"]["À répondre"]["À lire"] == 1
    assert metrics["per_label"]["À répondre"]["precision"] == 0.5
    assert metrics["per_label"]["À répondre"]["recall"] == 0.5
    assert metrics["per_label"]["À répondre"]["f1"] == 0.5
    assert metrics["per_label"]["Notification"]["classified_support"] == 0
    assert metrics["summary"]["abstentions"] == 1


def test_recordings_are_replayable_without_model_calls(tmp_path):
    cases = [case("one", "À lire"), case("two", "Commercial", body="Generic editorial content")]
    live_client = CaseClient({"one": raw("À lire", 0.9), "two": raw("Commercial", 0.91)})
    live = EmailClassifier("", client=live_client)
    first = evaluate_cases(cases, LABEL_SETTINGS, live, recordings_dir=tmp_path)

    replay = EmailClassifier("", client=ReplayClient(tmp_path))
    second = evaluate_cases(cases, LABEL_SETTINGS, replay)
    comparable = lambda rows: [
        {key: row[key] for key in ("id", "expected", "predicted", "path", "status", "correct", "confidence", "reason")}
        for row in rows
    ]
    assert comparable(second) == comparable(first)


def test_markdown_and_json_report_are_actionable(tmp_path):
    rows = [
        {
            "id": "failed-case",
            "expected": "À répondre",
            "predicted": "À lire",
            "raw_model_label": "À lire",
            "path": "model",
            "status": "classified",
            "correct": False,
            "confidence": 0.91,
            "reason": "Synthetic reason",
            "duration_ms": 12.0,
            "technical_error": None,
        }
    ]
    report = build_report(rows, model="test-model", dataset_dir=tmp_path)
    markdown = render_markdown(report)

    assert "Matrice de confusion" in markdown
    assert "Scores par libellé" in markdown
    assert "failed-case" in markdown
    assert "Synthetic reason" in markdown
    assert report["failures"][0]["confidence"] == 0.91


def test_cli_replay_writes_markdown_and_json_without_api_key(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    dataset = root / "evals" / "dataset"
    settings = root / "evals" / "label_settings.yaml"
    recordings = tmp_path / "recordings"
    output = tmp_path / "reports"

    for item in load_cases(dataset):
        path = (
            "deterministic"
            if deterministic_classify(item["subject"], item["sender"], item["body"])
            else "model"
        )
        response = None if path == "deterministic" else raw(item["expected"], 0.9)
        write_recording(recordings, item, path, response)

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert main([
        "--dataset", str(dataset),
        "--label-settings", str(settings),
        "--output-dir", str(output),
        "--replay", str(recordings),
    ]) == 0

    payload = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert payload["metrics"]["summary"]["total"] == 70
    assert "Matrice de confusion" in (output / "report.md").read_text(encoding="utf-8")
