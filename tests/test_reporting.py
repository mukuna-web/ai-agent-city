"""User-visible guarantees for explainable simulation reporting."""

from __future__ import annotations

import csv
import io
import json

import pytest

from reporting import (
    analyze_tick_history,
    export_tick_history_csv,
    review_analysis,
    review_report_file,
)


def sample_history() -> list[dict[str, int | float]]:
    return [
        {
            "tick": 1,
            "alive_agents": 5,
            "avg_energy": 90.0,
            "avg_reward": 1.0,
            "total_coins": 250,
            "world_resources": 80,
        },
        {
            "tick": 2,
            "alive_agents": 5,
            "avg_energy": 85.0,
            "avg_reward": 2.0,
            "total_coins": 270,
            "world_resources": 76,
        },
        {
            "tick": 3,
            "alive_agents": 4,
            "avg_energy": 79.0,
            "avg_reward": 3.5,
            "total_coins": 295,
            "world_resources": 69,
        },
    ]


def test_analysis_abstains_when_history_is_insufficient() -> None:
    report = analyze_tick_history(sample_history()[:1], min_ticks=3)

    assert report["status"] == "abstained"
    assert report["review_status"] == "not_reviewable"
    assert "at least 3" in report["reason"]
    assert report["findings"] == []


def test_analysis_is_explainable_and_requires_human_review() -> None:
    report = analyze_tick_history(sample_history(), min_ticks=3)

    assert report["status"] == "ready"
    assert report["review_status"] == "needs_review"
    assert report["metrics"]["population_change"] == -1
    assert report["metrics"]["coin_change"] == 45
    assert report["metrics"]["resource_change"] == -11
    assert all(finding["evidence"] for finding in report["findings"])
    assert all(finding["calculation"] for finding in report["findings"])


def test_counterfactual_metadata_does_not_change_aggregate_findings() -> None:
    baseline = analyze_tick_history(sample_history(), min_ticks=3)
    counterfactual = [dict(row, agent_label="counterfactual-name") for row in sample_history()]

    changed = analyze_tick_history(counterfactual, min_ticks=3)

    assert changed["metrics"] == baseline["metrics"]
    assert changed["findings"] == baseline["findings"]


def test_csv_export_uses_a_stable_allowlisted_schema() -> None:
    stream = io.StringIO()
    export_tick_history_csv(sample_history(), stream)

    rows = list(csv.DictReader(io.StringIO(stream.getvalue())))
    assert list(rows[0]) == [
        "tick",
        "alive_agents",
        "avg_energy",
        "avg_reward",
        "total_coins",
        "world_resources",
    ]
    assert "agent_label" not in rows[0]
    assert rows[-1]["total_coins"] == "295"


def test_review_requires_identity_and_records_approval() -> None:
    report = analyze_tick_history(sample_history(), min_ticks=3)

    reviewed = review_analysis(report, reviewer="casey", decision="approved", notes="Checked")

    assert reviewed["review_status"] == "approved"
    assert reviewed["review"]["reviewer"] == "casey"
    assert reviewed["review"]["notes"] == "Checked"


@pytest.mark.parametrize("decision", ["", "maybe", "auto-approved"])
def test_review_rejects_unknown_decisions(decision: str) -> None:
    report = analyze_tick_history(sample_history(), min_ticks=3)

    with pytest.raises(ValueError, match="decision"):
        review_analysis(report, reviewer="casey", decision=decision)


def test_abstained_analysis_cannot_be_approved() -> None:
    report = analyze_tick_history([], min_ticks=3)

    with pytest.raises(ValueError, match="not reviewable"):
        review_analysis(report, reviewer="casey", decision="approved")


def test_local_review_persists_report_and_aggregate_metrics(tmp_path) -> None:
    report_path = tmp_path / "analysis_report.json"
    metrics_path = tmp_path / "review_metrics.json"
    report_path.write_text(
        json.dumps(analyze_tick_history(sample_history(), min_ticks=3)),
        encoding="utf-8",
    )

    reviewed, metrics = review_report_file(
        report_path,
        metrics_path=metrics_path,
        reviewer="Casey",
        decision="approved",
        notes="Evidence checked",
        manual_minutes=18,
        assisted_minutes=6,
    )

    persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
    persisted_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert persisted_report == reviewed
    assert reviewed["review_status"] == "approved"
    assert metrics == persisted_metrics
    assert metrics["reviewed_reports"] == 1
    assert metrics["approved_reports"] == 1
    assert metrics["finding_acceptance_rate_percent"] == 100.0
    assert metrics["measured_time_reviews"] == 1
    assert metrics["total_analysis_minutes_saved"] == 12.0
    assert metrics["average_analysis_minutes_saved"] == 12.0
    assert "Casey" not in metrics_path.read_text(encoding="utf-8")


def test_repeat_review_updates_metrics_instead_of_double_counting(tmp_path) -> None:
    report_path = tmp_path / "analysis_report.json"
    metrics_path = tmp_path / "review_metrics.json"
    report_path.write_text(
        json.dumps(analyze_tick_history(sample_history(), min_ticks=3)),
        encoding="utf-8",
    )

    review_report_file(
        report_path,
        metrics_path=metrics_path,
        reviewer="Casey",
        decision="approved",
        manual_minutes=12,
        assisted_minutes=4,
    )
    _, metrics = review_report_file(
        report_path,
        metrics_path=metrics_path,
        reviewer="Morgan",
        decision="changes_requested",
        manual_minutes=12,
        assisted_minutes=5,
    )

    assert metrics["reviewed_reports"] == 1
    assert metrics["approved_reports"] == 0
    assert metrics["changes_requested_reports"] == 1
    assert metrics["finding_acceptance_rate_percent"] == 0.0
    assert metrics["total_analysis_minutes_saved"] == 7.0


@pytest.mark.parametrize(
    ("manual_minutes", "assisted_minutes"),
    [(-1, 1), (1, -1), (4, 5), (4, None)],
)
def test_review_metrics_reject_invalid_time_measurements(
    tmp_path,
    manual_minutes: float | None,
    assisted_minutes: float | None,
) -> None:
    report_path = tmp_path / "analysis_report.json"
    metrics_path = tmp_path / "review_metrics.json"
    original = analyze_tick_history(sample_history(), min_ticks=3)
    report_path.write_text(json.dumps(original), encoding="utf-8")

    with pytest.raises(ValueError, match="minutes"):
        review_report_file(
            report_path,
            metrics_path=metrics_path,
            reviewer="Casey",
            decision="approved",
            manual_minutes=manual_minutes,
            assisted_minutes=assisted_minutes,
        )

    assert json.loads(report_path.read_text(encoding="utf-8")) == original
    assert not metrics_path.exists()
