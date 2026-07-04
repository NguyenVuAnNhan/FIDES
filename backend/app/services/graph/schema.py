from __future__ import annotations

CONSTRAINTS = (
    "CREATE CONSTRAINT business_id IF NOT EXISTS FOR (b:Business) REQUIRE b.business_id IS UNIQUE",
    "CREATE CONSTRAINT counterparty_id IF NOT EXISTS FOR (c:Counterparty) REQUIRE c.counterparty_id IS UNIQUE",
    "CREATE CONSTRAINT invoice_id IF NOT EXISTS FOR (i:Invoice) REQUIRE i.invoice_id IS UNIQUE",
)


def init_graph_schema() -> None:
    from backend.app.services.graph.neo4j_client import run_write

    for statement in CONSTRAINTS:
        run_write(statement)
