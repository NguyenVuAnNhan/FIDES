from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.services.graph.counterparty import counterparty_id, normalize_counterparty_name
from backend.app.services.graph.neo4j_client import graph_available, run_write

UPSERT_INVOICE = """
MERGE (b:Business {business_id: $business_id})
ON CREATE SET
  b.name = $business_name,
  b.segment = $segment,
  b.first_seen_at = $now,
  b.last_seen_at = $now
ON MATCH SET
  b.name = coalesce($business_name, b.name),
  b.last_seen_at = $now
WITH b
MERGE (c:Counterparty {counterparty_id: $counterparty_id})
ON CREATE SET
  c.name = $customer_name,
  c.verified = $verified,
  c.first_seen_at = $now
ON MATCH SET
  c.name = coalesce($customer_name, c.name),
  c.verified = CASE WHEN $verified THEN true ELSE c.verified END
WITH b, c
MERGE (i:Invoice {invoice_id: $invoice_id})
ON CREATE SET
  i.total_amount = $invoice_total,
  i.currency = 'VND',
  i.issue_date = $issue_date,
  i.paid_on_time = $paid_on_time,
  i.ocr_confidence = $ocr_confidence,
  i.recorded_at = $now
ON MATCH SET
  i.total_amount = $invoice_total,
  i.issue_date = $issue_date,
  i.paid_on_time = $paid_on_time,
  i.ocr_confidence = $ocr_confidence,
  i.recorded_at = $now
MERGE (b)-[:SOLD {recorded_at: $now}]->(i)
MERGE (c)-[:BOUGHT]->(i)
WITH b, c, i
OPTIONAL MATCH (b)-[existing:REPEAT_WITH]->(c)
WITH b, c, i, existing,
     coalesce(existing.tx_count, 0) + 1 AS next_tx_count
MERGE (b)-[r:REPEAT_WITH]->(c)
SET r.tx_count = next_tx_count,
    r.last_amount = $invoice_total,
    r.last_date = $issue_date
"""


@dataclass(frozen=True)
class GrowInvoiceIngest:
    business_id: str
    business_name: str
    customer_name: str
    invoice_id: str
    invoice_total: int
    paid_on_time: bool
    issue_date: str
    ocr_confidence: float | None = None
    counterparty_verified: bool = False
    segment: str = "household_business"


def ingest_grow_invoice(payload: GrowInvoiceIngest) -> None:
    if not graph_available():
        return
    if not payload.business_id or not payload.invoice_id:
        return

    run_write(
        UPSERT_INVOICE,
        {
            "business_id": payload.business_id,
            "business_name": payload.business_name,
            "segment": payload.segment,
            "counterparty_id": counterparty_id(payload.customer_name),
            "customer_name": payload.customer_name,
            "verified": payload.counterparty_verified,
            "invoice_id": payload.invoice_id,
            "invoice_total": payload.invoice_total,
            "paid_on_time": payload.paid_on_time,
            "issue_date": payload.issue_date or datetime.now(UTC).date().isoformat(),
            "ocr_confidence": payload.ocr_confidence,
            "now": datetime.now(UTC).isoformat(),
        },
    )


def mark_counterparty_verified(customer_name: str) -> None:
    if not graph_available():
        return
    run_write(
        """
        MATCH (c:Counterparty {counterparty_id: $counterparty_id})
        SET c.verified = true
        """,
        {"counterparty_id": counterparty_id(customer_name)},
    )


def normalized_customer_name(name: str) -> str:
    return normalize_counterparty_name(name)
