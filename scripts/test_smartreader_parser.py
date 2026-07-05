#!/usr/bin/env python3
"""Unit tests for VNPT SmartReader response parsers (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.ocr.smartreader_parser import (
    lines_from_scan_response,
    parse_scan_response,
    parse_vat_invoice_response,
    vnpt_call_failed,
)

SCAN_RESPONSE = {
    "status": "SUCCESS",
    "object": {
        "lines": [
            "FIDES Grow Receipt",
            "Seller: An Nhien Coffee",
            "Buyer: Office Pantry Co.",
            "Invoice: INV-2026-001",
            "Total: 32,000,000 VND",
        ]
    },
}

VAT_RESPONSE = {
    "status": "SUCCESS",
    "object": {
        "buyer_company_name": "Office Pantry Co.",
        "buyer_name": "Office Pantry Co.",
        "seller_name": "An Nhien Coffee",
        "invoice_number": "INV-2026-001",
        "grand_total_before_tax": 29090909,
        "grand_total_after_tax": 32000000,
        "details": [
            {"item_name": "Arabica beans 50kg", "amount": 18000000},
            {"item_name": "Roasting service", "amount": 14000000},
        ],
    },
}


def main() -> int:
    failures: list[str] = []

    if vnpt_call_failed({"status": "error"}):
        print("[ok] vnpt_call_failed detects error status")
    else:
        failures.append("vnpt_call_failed should detect error status")

    lines = lines_from_scan_response(SCAN_RESPONSE)
    if len(lines) != 5:
        failures.append(f"lines_from_scan_response count: {len(lines)}")

    scan = parse_scan_response(SCAN_RESPONSE)
    if scan.fields.seller_name != "An Nhien Coffee":
        failures.append(f"scan seller: {scan.fields.seller_name!r}")
    if scan.fields.invoice_id != "INV-2026-001":
        failures.append(f"scan invoice: {scan.fields.invoice_id!r}")
    if scan.fields.total_amount != 32_000_000:
        failures.append(f"scan total: {scan.fields.total_amount}")

    vat = parse_vat_invoice_response(VAT_RESPONSE)
    if vat.fields.buyer_name != "Office Pantry Co.":
        failures.append(f"vat buyer: {vat.fields.buyer_name!r}")
    if vat.fields.total_amount != 32_000_000:
        failures.append(f"vat total: {vat.fields.total_amount}")
    if vat.fields.tax_amount != 2_909_091:
        failures.append(f"vat tax: {vat.fields.tax_amount}")
    if len(vat.fields.line_items) != 2:
        failures.append(f"vat line_items: {vat.fields.line_items}")

    if failures:
        print("\nSmartReader parser tests FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nSmartReader parser tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
