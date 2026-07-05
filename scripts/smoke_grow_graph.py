#!/usr/bin/env python3
"""Smoke-test Grow Neo4j trust graph ingest and feature queries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import GrowProcessRequest
from backend.app.services.graph.grow_features import fetch_grow_graph_features
from backend.app.services.graph.neo4j_client import graph_available, health_check
from backend.app.services.grow_pipeline_service import process_invoice

FIXTURE = "/static/fixtures/receipts/grow-coffee-strong.png"


def main() -> int:
    if not graph_available():
        print("Neo4j disabled — skipping graph smoke test")
        return 0
    if not health_check():
        print("Neo4j not reachable — skipping graph smoke test")
        return 0

    failures: list[str] = []
    coffee = fetch_grow_graph_features("biz_an_nhien_coffee")
    print(
        f"[graph] biz_an_nhien_coffee repeat={coffee.repeat_counterparty_count} "
        f"trust={coffee.trust_graph_score}"
    )
    if coffee.repeat_counterparty_count < 2:
        failures.append("expected seeded repeat relationships for biz_an_nhien_coffee")

    thin = fetch_grow_graph_features("biz_bep_nha_linh")
    print(f"[graph] biz_bep_nha_linh repeat={thin.repeat_counterparty_count} trust={thin.trust_graph_score}")
    if coffee.trust_graph_score <= thin.trust_graph_score:
        failures.append("expected coffee trust graph stronger than food stall")

    response = process_invoice(
        GrowProcessRequest(
            business_id="biz_an_nhien_coffee",
            business_name="An Nhien Coffee",
            input_mode="invoice_photo",
            input_source=FIXTURE,
            invoice_id="INV-SMOKE-GRAPH",
            customer_name="Office Pantry Co.",
            invoice_total=0,
            paid_on_time=True,
            items=[],
        )
    )
    profile = response.request.alternative_credit_profile
    if profile is None:
        failures.append("process-invoice missing alternative_credit_profile")
    else:
        print(
            f"[graph] pipeline trust={profile.trust_graph_score} "
            f"analysis={response.analysis.trust_score} band={response.analysis.credit_band}"
        )
        if profile.repeat_counterparty_count < 2:
            failures.append("pipeline graph profile missing repeat counterparties")

    if failures:
        print("\nGrow graph smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nGrow graph smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
