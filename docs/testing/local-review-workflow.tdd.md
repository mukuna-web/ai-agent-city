# Local review workflow TDD evidence

## Source and user journey

This change was derived from the repository audit rather than a separate plan
file. As a local operator, I can record a named decision on a ready analysis,
persist that reviewed report, and inspect de-identified acceptance and measured
time-saved metrics without transmitting simulation data.

## RED and GREEN evidence

| Guarantee | Test target | Evidence |
| --- | --- | --- |
| A missing persisted-review API is caught before implementation | `tests/test_reporting.py` | RED: `python3 -c 'from reporting import review_report_file'` failed with the expected missing-import error. |
| A missing user-facing review command is caught before implementation | `tests/test_review_report.py` | RED: `python3 -c 'from review_report import main'` failed with the expected missing-module error. |
| A review updates the report and aggregate metrics without copying reviewer identity into metrics | `test_local_review_persists_report_and_aggregate_metrics` | GREEN in the focused 16-test run. |
| Re-reviewing one analysis replaces its metric record | `test_repeat_review_updates_metrics_instead_of_double_counting` | GREEN in the focused 16-test run. |
| Invalid or unpaired timing measurements do not mutate either artifact | `test_review_metrics_reject_invalid_time_measurements` | GREEN in the focused 16-test run. |
| The CLI records a decision and prints aggregate outcome metrics | `test_cli_reviews_local_report_and_prints_aggregate_metrics` | GREEN in the focused 16-test run. |

## Verification

- `PYTHONPATH=. .venv/bin/python -m pytest -q`: 146 passed.
- Focused branch coverage for `reporting.py` and `review_report.py`: 90.28%.
- Scoped Ruff check for changed reporting/CLI/test files: passed.
- `uv build`: source distribution and wheel built successfully.
- `.venv/bin/pip-audit`: no known vulnerabilities found.

The first editable-package runner attempt was canceled by the local filesystem
during environment creation. The RED gate was therefore captured with direct
imports, and the same test files were subsequently executed successfully after
installing the small test toolchain into the local generated environment.
