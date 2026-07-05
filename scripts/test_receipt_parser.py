#!/usr/bin/env python3
"""Unit tests for FIDES receipt OCR text parsing (Part 1, no Paddle required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.ocr.receipt_parser import parse_receipt_lines, parse_vnd

COFFEE_LINES = [
    "FIDES GROW RECEIPT",
    "Synthetic demo fixture",
    "Seller: An Nhien Coffee",
    "Buyer: Office Pantry Co.",
    "Invoice: INV-2026-001",
    "Issue date: 2026-06-21",
    "Due date: 2026-06-28",
    "Description",
    "Amount",
    "Monthly coffee bean supply 18,000,000 VND",
    "Office catering package 14,000,000 VND",
    "Tax: 2,909,091 VND",
    "Total: 32,000,000 VND",
    "OCR provider: SmartReader",
    "Confidence: 0.93",
    "Generated for FIDES HackAIthon MVP",
]

SPLIT_LABEL_LINES = [
    "Seller:",
    "Bep Nha Linh",
    "Buyer:",
    "Co-working Lunch Club",
    "Invoice:",
    "INV-2026-017",
    "Issue date: 2026-06-10",
    "Due date: -",
    "Description Amount",
    "Lunch boxes and delivery 12,500,000 VND",
    "Tax: 1,136,364 VND",
    "Total: 12.500.000 VND",
]

# Paddle sometimes drops the "Total:" label and only emits the amount.
PADDLE_MISSING_TOTAL_LABEL = [
    "Seller.",
    "Nam Phuong Devices",
    "Buyer.",
    "District Repair Network",
    "Invoice:",
    "INV-2026-108",
    "Description",
    "Amount",
    "Replacement screens",
    "42,000,000 VND",
    "Tax:",
    "7,818,182 VND",
    "86,000,000 VND",
]

# Realistic OCR text lines from grow-coffee-strong.png (Seller. / split amounts).
PADDLE_COFFEE_LINES = [
    "FIDESGROW RECEIPT",
    "Synthetic de mo fixture",
    "Seller.",
    "An Nhien Coffee",
    "Buyer.",
    "Office Pantry Co.",
    "Invoice:",
    "INV-2026-001",
    "Issue date:",
    "2026-06-21",
    "Due date:",
    "2026-06-28",
    "Description",
    "Amount",
    "Monthly coffee bean supply",
    "18,000,000VND",
    "Office catering package",
    "14,000,000 VND",
    "Tax:",
    "2,909,091 VND",
    "Total:",
    "32,000,000 VND",
]


def main() -> int:
    failures: list[str] = []

    for raw, expected in [
        ("32,000,000 VND", 32_000_000),
        ("32.000.000", 32_000_000),
        ("2909091", 2_909_091),
        ("", 0),
    ]:
        got = parse_vnd(raw)
        if got != expected:
            failures.append(f"parse_vnd({raw!r}) expected {expected}, got {got}")

    coffee = parse_receipt_lines(COFFEE_LINES)
    fields = coffee.fields
    checks = {
        "seller_name": "An Nhien Coffee",
        "buyer_name": "Office Pantry Co.",
        "invoice_id": "INV-2026-001",
        "issue_date": "2026-06-21",
        "due_date": "2026-06-28",
        "tax_amount": 2_909_091,
        "total_amount": 32_000_000,
    }
    for name, expected in checks.items():
        got = getattr(fields, name)
        if got != expected:
            failures.append(f"coffee.{name}: expected {expected!r}, got {got!r}")

    if len(fields.line_items) != 2:
        failures.append(f"coffee line_items count: expected 2, got {len(fields.line_items)}")
    else:
        if fields.line_items[0].description != "Monthly coffee bean supply":
            failures.append(f"coffee item0 description: {fields.line_items[0].description!r}")
        if fields.line_items[0].amount != 18_000_000:
            failures.append(f"coffee item0 amount: {fields.line_items[0].amount}")
        if fields.line_items[1].amount != 14_000_000:
            failures.append(f"coffee item1 amount: {fields.line_items[1].amount}")

    if coffee.missing_required:
        failures.append(f"coffee missing_required: {coffee.missing_required}")
    if coffee.confidence < 0.9:
        failures.append(f"coffee confidence too low: {coffee.confidence}")

    split = parse_receipt_lines(SPLIT_LABEL_LINES)
    if split.fields.seller_name != "Bep Nha Linh":
        failures.append(f"split seller: {split.fields.seller_name!r}")
    if split.fields.invoice_id != "INV-2026-017":
        failures.append(f"split invoice: {split.fields.invoice_id!r}")
    if split.fields.total_amount != 12_500_000:
        failures.append(f"split total: {split.fields.total_amount}")
    if split.fields.due_date is not None:
        failures.append(f"split due_date should be None, got {split.fields.due_date!r}")
    if len(split.fields.line_items) != 1:
        failures.append(f"split line_items: {split.fields.line_items}")

    missing_total = parse_receipt_lines(PADDLE_MISSING_TOTAL_LABEL)
    if missing_total.fields.total_amount != 86_000_000:
        failures.append(f"missing total label: {missing_total.fields.total_amount}")
    if missing_total.missing_required:
        failures.append(f"missing total label required: {missing_total.missing_required}")

    parsed = parse_receipt_lines(PADDLE_COFFEE_LINES)
    if parsed.fields.seller_name != "An Nhien Coffee":
        failures.append(f"coffee seller: {parsed.fields.seller_name!r}")
    if parsed.fields.invoice_id != "INV-2026-001":
        failures.append(f"coffee invoice: {parsed.fields.invoice_id!r}")
    if parsed.fields.total_amount != 32_000_000:
        failures.append(f"coffee total: {parsed.fields.total_amount}")
    if parsed.fields.tax_amount != 2_909_091:
        failures.append(f"coffee tax: {parsed.fields.tax_amount}")
    if len(parsed.fields.line_items) != 2:
        failures.append(f"coffee line_items: {parsed.fields.line_items}")
    elif parsed.fields.line_items[0].amount != 18_000_000:
        failures.append(f"coffee item0 amount: {parsed.fields.line_items[0].amount}")

    empty = parse_receipt_lines(["FIDES GROW RECEIPT", "noise only"])
    if not empty.missing_required:
        failures.append("empty receipt should report missing required fields")
    if empty.confidence != 0:
        failures.append(f"empty confidence expected 0, got {empty.confidence}")

    if failures:
        print("Receipt parser tests FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Receipt parser tests passed.")
    print(
        f"coffee: invoice={fields.invoice_id} total={fields.total_amount} "
        f"items={len(fields.line_items)} confidence={coffee.confidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
