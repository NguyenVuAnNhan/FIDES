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

echo "==> Training Grow credit model (v2 with trust graph features)"
python scripts/train_grow_credit_model.py

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "==> Starting Neo4j (optional trust graph)"
  docker compose up neo4j -d
  if grep -q '^NEO4J_ENABLED=true' .env 2>/dev/null; then
    echo "==> Initializing Neo4j schema and seed data"
    python scripts/init_neo4j_schema.py
    python scripts/seed_grow_graph.py
    echo "==> Retraining Grow credit model with graph-aware labels"
    python scripts/train_grow_credit_model.py
    python scripts/smoke_grow_graph.py
  else
    echo "==> Neo4j running; set NEO4J_ENABLED=true in .env to enable trust graph"
  fi
fi

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
