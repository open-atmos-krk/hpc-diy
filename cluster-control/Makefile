SHELL := /bin/bash
configure:
	[ -d venv ] || python3 -m venv ./venv
install: configure
	./venv/bin/pip install .
lint: configure
	./venv/bin/pip install ".[lint]"
	./venv/bin/ruff check $(if $(FIX),--fix) cluster_control/
	./venv/bin/mypy cluster_control/
