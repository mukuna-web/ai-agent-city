"""Local command-line review workflow for AI Agent City analysis reports."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from reporting import review_report_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review a local AI Agent City report and update aggregate metrics.",
    )
    parser.add_argument("--report", default="analysis_report.json")
    parser.add_argument("--metrics", default="review_metrics.json")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument(
        "--decision",
        required=True,
        choices=("approved", "rejected", "changes_requested"),
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--manual-minutes", type=float)
    parser.add_argument("--assisted-minutes", type=float)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    reviewed, metrics = review_report_file(
        args.report,
        metrics_path=args.metrics,
        reviewer=args.reviewer,
        decision=args.decision,
        notes=args.notes,
        manual_minutes=args.manual_minutes,
        assisted_minutes=args.assisted_minutes,
    )
    public_metrics = {key: value for key, value in metrics.items() if key != "review_records"}
    print(
        json.dumps(
            {
                "review_status": reviewed["review_status"],
                "report": args.report,
                "metrics_file": args.metrics,
                "metrics": public_metrics,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
