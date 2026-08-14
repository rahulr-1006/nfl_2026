.PHONY: venv install test lint collect collect-once clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests

collect:
	$(PY) -m src.collect.run

collect-once:
	$(PY) -m src.collect.run --once

clean:
	rm -rf $(VENV) .pytest_cache **/__pycache__
