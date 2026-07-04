#!/usr/bin/env python3
"""Apply Neo4j constraints for the Grow trust graph."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.graph.neo4j_client import graph_available, health_check
from backend.app.services.graph.schema import init_graph_schema


def main() -> int:
    if not graph_available():
        print("Neo4j is disabled. Set NEO4J_ENABLED=true in .env")
        return 1
    if not health_check():
        print("Neo4j is not reachable. Start it with: docker compose up neo4j -d")
        return 1

    init_graph_schema()
    print("[ok] Neo4j schema initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
