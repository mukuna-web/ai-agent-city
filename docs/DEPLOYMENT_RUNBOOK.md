# Deployment and operations runbook

## Supported mode

The supported demonstration is a local Python simulation, local WebSocket
bridge, and local Vite frontend. It is not a multi-tenant production service.

## Start

1. Install Python dependencies with `uv sync --extra dev --extra viz`.
2. Run `uv run pytest`.
3. Start `uv run python viz/ws_bridge.py`.
4. In `frontend/`, run `npm ci && npm run dev`.
5. Confirm the dashboard shows `LIVE`, ticks advance, and metrics populate.
6. Review a ready report with `uv run agent-city-review --help`; confirm the
   report decision and aggregate metrics are persisted locally.

## Health checks

- WebSocket connects at `ws://localhost:8765`.
- Population and tick values change after playback starts.
- `analysis_report.json` is either `ready/needs_review` or explicitly
  `abstained`; it must never silently contain an approved state.
- `review_metrics.json` contains aggregate records only and a repeat review does
  not increase `reviewed_reports`.

## Failure recovery

- Stop both processes and restart from the configured seed.
- Generated files are disposable. Preserve them only when needed for an audit.
- If a report is malformed or incomplete, do not approve it; rerun after fixing
  the data/configuration issue.

## Rollback

Revert to the previous tagged revision, recreate the `uv` environment, run the
tests, and restart both local processes. There is no external database migration.
