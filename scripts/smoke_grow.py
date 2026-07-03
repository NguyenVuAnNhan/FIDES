#!/usr/bin/env python3
"""Smoke-test FIDES Grow demo scenarios against the local analyzer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import GrowAnalyzeRequest
from backend.app.services.grow_service import analyze_invoice

DATASET_PATH = ROOT / "backend/app/data/demo_dataset.json"
FIXTURES_DIR = ROOT / "frontend/static/fixtures/receipts"

EXPECTED_BANDS = {
    "grow-coffee-strong": "strong",
    "grow-food-stall-emerging": "emerging",
    "grow-retail-late-payment": "thin_file",
    "grow-electronics-strong": "strong",
}


def main() -> int:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for record in dataset["grow_invoices"]:
        scenario_id = record["id"]
        payload = record["payload"]
        request = GrowAnalyzeRequest(**payload)
        response = analyze_invoice(request)
        expected_band = EXPECTED_BANDS.get(scenario_id)

        print(
            f"[grow] {scenario_id}: trust={response.trust_score} "
            f"band={response.credit_band} readiness={response.loan_readiness}"
        )

        if expected_band and response.credit_band != expected_band:
            failures.append(
                f"{scenario_id}: expected credit_band={expected_band}, got {response.credit_band}"
            )

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
