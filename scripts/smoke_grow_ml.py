#!/usr/bin/env python3
"""Smoke-test Grow ML credit model loading and demo fixture bands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import GrowAnalyzeRequest
from backend.app.services.graph.grow_features import build_alternative_credit_profile
from backend.app.services.grow_service import analyze_invoice
from backend.app.services.ml.credit_model import model_available

DATASET_PATH = ROOT / "backend/app/data/demo_dataset.json"

EXPECTED_BANDS = {
    "grow-coffee-strong": "strong",
    "grow-food-stall-emerging": "emerging",
    "grow-retail-late-payment": "thin_file",
    "grow-electronics-strong": "strong",
}


def _ml_ready_request(payload: dict) -> GrowAnalyzeRequest:
    """Use only OCR/invoice fields; attach Neo4j graph profile when available."""
    business_id = payload.get("business_id", "")
    profile = build_alternative_credit_profile(business_id)
    return GrowAnalyzeRequest(
        business_id=business_id,
        business_name=payload["business_name"],
        input_mode=payload.get("input_mode", "invoice_photo"),
        input_source=payload.get("input_source"),
        ocr=payload["ocr"],
        normalized_ledger_entry=payload.get("normalized_ledger_entry"),
        alternative_credit_profile=profile,
        invoice_id=payload["invoice_id"],
        customer_name=payload["customer_name"],
        invoice_total=payload["invoice_total"],
        paid_on_time=payload["paid_on_time"],
        items=payload.get("items", []),
    )


def main() -> int:
    if not model_available():
        print("Grow ML model not found. Run: python scripts/train_grow_credit_model.py")
        return 1

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for record in dataset["grow_invoices"]:
        scenario_id = record["id"]
        payload = record["payload"]
        expected_band = EXPECTED_BANDS.get(scenario_id)
        if expected_band is None:
            continue

        analysis = analyze_invoice(_ml_ready_request(payload))
        print(f"[ml] {scenario_id}: trust={analysis.trust_score} band={analysis.credit_band}")

        if analysis.credit_band != expected_band:
            failures.append(f"{scenario_id}: expected {expected_band}, got {analysis.credit_band}")

        explainability = analysis.credit_explainability
        if explainability is None:
            failures.append(f"{scenario_id}: missing credit_explainability")
        elif explainability.model_version == "grow_alt_credit_mock_v1":
            failures.append(f"{scenario_id}: still using mock explainability")
        elif not explainability.feature_contributions:
            failures.append(f"{scenario_id}: missing feature contributions")

    if failures:
        print("\nGrow ML smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nGrow ML smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
