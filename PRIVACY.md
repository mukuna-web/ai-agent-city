# Privacy and local-operation policy

AI Agent City is local-first. The default CLI, analysis, tests, and dashboard do
not call a model provider, analytics service, or external API. No real-person
data is required or expected.

The CSV exporter uses a fixed aggregate schema and drops extra metadata. Do not
insert names, contact details, account identifiers, or other personal data into
configuration, tick logs, screenshots, or demo fixtures. Generated JSON and CSV
files are ignored by Git and should be deleted according to the operator's local
retention policy.

The local review command stores reviewer identity and notes only in the reviewed
`analysis_report.json`. Its separate `review_metrics.json` contains a one-way
analysis identifier plus decision, finding count, and optional timing values;
it excludes reviewer identity, notes, findings, and tick data. Neither file is
transmitted by the application.

If a future adapter introduces external inference or telemetry, it must be
opt-in, document the exact fields transmitted, minimize retention, and receive a
separate security and privacy review.
