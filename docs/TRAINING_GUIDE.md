# Operator training guide

Audience: a facilitator or analyst with basic command-line familiarity.

## 45-minute session

1. Explain what the simulation does and does not claim (5 minutes).
2. Run the seeded CLI and inspect the four generated artifacts (10 minutes).
3. Start the dashboard, pause/resume time, and open the metrics panel (10 minutes).
4. Export CSV and Print/PDF, then trace one finding back to its calculation
   evidence (10 minutes).
5. Trigger an abstention with fewer than 12 ticks, then use
   `uv run agent-city-review --help` to record a decision on a ready report and
   inspect the local aggregate metrics (10 minutes).

The operator should be able to explain why a finding appeared, distinguish a
synthetic trend from a causal claim, identify an abstention, and restart the
system without developer assistance.
