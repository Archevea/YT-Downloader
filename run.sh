#!/usr/bin/env bash
# Creates the venv + installs dependencies if missing, then runs app.py.
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment (first run may take a while)..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

./venv/bin/python app.py
