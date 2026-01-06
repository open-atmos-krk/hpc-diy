#!/usr/bin/env bash
set -e

[ -d venv ] || python3 -m venv ./venv
./venv/bin/pip install .

exec ./venv/bin/uvicorn cluster_control.main:app --host 0.0.0.0 --port 8000
