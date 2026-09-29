#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def compare_report(report: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    expected_model = baseline.get("model")
    if report.get("model") != expected_model:
        return [f"Model changed: expected {expected_model}, got {report.get('model')}"]

    current_labels = report["metrics"]["per_label"]
    reference_labels = baseline["per_label"]
    default_tolerance = float(baseline["tolerance"]["f1_absolute"])
    label_tolerances = baseline["tolerance"].get("per_label_f1_absolute", {})
    regressions: list[str] = []
    for label, reference in reference_labels.items():
        if label not in current_labels:
            regressions.append(f"Missing label in report: {label}")
            continue
        current_f1 = float(current_labels[label]["f1"])
        reference_f1 = float(reference["f1"])
        tolerance = float(label_tolerances.get(label, default_tolerance))
        minimum = max(0.0, reference_f1 - tolerance)
        if current_f1 + 1e-12 < minimum:
            regressions.append(
                f"{label}: F1 {current_f1:.6f} below {minimum:.6f} "
                f"(baseline {reference_f1:.6f}, tolerance {tolerance:.6f})"
            )

    max_technical_error_rate = float(
        baseline["tolerance"]["max_technical_error_rate"]
    )
    error_rate = float(report["metrics"]["summary"]["technical_error_rate"])
    if error_rate > max_technical_error_rate + 1e-12:
        regressions.append(
            f"Technical error rate {error_rate:.6f} exceeds "
            f"{max_technical_error_rate:.6f}"
        )
    return regressions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare a live eval with its reviewed baseline.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--baseline", type=Path, default=ROOT / "evals" / "baseline.json")
    args = parser.parse_args(argv)

    regressions = compare_report(load_json(args.report), load_json(args.baseline))
    if regressions:
        print("Evaluation regression detected:")
        for regression in regressions:
            print(f"- {regression}")
        return 1
    print("Evaluation remains within the calibrated tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
