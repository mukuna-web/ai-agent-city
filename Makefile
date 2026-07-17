.PHONY: test coverage build verify

test:
	uv run --extra dev pytest -q

coverage:
	uv run --extra dev pytest tests/test_reporting.py --cov=reporting --cov-branch --cov-report=term-missing

build:
	uv build

verify: test coverage build
