import copy
import json
from pathlib import Path

from evals.compare_reports import compare_report


ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    baseline = json.loads((ROOT / "evals" / "baseline.json").read_text(encoding="utf-8"))
    report = json.loads(
        (ROOT / "evals" / "baseline" / "report.json").read_text(encoding="utf-8")
    )
    return report, baseline


def test_reviewed_baseline_is_inside_its_tolerance():
    report, baseline = fixtures()
    assert compare_report(report, baseline) == []


def test_per_label_regression_beyond_tolerance_is_reported():
    report, baseline = fixtures()
    degraded = copy.deepcopy(report)
    label = next(iter(baseline["per_label"]))
    degraded["metrics"]["per_label"][label]["f1"] = 0.0

    regressions = compare_report(degraded, baseline)

    assert any(label in regression and "F1" in regression for regression in regressions)


def test_small_hosted_model_variation_is_tolerated():
    report, baseline = fixtures()
    varied = copy.deepcopy(report)
    label = next(iter(baseline["per_label"]))
    reference = baseline["per_label"][label]["f1"]
    tolerance = baseline["tolerance"]["f1_absolute"]
    varied["metrics"]["per_label"][label]["f1"] = reference - tolerance / 2

    assert compare_report(varied, baseline) == []
