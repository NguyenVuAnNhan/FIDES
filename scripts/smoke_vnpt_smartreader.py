#!/usr/bin/env python3
"""Smoke-test VNPT SmartReader OCR on Grow receipt fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES_DIR = ROOT / "frontend/static/fixtures/receipts"
EXPECTED_FIXTURES = [
    "grow-coffee-strong.png",
    "grow-food-stall-emerging.png",
    "grow-retail-late-payment.png",
    "grow-electronics-strong.png",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test VNPT SmartReader Grow OCR.")
    parser.add_argument(
        "--fixture",
        help="Run a single fixture filename under frontend/static/fixtures/receipts/",
    )
    args = parser.parse_args()

    from backend.app.config import get_settings
    from backend.app.services.ocr.smartreader_provider import get_smartreader_provider
    from backend.app.services.vnpt_client import VnptClient

    settings = get_settings()
    client = VnptClient(settings)
    print(f"smartreader_enabled={client.smartreader_enabled} provider_mode={client.mode}")
    if not client.smartreader_enabled:
        print("FAIL: SmartReader real mode is disabled or credentials are incomplete.")
        print("Set VNPT_SMARTREADER_MODE=real and VNPT token credentials in .env")
        return 1

    if not FIXTURES_DIR.is_dir():
        print(f"Missing fixtures directory: {FIXTURES_DIR}")
        print("Run: python scripts/generate_receipt_fixtures.py")
        return 1

    provider = get_smartreader_provider()
    failures: list[str] = []
    fixtures = [args.fixture] if args.fixture else EXPECTED_FIXTURES

    print("Running SmartReader OCR on receipt fixtures...")
    for name in fixtures:
        path = FIXTURES_DIR / name
        if not path.is_file():
            failures.append(f"{name}: missing file")
            print(f"[fail] {name}: missing file")
            continue

        result = provider.extract(path)
        fields = result.extracted_fields
        seller = fields.seller_name if fields else ""
        invoice_id = fields.invoice_id if fields else ""
        total = fields.total_amount if fields else 0
        items = len(fields.line_items) if fields else 0

        print(
            f"[{result.status}] {name}: seller={seller!r} invoice={invoice_id!r} "
            f"total={total} items={items} confidence={result.confidence}"
        )

        if result.provider != "SmartReader":
            failures.append(f"{name}: provider={result.provider!r}")
        if result.status != "completed":
            failures.append(f"{name}: status={result.status}")
            continue
        if not fields:
            failures.append(f"{name}: missing extracted_fields")
            continue
        if not fields.seller_name:
            failures.append(f"{name}: empty seller_name")
        if not fields.invoice_id:
            failures.append(f"{name}: empty invoice_id")
        if fields.total_amount <= 0:
            failures.append(f"{name}: total_amount={fields.total_amount}")

    missing = provider.extract(FIXTURES_DIR / "does-not-exist.png")
    if missing.status != "failed":
        failures.append(f"missing file status expected failed, got {missing.status}")
    else:
        print("[ok] missing file returns status=failed")

    if failures:
        print("\nSmartReader OCR smoke FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nSmartReader OCR smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
