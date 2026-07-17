# Success metrics

These metrics measure whether the tool is understandable and operable; they are
not claims about real economic outcomes.

| Metric | Definition | Initial target |
| --- | --- | --- |
| Setup time | Minutes from clean checkout to first advancing tick | <= 15 min |
| Analysis traceability | Findings for which an operator identifies the exact calculation | 100% |
| Abstention correctness | Insufficient runs that emit no findings | 100% |
| Review compliance | Ready reports published only after named review | 100% |
| Operator task success | Trainees completing start, export, explain, and restart tasks | >= 80% |
| Finding acceptance | Findings in approved reports / findings in all reviewed reports | Track; no synthetic target |
| Analysis time saved | Manual baseline minutes minus assisted analysis-and-review minutes for the same task | Track measured pairs only |

Record measured values only after a real operator session. Do not substitute
automated test results for adoption or time-saved evidence.

`uv run agent-city-review` maintains these review metrics in ignored local
`review_metrics.json`. Timing is optional because an unmeasured estimate must not
be presented as evidence. The file records no reviewer identity or finding text;
delete it to reset the aggregate measurement history.
