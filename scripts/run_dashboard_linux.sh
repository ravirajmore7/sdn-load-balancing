#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
fi

python3 dashboard/app.py
