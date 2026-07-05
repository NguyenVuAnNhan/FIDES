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
    smartreader_field_text,
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

NESTED_SCAN_RESPONSE = {
    "status": "SUCCESS",
    "object": {
        "lines": [
            {
                "type": "List",
                "cells": [
                    {"text": "FIDESGROW RECEIPT", "type": "Phrase"},
                    {"text": "Synthetic demofixture", "type": "Phrase"},
                    {"text": "An Nhien Colfee", "type": "Phrase"},
                    {"text": "Buyer: Office Pantry Co", "type": "Phrase"},
                    {"text": "INV-2026-001", "type": "Phrase"},
                    {"text": "lssue date: 2026-06-21", "type": "Phrase"},
                    {"text": "Due date: 2026-06-28", "type": "Phrase"},
                    {"text": "Description Amount", "type": "Phrase"},
                    {"text": "Monthly coffee bean supply 18,000,000 VND", "type": "Phrase"},
                    {"text": "Office catering package 14000,000 VND", "type": "Phrase"},
                    {"text": "2909,091 VND", "type": "Phrase"},
                    {"text": "32,000,000 VND", "type": "Phrase"},
                ],
            }
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

KIE_FIELD = {
    "text": "",
    "font_styles": ["normal"],
    "type": "Field",
    "bboxes": {},
    "bbox_conf_score": 1.0,
    "confidence_score": 1,
    "warnings": [],
}

KIE_VAT_RESPONSE = {
    "status": "SUCCESS",
    "object": {
        "buyer_company_name": KIE_FIELD,
        "buyer_name": KIE_FIELD,
        "seller_name": KIE_FIELD,
        "invoice_number": KIE_FIELD,
        "grand_total_after_tax": KIE_FIELD,
    },
}

KIE_VAT_WITH_TEXT = {
    "status": "SUCCESS",
    "object": {
        "buyer_company_name": {**KIE_FIELD, "text": "Office Pantry Co."},
        "seller_name": {**KIE_FIELD, "text": "An Nhien Coffee"},
        "invoice_number": {**KIE_FIELD, "text": "INV-2026-001"},
        "grand_total_after_tax": {**KIE_FIELD, "text": "32,000,000 VND"},
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

    nested_lines = lines_from_scan_response(NESTED_SCAN_RESPONSE)
    if len(nested_lines) < 10:
        failures.append(f"nested scan line count: {len(nested_lines)}")

    nested = parse_scan_response(NESTED_SCAN_RESPONSE)
    if nested.missing_required:
        failures.append(f"nested scan missing: {nested.missing_required}")
    if nested.fields.seller_name != "An Nhien Colfee":
        failures.append(f"nested seller: {nested.fields.seller_name!r}")
    if nested.fields.buyer_name != "Office Pantry Co":
        failures.append(f"nested buyer: {nested.fields.buyer_name!r}")
    if nested.fields.invoice_id != "INV-2026-001":
        failures.append(f"nested invoice: {nested.fields.invoice_id!r}")
    if nested.fields.total_amount != 32_000_000:
        failures.append(f"nested total: {nested.fields.total_amount}")
    if nested.fields.issue_date != "2026-06-21":
        failures.append(f"nested issue_date: {nested.fields.issue_date!r}")

    vat = parse_vat_invoice_response(VAT_RESPONSE)
    if vat.fields.buyer_name != "Office Pantry Co.":
        failures.append(f"vat buyer: {vat.fields.buyer_name!r}")
    if vat.fields.total_amount != 32_000_000:
        failures.append(f"vat total: {vat.fields.total_amount}")
    if vat.fields.tax_amount != 2_909_091:
        failures.append(f"vat tax: {vat.fields.tax_amount}")
    if len(vat.fields.line_items) != 2:
        failures.append(f"vat line_items: {vat.fields.line_items}")

    kie_empty = parse_vat_invoice_response(KIE_VAT_RESPONSE)
    if kie_empty.fields.seller_name:
        failures.append(f"kie empty seller should be blank: {kie_empty.fields.seller_name!r}")
    if kie_empty.fields.total_amount != 0:
        failures.append(f"kie empty total should be 0: {kie_empty.fields.total_amount}")
    if not kie_empty.missing_required:
        failures.append("kie empty response should report missing required fields")

    kie_text = parse_vat_invoice_response(KIE_VAT_WITH_TEXT)
    if kie_text.fields.seller_name != "An Nhien Coffee":
        failures.append(f"kie text seller: {kie_text.fields.seller_name!r}")
    if kie_text.fields.total_amount != 32_000_000:
        failures.append(f"kie text total: {kie_text.fields.total_amount}")
    if smartreader_field_text(KIE_FIELD) != "":
        failures.append("smartreader_field_text should unwrap empty KIE field")

    if failures:
        print("\nSmartReader parser tests FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nSmartReader parser tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
