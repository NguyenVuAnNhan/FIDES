#!/usr/bin/env python3
"""Smoke-test FIDES Grow demo scenarios against the local analyzer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import GrowAnalyzeRequest, GrowProcessRequest
from backend.app.services.grow_pipeline_service import process_invoice
from backend.app.services.grow_service import analyze_invoice

DATASET_PATH = ROOT / "backend/app/data/demo_dataset.json"
FIXTURES_DIR = ROOT / "frontend/static/fixtures/receipts"

EXPECTED_BANDS = {
    "grow-coffee-strong": "strong",
    "grow-food-stall-emerging": "emerging",
    "grow-retail-late-payment": "thin_file",
    "grow-electronics-strong": "strong",
}


def _minimal_payload(payload: dict) -> dict:
    return {
        "business_id": payload["business_id"],
        "business_name": payload["business_name"],
        "input_mode": payload["input_mode"],
        "input_source": payload.get("input_source"),
        "invoice_id": payload["invoice_id"],
        "customer_name": payload["customer_name"],
        "invoice_total": payload["invoice_total"],
        "paid_on_time": payload["paid_on_time"],
        "items": payload.get("items", []),
    }


def main() -> int:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for record in dataset["grow_invoices"]:
        scenario_id = record["id"]
        payload = record["payload"]
        full_request = GrowAnalyzeRequest(**payload)
        full_response = analyze_invoice(full_request)

        process_response = process_invoice(GrowProcessRequest(**_minimal_payload(payload)))
        expected_band = EXPECTED_BANDS.get(scenario_id)

        print(
            f"[grow] {scenario_id}: trust={process_response.analysis.trust_score} "
            f"band={process_response.analysis.credit_band} "
            f"readiness={process_response.analysis.loan_readiness}"
        )

        if expected_band and process_response.analysis.credit_band != expected_band:
            failures.append(
                f"{scenario_id}: expected credit_band={expected_band}, "
                f"got {process_response.analysis.credit_band}"
            )

        if process_response.analysis.credit_band != full_response.credit_band:
            failures.append(
                f"{scenario_id}: pipeline band {process_response.analysis.credit_band} "
                f"!= full payload band {full_response.credit_band}"
            )

        if not process_response.request.ocr.extracted_fields and payload.get("input_mode") == "invoice_photo":
            failures.append(f"{scenario_id}: pipeline missing OCR extraction")

        input_source = payload.get("input_source", "")
        if payload.get("input_mode") == "invoice_photo" and input_source.startswith("/static/"):
            fixture_path = ROOT / "frontend/static" / input_source.removeprefix("/static/")
            if not fixture_path.exists():
                failures.append(f"{scenario_id}: missing receipt fixture {fixture_path}")

    if not FIXTURES_DIR.exists():
        failures.append(f"missing fixtures directory: {FIXTURES_DIR}")
    elif not any(FIXTURES_DIR.glob("*.png")):
        failures.append(f"no receipt PNG fixtures found in {FIXTURES_DIR}")

    if failures:
        print("\nGrow smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nGrow smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
