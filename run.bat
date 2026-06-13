@echo off
REM Creates the venv + installs dependencies if missing, then runs app.py.
cd /d "%~dp0"

if not exist "venv" (
    echo Creating virtual environment ^(first run may take a while^)...
    python -m venv venv
    venv\Scripts\python -m pip install --upgrade pip
    venv\Scripts\python -m pip install -r requirements.txt
)

venv\Scripts\python app.py
