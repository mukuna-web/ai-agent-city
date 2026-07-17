# AI Agent City

AI Agent City is a local-first economic and social simulation in which bounded
reinforcement-learning agents gather resources, work, trade, build, communicate,
and learn inside a seeded world. A Three.js dashboard streams the city state and
aggregate economic metrics in real time.

This is a synthetic simulation—not a model of real people, a policy forecast, or
an autonomous LLM society. The default engine makes no model-provider or network
calls.

## What it demonstrates

- Seeded world generation and reproducible agent behavior.
- Q-learning, replay memory, reward shaping, and knowledge sharing.
- Resource, labor, production, and marketplace systems.
- WebSocket state streaming into an interactive Three.js dashboard.
- Explainable aggregate trend reports with explicit calculations and evidence.
- CSV and browser Print/PDF export.
- Abstention when a run is too short or required metrics are missing.
- A human-review state that generated analyses cannot approve themselves out of.
- Counterfactual tests proving identity-only metadata does not alter aggregates.

## Quick start

Requirements: Python 3.12+, Node.js 20+, and `uv`.

```bash
uv sync --extra dev --extra viz
uv run pytest
uv run python main.py
```

The CLI produces ignored local artifacts:

```text
simulation_result.json   full final snapshot
tick_log.json            per-tick aggregate trace
simulation_metrics.csv   allowlisted aggregate export
analysis_report.json     explainable, review-gated findings
review_metrics.json      de-identified local review and time-saved aggregates
```

## Interactive dashboard

Start the simulation bridge:

```bash
uv run python viz/ws_bridge.py
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL displayed in the terminal. The dashboard provides city-state
inspection, economic charts, CSV download, and Print/PDF export.

## Explainability and review

`reporting.analyze_tick_history` derives every finding from an allowlisted
aggregate field and records its start value, end value, and calculation. It
returns `abstained` until the configured minimum number of ticks is available.
Ready reports start in `needs_review`; only an identified reviewer can mark a
copy `approved`, `rejected`, or `changes_requested`.

Record a local decision and, when measured against the same task, optional
manual-versus-assisted timing evidence:

```bash
uv run agent-city-review \
  --report analysis_report.json \
  --reviewer "Casey" \
  --decision approved \
  --manual-minutes 18 \
  --assisted-minutes 6
```

The command updates the report in place and writes ignored
`review_metrics.json`. Re-reviewing the same analysis replaces its aggregate
record rather than inflating counts. The metrics file contains no reviewer name,
notes, simulation observations, or findings; it exposes reviewed/approved/
rejected counts, finding acceptance, and measured time saved. All work remains
on the local filesystem.

The counterfactual test suite adds identity-only metadata to every observation
and verifies that metrics and findings remain unchanged. This guards the
aggregate analysis boundary; it is not a claim of demographic fairness or real-
world validity.

## Project layout

```text
agents/       reference agent model
engine/       seeded simulation engine and world clock
economy/      market primitives
learning/     reinforcement and social learning
frontend/     Three.js and React dashboard
viz/          WebSocket/HTTP bridge
reporting.py  explainable analysis, abstention, persisted review, metrics, CSV
review_report.py  local human-review CLI
tests/        unit and integration tests
docs/         architecture, operations, training, privacy, and metrics
```

## Safety and limitations

- The generated population is synthetic and contains no real personal data.
- Local artifacts can still reveal experiment assumptions; review before sharing.
- Aggregate associations do not establish causality.
- A seeded simulator is reproducible only for the pinned code/configuration.
- The repository contains an older parallel `src/` architecture; the supported
  runnable reference path is currently the root `main.py` plus root packages.

See [PRIVACY.md](PRIVACY.md), [the deployment runbook](docs/DEPLOYMENT_RUNBOOK.md),
[the training guide](docs/TRAINING_GUIDE.md), and [the metrics plan](docs/METRICS.md).

## License

MIT.
