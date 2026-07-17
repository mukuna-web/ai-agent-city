# Contributing

Use synthetic scenarios. Add a failing test before changing aggregate analysis, abstention, review, export, or simulation behavior. Run `uv sync --extra dev --extra viz`, `make verify`, and the frontend `npm ci && npm run build && npm audit`. Document any new data field, network flow, or metric assumption.
