#!/usr/bin/env python3
"""Seed Grow trust graph history in Neo4j from demo business profiles."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.graph.grow_features import fetch_grow_graph_features
from backend.app.services.graph.grow_ingest import GrowInvoiceIngest, ingest_grow_invoice, mark_counterparty_verified
from backend.app.services.graph.neo4j_client import graph_available, health_check
from backend.app.services.graph.schema import init_graph_schema

DEMO_DATASET = ROOT / "backend/app/data/demo_dataset.json"

SEED_PROFILES = {
    "biz_an_nhien_coffee": {
        "business_name": "An Nhien Coffee",
        "segment": "household_business",
        "history_invoices": 18,
        "repeat_buyers": [
            ("Office Pantry Co.", True),
            ("District Cafe Group", True),
            ("Hotel Sunrise", True),
            ("Co-working Lunch Club", False),
        ],
        "one_off_buyers": 4,
    },
    "biz_bep_nha_linh": {
        "business_name": "Bep Nha Linh",
        "segment": "household_business",
        "history_invoices": 6,
        "repeat_buyers": [("Co-working Lunch Club", False)],
        "one_off_buyers": 3,
    },
    "biz_thanh_tam_mini_mart": {
        "business_name": "Thanh Tam Mini Mart",
        "segment": "household_business",
        "history_invoices": 10,
        "repeat_buyers": [("Local Wholesale Buyer", False), ("Corner Store Chain", False)],
        "one_off_buyers": 5,
    },
    "biz_nam_phuong_devices": {
        "business_name": "Nam Phuong Devices",
        "segment": "SME",
        "history_invoices": 22,
        "repeat_buyers": [
            ("Tech Retail Hub", True),
            ("Mobile World Partner", True),
            ("Enterprise IT Co.", True),
            ("Repair Chain North", True),
        ],
        "one_off_buyers": 3,
    },
}


def main() -> int:
    if not graph_available():
        print("Neo4j is disabled. Set NEO4J_ENABLED=true in .env")
        return 1
    if not health_check():
        print("Neo4j is not reachable. Start it with: docker compose up neo4j -d")
        return 1

    init_graph_schema()
    rng = random.Random(20260628)

    for business_id, profile in SEED_PROFILES.items():
        _seed_business_history(rng, business_id, profile)
        features = fetch_grow_graph_features(business_id)
        print(
            f"[seed] {business_id}: repeat={features.repeat_counterparty_count} "
            f"verified={features.verified_counterparty_count} trust={features.trust_graph_score}"
        )

    _seed_demo_current_invoices(rng)
    print("[ok] Grow graph seed complete")
    return 0


def _seed_business_history(rng: random.Random, business_id: str, profile: dict) -> None:
    invoice_index = 1
    for buyer_name, verified in profile["repeat_buyers"]:
        repeats = max(2, profile["history_invoices"] // max(1, len(profile["repeat_buyers"])))
        for _ in range(repeats):
            _ingest(
                rng,
                business_id=business_id,
                business_name=profile["business_name"],
                segment=profile["segment"],
                customer_name=buyer_name,
                invoice_index=invoice_index,
                verified=verified,
            )
            invoice_index += 1
        if verified:
            mark_counterparty_verified(buyer_name)

    for offset in range(profile["one_off_buyers"]):
        _ingest(
            rng,
            business_id=business_id,
            business_name=profile["business_name"],
            segment=profile["segment"],
            customer_name=f"One-off Buyer {offset + 1}",
            invoice_index=invoice_index,
            verified=False,
        )
        invoice_index += 1


def _seed_demo_current_invoices(rng: random.Random) -> None:
    dataset = json.loads(DEMO_DATASET.read_text(encoding="utf-8"))
    for record in dataset["grow_invoices"]:
        payload = record["payload"]
        _ingest(
            rng,
            business_id=payload["business_id"],
            business_name=payload["business_name"],
            segment="SME" if "devices" in payload["business_id"] else "household_business",
            customer_name=payload["customer_name"],
            invoice_index=int(payload["invoice_id"].split("-")[-1]),
            verified=payload["business_id"] in {"biz_an_nhien_coffee", "biz_nam_phuong_devices"},
            invoice_total=payload["invoice_total"],
            paid_on_time=payload["paid_on_time"],
            invoice_id=payload["invoice_id"],
        )


def _ingest(
    rng: random.Random,
    *,
    business_id: str,
    business_name: str,
    segment: str,
    customer_name: str,
    invoice_index: int,
    verified: bool,
    invoice_total: int | None = None,
    paid_on_time: bool = True,
    invoice_id: str | None = None,
) -> None:
    amount = invoice_total or rng.randint(8_000_000, 45_000_000)
    ingest_grow_invoice(
        GrowInvoiceIngest(
            business_id=business_id,
            business_name=business_name,
            customer_name=customer_name,
            invoice_id=invoice_id or f"SEED-{business_id}-{invoice_index:04d}",
            invoice_total=amount,
            paid_on_time=paid_on_time,
            issue_date=f"2026-0{(invoice_index % 6) + 1:01d}-15",
            ocr_confidence=round(rng.uniform(0.82, 0.98), 2),
            counterparty_verified=verified,
            segment=segment,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
