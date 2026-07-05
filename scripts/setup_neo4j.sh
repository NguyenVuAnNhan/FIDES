#!/usr/bin/env bash
# One-shot Neo4j setup for FIDES Grow trust graph.
# Prefers Docker Compose; falls back to Homebrew neo4j when Docker is unavailable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NEO4J_PASSWORD="${NEO4J_PASSWORD:-fides-dev-password}"
USE_BREW=false

ensure_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "==> Created .env from .env.example"
  fi
  if grep -q '^NEO4J_ENABLED=false' .env 2>/dev/null; then
    sed -i '' 's/^NEO4J_ENABLED=false/NEO4J_ENABLED=true/' .env
    echo "==> Set NEO4J_ENABLED=true in .env"
  elif ! grep -q '^NEO4J_ENABLED=true' .env 2>/dev/null; then
    printf '\nNEO4J_ENABLED=true\n' >> .env
    echo "==> Appended NEO4J_ENABLED=true to .env"
  fi
}

wait_for_neo4j() {
  echo "==> Waiting for Neo4j on bolt://localhost:7687"
  for _ in $(seq 1 60); do
    if python - <<'PY' 2>/dev/null; then
import os, sys
from pathlib import Path
root = Path(".").resolve()
sys.path.insert(0, str(root))
os.environ.setdefault("NEO4J_ENABLED", "true")
from backend.app.services.graph.neo4j_client import health_check
sys.exit(0 if health_check() else 1)
PY
      return 0
    fi
    sleep 2
  done
  echo "Neo4j did not become ready in time."
  return 1
}

start_with_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "==> Docker is installed but not running. Open Docker Desktop, then re-run this script."
    return 1
  fi
  echo "==> Starting Neo4j via Docker Compose"
  docker compose up neo4j -d
  return 0
}

start_with_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install Docker Desktop or Homebrew + neo4j."
    return 1
  fi
  USE_BREW=true
  if ! command -v neo4j >/dev/null 2>&1; then
    echo "==> Installing Neo4j via Homebrew (no Docker detected)"
    brew install neo4j
  fi
  echo "==> Configuring Neo4j password"
  neo4j-admin dbms set-initial-password "$NEO4J_PASSWORD" 2>/dev/null || true
  echo "==> Starting Neo4j service (Homebrew)"
  neo4j start || brew services start neo4j
}

ensure_env

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m pip install -q "neo4j>=5.26" 2>/dev/null || true

if start_with_docker; then
  :
elif start_with_brew; then
  :
else
  exit 1
fi

wait_for_neo4j

echo "==> Initializing graph schema"
python scripts/init_neo4j_schema.py

echo "==> Seeding demo graph data"
python scripts/seed_grow_graph.py

echo "==> Running graph smoke test"
python scripts/smoke_grow_graph.py

echo
echo "Neo4j setup complete."
if [[ "$USE_BREW" == true ]]; then
  echo "  Browser: http://localhost:7474"
  echo "  Login:   neo4j / $NEO4J_PASSWORD"
  echo "  Stop:    neo4j stop"
else
  echo "  Browser: http://localhost:7474"
  echo "  Login:   neo4j / $NEO4J_PASSWORD"
  echo "  Stop:    docker compose stop neo4j"
fi
echo "  Grow UI: use business_id biz_an_nhien_coffee (or other seeded IDs)"
