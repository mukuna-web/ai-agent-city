# Fairness and counterfactual testing

The aggregate analysis intentionally ignores agent names and arbitrary metadata.
`tests/test_reporting.py` verifies that adding identity-only metadata leaves
metrics and findings unchanged.

This narrow invariant prevents labels from influencing aggregate reporting. It
does not establish demographic fairness because the simulator has no validated
demographic representation, real-world outcome model, or policy-use mandate.
Any future real-person or policy application requires representative data,
stakeholder-defined harm analysis, subgroup evaluation, and independent review.
