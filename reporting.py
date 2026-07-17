"""Explainable, review-gated analysis and export helpers for simulation runs."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Iterable

CSV_FIELDS = (
    "tick",
    "alive_agents",
    "avg_energy",
    "avg_reward",
    "total_coins",
    "world_resources",
)


def _delta_finding(
    *,
    key: str,
    label: str,
    first: dict[str, Any],
    last: dict[str, Any],
) -> dict[str, Any]:
    start = first[key]
    end = last[key]
    change = end - start
    direction = "increased" if change > 0 else "decreased" if change < 0 else "was stable"
    return {
        "metric": key,
        "summary": f"{label} {direction} by {abs(change):g}.",
        "calculation": f"{end:g} - {start:g} = {change:g}",
        "evidence": [
            {"tick": first["tick"], "value": start},
            {"tick": last["tick"], "value": end},
        ],
    }


def analyze_tick_history(
    history: Iterable[dict[str, Any]],
    *,
    min_ticks: int = 12,
) -> dict[str, Any]:
    """Summarize aggregate trends or abstain when the run is too short.

    Only aggregate, allowlisted fields influence the result. Names and other
    metadata are intentionally ignored so identity-only counterfactual changes
    cannot alter the findings.
    """

    rows = list(history)
    if min_ticks < 2:
        raise ValueError("min_ticks must be at least 2")
    if len(rows) < min_ticks:
        return {
            "schema_version": "1.0",
            "status": "abstained",
            "review_status": "not_reviewable",
            "reason": f"analysis requires at least {min_ticks} ticks; received {len(rows)}",
            "sample_size": len(rows),
            "metrics": {},
            "findings": [],
        }

    missing = [field for field in CSV_FIELDS if field not in rows[0] or field not in rows[-1]]
    if missing:
        return {
            "schema_version": "1.0",
            "status": "abstained",
            "review_status": "not_reviewable",
            "reason": f"required aggregate fields are missing: {', '.join(missing)}",
            "sample_size": len(rows),
            "metrics": {},
            "findings": [],
        }

    first, last = rows[0], rows[-1]
    metrics = {
        "population_change": last["alive_agents"] - first["alive_agents"],
        "coin_change": last["total_coins"] - first["total_coins"],
        "resource_change": last["world_resources"] - first["world_resources"],
        "energy_change": round(last["avg_energy"] - first["avg_energy"], 3),
        "reward_change": round(last["avg_reward"] - first["avg_reward"], 3),
    }
    findings = [
        _delta_finding(
            key="alive_agents", label="Population", first=first, last=last
        ),
        _delta_finding(
            key="total_coins", label="Aggregate coins", first=first, last=last
        ),
        _delta_finding(
            key="world_resources", label="World resources", first=first, last=last
        ),
    ]
    return {
        "schema_version": "1.0",
        "status": "ready",
        "review_status": "needs_review",
        "reason": "aggregate thresholds satisfied; human interpretation is still required",
        "sample_size": len(rows),
        "tick_range": [first["tick"], last["tick"]],
        "metrics": metrics,
        "findings": findings,
        "limitations": [
            "The simulation is synthetic and does not describe real people or cities.",
            "Aggregate trends do not establish causality.",
            "Identity metadata is excluded from the analysis calculation.",
        ],
    }


def review_analysis(
    report: dict[str, Any],
    *,
    reviewer: str,
    decision: str,
    notes: str = "",
) -> dict[str, Any]:
    """Return a reviewed copy; generated reports never approve themselves."""

    allowed = {"approved", "rejected", "changes_requested"}
    if report.get("review_status") == "not_reviewable":
        raise ValueError("abstained analyses are not reviewable")
    if decision not in allowed:
        raise ValueError(f"decision must be one of: {', '.join(sorted(allowed))}")
    if not reviewer.strip():
        raise ValueError("reviewer identity is required")

    reviewed = copy.deepcopy(report)
    reviewed["review_status"] = decision
    reviewed["review"] = {
        "reviewer": reviewer.strip(),
        "decision": decision,
        "notes": notes.strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return reviewed


def _analysis_id(report: dict[str, Any]) -> str:
    """Return a stable identifier that excludes mutable human-review fields."""

    analysis = {
        key: value
        for key, value in report.items()
        if key not in {"review", "review_status", "local_metrics"}
    }
    canonical = json.dumps(analysis, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_time_measurement(
    manual_minutes: float | None,
    assisted_minutes: float | None,
) -> None:
    if (manual_minutes is None) != (assisted_minutes is None):
        raise ValueError("manual and assisted minutes must be provided together")
    if manual_minutes is None or assisted_minutes is None:
        return
    if manual_minutes < 0 or assisted_minutes < 0:
        raise ValueError("manual and assisted minutes cannot be negative")
    if assisted_minutes > manual_minutes:
        raise ValueError("assisted minutes cannot exceed manual minutes")


def _summarize_review_records(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    decisions = [record["decision"] for record in records.values()]
    finding_count = sum(int(record["finding_count"]) for record in records.values())
    accepted_findings = sum(
        int(record["finding_count"])
        for record in records.values()
        if record["decision"] == "approved"
    )
    timed_records = [
        record
        for record in records.values()
        if record.get("manual_minutes") is not None
        and record.get("assisted_minutes") is not None
    ]
    total_saved = round(
        sum(
            float(record["manual_minutes"]) - float(record["assisted_minutes"])
            for record in timed_records
        ),
        3,
    )
    return {
        "schema_version": "1.0",
        "reviewed_reports": len(records),
        "approved_reports": decisions.count("approved"),
        "rejected_reports": decisions.count("rejected"),
        "changes_requested_reports": decisions.count("changes_requested"),
        "reviewed_findings": finding_count,
        "accepted_findings": accepted_findings,
        "finding_acceptance_rate_percent": (
            round(accepted_findings / finding_count * 100, 2) if finding_count else None
        ),
        "measured_time_reviews": len(timed_records),
        "total_analysis_minutes_saved": total_saved,
        "average_analysis_minutes_saved": (
            round(total_saved / len(timed_records), 3) if timed_records else None
        ),
        "review_records": records,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace a local JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    temporary.replace(path)


def review_report_file(
    report_path: str | Path,
    *,
    metrics_path: str | Path = "review_metrics.json",
    reviewer: str,
    decision: str,
    notes: str = "",
    manual_minutes: float | None = None,
    assisted_minutes: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Review a local report and persist de-identified aggregate workflow metrics.

    Re-reviewing the same analysis replaces its aggregate record rather than
    double-counting it. Reviewer identity and notes remain only in the reviewed
    report; the metrics artifact contains a hash plus aggregate decision/timing
    values and never sends data anywhere.
    """

    _validate_time_measurement(manual_minutes, assisted_minutes)
    report_file = Path(report_path)
    metrics_file = Path(metrics_path)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("analysis report must be a JSON object")

    reviewed = review_analysis(
        report,
        reviewer=reviewer,
        decision=decision,
        notes=notes,
    )
    records: dict[str, dict[str, Any]] = {}
    if metrics_file.exists():
        existing = json.loads(metrics_file.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or not isinstance(
            existing.get("review_records", {}), dict
        ):
            raise ValueError("review metrics must be a JSON object with review_records")
        records = copy.deepcopy(existing.get("review_records", {}))

    identifier = _analysis_id(report)
    records[identifier] = {
        "decision": decision,
        "finding_count": len(report.get("findings", [])),
        "manual_minutes": manual_minutes,
        "assisted_minutes": assisted_minutes,
    }
    metrics = _summarize_review_records(records)
    reviewed["local_metrics"] = {
        key: value for key, value in metrics.items() if key != "review_records"
    }

    _write_json(report_file, reviewed)
    _write_json(metrics_file, metrics)
    return reviewed, metrics


def export_tick_history_csv(history: Iterable[dict[str, Any]], stream: IO[str]) -> None:
    """Write only allowlisted aggregate fields to CSV."""

    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in history:
        writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
