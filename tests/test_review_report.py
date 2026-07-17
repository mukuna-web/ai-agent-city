"""CLI guarantees for the local human-review workflow."""

from __future__ import annotations

import json

from reporting import analyze_tick_history
from review_report import main


def _history() -> list[dict[str, int | float]]:
    return [
        {
            "tick": tick,
            "alive_agents": 4,
            "avg_energy": 90 - tick,
            "avg_reward": tick / 2,
            "total_coins": 200 + tick,
            "world_resources": 100 - tick,
        }
        for tick in range(1, 4)
    ]


def test_cli_reviews_local_report_and_prints_aggregate_metrics(tmp_path, capsys) -> None:
    report_path = tmp_path / "analysis_report.json"
    metrics_path = tmp_path / "review_metrics.json"
    report_path.write_text(
        json.dumps(analyze_tick_history(_history(), min_ticks=3)),
        encoding="utf-8",
    )

    result = main(
        [
            "--report",
            str(report_path),
            "--metrics",
            str(metrics_path),
            "--reviewer",
            "Casey",
            "--decision",
            "approved",
            "--manual-minutes",
            "15",
            "--assisted-minutes",
            "5",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["review_status"] == "approved"
    assert output["metrics"]["finding_acceptance_rate_percent"] == 100.0
    assert output["metrics"]["total_analysis_minutes_saved"] == 10.0
    assert report_path.exists()
    assert metrics_path.exists()
