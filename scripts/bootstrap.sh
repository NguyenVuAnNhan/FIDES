#!/usr/bin/env bash
# One-command setup (and optional run) for the FIDES MVP.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Creating virtualenv"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies"
python -m pip install -q -U pip setuptools wheel
python -m pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example"
fi

echo "==> Generating receipt fixtures"
python scripts/generate_receipt_fixtures.py

mkdir -p frontend/static/uploads/receipts
touch frontend/static/uploads/receipts/.gitkeep

echo "==> Training Grow credit model"
python scripts/train_grow_credit_model.py

echo "==> Running Grow smoke checks"
python scripts/test_receipt_parser.py
python scripts/smoke_grow_ml.py
python scripts/smoke_grow.py

if [[ "${1:-}" == "--no-run" ]]; then
  echo
  echo "Setup complete. Start the app with:"
  echo "  source .venv/bin/activate"
  echo "  uvicorn backend.app.main:app --reload"
  exit 0
fi

echo
echo "Starting FIDES on http://127.0.0.1:8000 (Ctrl+C to stop)"
exec uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
