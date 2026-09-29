#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from classifier import (  # noqa: E402
    MIN_CONFIDENCE,
    EmailClassifier,
    canonical_label_key,
    deterministic_classify,
    parse_json_object,
)
from bao_secrets import BaoSecrets  # noqa: E402


SCHEMA_VERSION = 1
LABELS = ("À répondre", "À traiter", "À lire", "Notification", "Commercial")


def case_fingerprint(case: dict[str, Any]) -> str:
    content = {key: case[key] for key in ("id", "subject", "sender", "body", "expected")}
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_cases(dataset_dir: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(dataset_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Dataset file must contain a list: {path}")
        cases.extend(payload)
    if not cases:
        raise ValueError(f"No evaluation cases found in {dataset_dir}")
    ids = [str(case.get("id", "")) for case in cases]
    if any(not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be non-empty and unique")
    return cases


def load_label_settings(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    labels = payload.get("labels") if isinstance(payload, dict) else None
    if not isinstance(labels, list) or {item.get("key") for item in labels} != set(LABELS):
        raise ValueError(f"Frozen label settings are invalid: {path}")
    return labels


class CapturingCompletions:
    def __init__(self, owner: "CapturingClient", delegate: Any) -> None:
        self.owner = owner
        self.delegate = delegate

    def create(self, **kwargs: Any) -> Any:
        response = self.delegate.create(**kwargs)
        self.owner.last_raw_response = str(response.choices[0].message.content)
        return response


class CapturingClient:
    def __init__(self, delegate: Any) -> None:
        self.last_raw_response: str | None = None
        self.chat = SimpleNamespace(completions=CapturingCompletions(self, delegate.chat.completions))

    def prepare_case(self, case: dict[str, Any], path: str) -> None:
        self.last_raw_response = None


class ReplayCompletions:
    def __init__(self, owner: "ReplayClient") -> None:
        self.owner = owner

    def create(self, **kwargs: Any) -> Any:
        raw = self.owner.last_raw_response
        if raw is None:
            raise RuntimeError(f"Recording has no model response for {self.owner.current_case_id}")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]
        )


class ReplayClient:
    def __init__(self, recordings_dir: Path) -> None:
        self.recordings_dir = recordings_dir
        self.current_case_id = ""
        self.last_raw_response: str | None = None
        self.chat = SimpleNamespace(completions=ReplayCompletions(self))

    def prepare_case(self, case: dict[str, Any], path: str) -> None:
        self.current_case_id = str(case["id"])
        recording_path = self.recordings_dir / f"{self.current_case_id}.json"
        if not recording_path.exists():
            raise FileNotFoundError(f"Missing recording: {recording_path}")
        payload = json.loads(recording_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported recording schema for {self.current_case_id}")
        if payload.get("input_sha256") != case_fingerprint(case):
            raise ValueError(f"Recording does not match current case: {self.current_case_id}")
        if payload.get("path") != path:
            raise ValueError(f"Recorded path changed for {self.current_case_id}")
        self.last_raw_response = payload.get("raw_model_response")


def raw_model_details(raw: str, allowed_labels: set[str]) -> dict[str, Any]:
    parsed = parse_json_object(raw)
    raw_label = str(parsed.get("libelle") or parsed.get("label") or "").strip()
    canonical_label = canonical_label_key(raw_label)
    if canonical_label not in allowed_labels:
        raise ValueError(f"unknown_label:{raw_label or '<empty>'}")
    raw_confidence = parsed.get("confiance", parsed.get("confidence"))
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_confidence:{raw_confidence}") from exc
    if not 0 <= confidence <= 1:
        raise ValueError(f"invalid_confidence:{confidence}")
    return {
        "raw_label": canonical_label,
        "confidence": confidence,
        "reason": str(parsed.get("raison") or parsed.get("reason") or "").strip(),
    }


def technical_error_kind(exc: Exception, raw: str | None) -> str:
    if raw is not None:
        try:
            raw_model_details(raw, set(LABELS))
        except json.JSONDecodeError:
            return "invalid_json"
        except ValueError as detail:
            message = str(detail)
            if message.startswith("unknown_label:"):
                return "unknown_label"
            if message.startswith("invalid_confidence:"):
                return "invalid_confidence"
            if "No JSON object found" in message:
                return "invalid_json"
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return "api_error"
    message = str(exc).lower()
    if any(token in message for token in ("connection", "timeout", "rate limit", "api")):
        return "api_error"
    return "classification_error"


def write_recording(
    recordings_dir: Path,
    case: dict[str, Any],
    path: str,
    raw_response: str | None,
) -> None:
    recordings_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "id": case["id"],
        "input_sha256": case_fingerprint(case),
        "path": path,
        "raw_model_response": raw_response,
    }
    target = recordings_dir / f"{case['id']}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evaluate_cases(
    cases: Iterable[dict[str, Any]],
    label_settings: list[dict[str, Any]],
    classifier: EmailClassifier,
    *,
    recordings_dir: Path | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    allowed_labels = {str(item["key"]) for item in label_settings}

    for case in cases:
        deterministic = deterministic_classify(case["subject"], case["sender"], case["body"])
        path = "deterministic" if deterministic is not None else "model"
        client = classifier.client
        if hasattr(client, "prepare_case"):
            client.prepare_case(case, path)
        started = clock()
        raw_response: str | None = None
        result: dict[str, Any] | None = None
        error: dict[str, str] | None = None
        raw_details: dict[str, Any] | None = None

        try:
            result = classifier.classify(
                case["subject"], case["sender"], case["body"], label_settings=label_settings
            )
            raw_response = getattr(client, "last_raw_response", None)
            if path == "model":
                if raw_response is None:
                    raise ValueError("missing_raw_model_response")
                raw_details = raw_model_details(raw_response, allowed_labels)
        except Exception as exc:  # Evaluation must expose and classify technical failures.
            raw_response = getattr(client, "last_raw_response", None)
            error = {"kind": technical_error_kind(exc, raw_response), "message": str(exc)}

        duration_ms = round((clock() - started) * 1000, 3)
        if error:
            status = "technical_error"
            predicted = result.get("label") if result else None
            confidence = raw_details.get("confidence") if raw_details else None
            reason = raw_details.get("reason") if raw_details else ""
        elif path == "model" and raw_details and raw_details["confidence"] < MIN_CONFIDENCE:
            status = "abstention"
            predicted = result.get("label") if result else None
            confidence = raw_details["confidence"]
            reason = raw_details["reason"] or str(result.get("reason", ""))
        else:
            status = "classified"
            predicted = result.get("label") if result else None
            confidence = (
                raw_details["confidence"]
                if raw_details
                else float(result.get("confidence", 0)) if result else None
            )
            reason = str(result.get("reason", "")) if result else ""

        row = {
            "id": case["id"],
            "expected": case["expected"],
            "predicted": predicted,
            "raw_model_label": raw_details.get("raw_label") if raw_details else None,
            "path": path,
            "status": status,
            "correct": status == "classified" and predicted == case["expected"],
            "confidence": confidence,
            "reason": reason,
            "duration_ms": duration_ms,
            "technical_error": error,
        }
        results.append(row)
        if recordings_dir is not None:
            write_recording(recordings_dir, case, path, raw_response)

    return results


def safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    classified = [row for row in results if row["status"] == "classified"]
    matrix = {expected: {predicted: 0 for predicted in LABELS} for expected in LABELS}
    for row in classified:
        if row["expected"] in matrix and row["predicted"] in matrix[row["expected"]]:
            matrix[row["expected"]][row["predicted"]] += 1

    per_label: dict[str, dict[str, Any]] = {}
    for label in LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[expected][label] for expected in LABELS if expected != label)
        fn = sum(matrix[label][predicted] for predicted in LABELS if predicted != label)
        precision = safe_ratio(tp, tp + fp)
        recall = safe_ratio(tp, tp + fn)
        f1 = round(2 * precision * recall / (precision + recall), 6) if precision + recall else 0.0
        per_label[label] = {
            "support": sum(1 for row in results if row["expected"] == label),
            "classified_support": sum(matrix[label].values()),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    per_path: dict[str, dict[str, Any]] = {}
    for path in ("deterministic", "model"):
        rows = [row for row in results if row["path"] == path]
        per_path[path] = {
            "total": len(rows),
            "correct": sum(bool(row["correct"]) for row in rows),
            "accuracy": safe_ratio(sum(bool(row["correct"]) for row in rows), len(rows)),
            "abstentions": sum(row["status"] == "abstention" for row in rows),
            "technical_errors": sum(row["status"] == "technical_error" for row in rows),
        }

    status_counts = Counter(row["status"] for row in results)
    technical_kinds = Counter(
        row["technical_error"]["kind"]
        for row in results
        if row["technical_error"] is not None
    )
    return {
        "summary": {
            "total": len(results),
            "classified": status_counts["classified"],
            "correct": sum(bool(row["correct"]) for row in results),
            "strict_accuracy": safe_ratio(sum(bool(row["correct"]) for row in results), len(results)),
            "classified_accuracy": safe_ratio(
                sum(bool(row["correct"]) for row in classified), len(classified)
            ),
            "abstentions": status_counts["abstention"],
            "abstention_rate": safe_ratio(status_counts["abstention"], len(results)),
            "technical_errors": status_counts["technical_error"],
            "technical_error_rate": safe_ratio(status_counts["technical_error"], len(results)),
            "technical_error_kinds": dict(sorted(technical_kinds.items())),
        },
        "per_path": per_path,
        "per_label": per_label,
        "confusion_matrix": matrix,
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    summary = metrics["summary"]
    lines = [
        "# Rapport d'évaluation InboxPilot",
        "",
        f"- Modèle : `{report['model']}`",
        f"- Cas : **{summary['total']}**",
        f"- Justesse stricte : **{summary['strict_accuracy']:.2%}**",
        f"- Abstentions : **{summary['abstentions']}** ({summary['abstention_rate']:.2%})",
        f"- Erreurs techniques : **{summary['technical_errors']}** ({summary['technical_error_rate']:.2%})",
        "",
        "## Résultats par chemin",
        "",
        "| Chemin | Cas | Corrects | Justesse | Abstentions | Erreurs techniques |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for path in ("deterministic", "model"):
        row = metrics["per_path"][path]
        lines.append(
            f"| {path} | {row['total']} | {row['correct']} | {row['accuracy']:.2%} | "
            f"{row['abstentions']} | {row['technical_errors']} |"
        )

    lines.extend([
        "",
        "## Scores par libellé",
        "",
        "| Libellé | Support | Classés | Précision | Rappel | F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for label in LABELS:
        row = metrics["per_label"][label]
        lines.append(
            f"| {label} | {row['support']} | {row['classified_support']} | "
            f"{row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |"
        )

    lines.extend(["", "## Matrice de confusion", ""])
    lines.append("| Attendu \\ Obtenu | " + " | ".join(LABELS) + " |")
    lines.append("|---|" + "---:|" * len(LABELS))
    for expected in LABELS:
        counts = [str(metrics["confusion_matrix"][expected][predicted]) for predicted in LABELS]
        lines.append(f"| {expected} | " + " | ".join(counts) + " |")

    failures = report["failures"]
    lines.extend(["", "## Échecs détaillés", ""])
    if not failures:
        lines.append("Aucun échec.")
    else:
        for row in failures:
            confidence = "—" if row["confidence"] is None else f"{row['confidence']:.3f}"
            obtained = row["predicted"] or "—"
            error = row["technical_error"]
            detail = f" Erreur : `{error['kind']}` — {error['message']}" if error else ""
            lines.extend([
                f"### `{row['id']}`",
                "",
                f"- Attendu : **{row['expected']}**",
                f"- Obtenu : **{obtained}**",
                f"- Statut : `{row['status']}`",
                f"- Chemin : `{row['path']}`",
                f"- Confiance : {confidence}",
                f"- Raison : {row['reason'] or '—'}{detail}",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def build_report(results: list[dict[str, Any]], *, model: str, dataset_dir: Path) -> dict[str, Any]:
    failures = [row for row in results if not row["correct"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "dataset": str(dataset_dir),
        "confidence_threshold": MIN_CONFIDENCE,
        "metrics": compute_metrics(results),
        "failures": failures,
        "cases": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Évalue le classement InboxPilot.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals" / "dataset")
    parser.add_argument("--label-settings", type=Path, default=ROOT / "evals" / "label_settings.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "evals" / "reports")
    parser.add_argument("--model", default=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
    parser.add_argument(
        "--record",
        nargs="?",
        const=ROOT / "evals" / "recordings",
        type=Path,
        help="Enregistre les réponses brutes, éventuellement dans le dossier indiqué.",
    )
    parser.add_argument("--replay", type=Path, help="Rejoue des réponses précédemment enregistrées.")
    args = parser.parse_args(argv)
    if args.record and args.replay:
        parser.error("--record and --replay cannot be used together")
    return args


def load_groq_api_key() -> str:
    """Read the live-evaluation key through the worker OpenBao agent."""

    value = str(BaoSecrets().get("GROQ_API_KEY")).strip()
    if not value:
        raise RuntimeError("OpenBao returned an empty GROQ_API_KEY")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cases = load_cases(args.dataset)
    label_settings = load_label_settings(args.label_settings)

    if args.replay:
        client: Any = ReplayClient(args.replay)
        classifier = EmailClassifier("", model=args.model, client=client)
    else:
        api_key = load_groq_api_key()
        live_classifier = EmailClassifier(api_key, model=args.model)
        client = CapturingClient(live_classifier.client)
        classifier = EmailClassifier("", model=args.model, client=client)

    results = evaluate_cases(
        cases,
        label_settings,
        classifier,
        recordings_dir=args.record,
    )
    report = build_report(results, model=args.model, dataset_dir=args.dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "report.json"
    markdown_path = args.output_dir / "report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Markdown report: {markdown_path}")
    print(f"JSON report: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
