#!/usr/bin/env bash
set -e

make install

exec ./venv/bin/uvicorn cluster_control.main:app --host 0.0.0.0 --port 8000
