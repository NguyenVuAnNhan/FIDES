"""Map VNPT SmartReader OCR/KIE responses into Grow OcrExtractedFields."""

from __future__ import annotations

from typing import Any

from backend.app.models import InvoiceItem, OcrExtractedFields
from backend.app.services.ocr.receipt_parser import ParseResult, parse_receipt_lines, parse_vnd


def vnpt_call_failed(response: dict[str, Any]) -> bool:
    if response.get("status") == "error":
        return True
    http_status = response.get("http_status")
    if isinstance(http_status, int) and http_status >= 400:
        return True
    provider_status = str(response.get("status", "")).upper()
    if provider_status in {"BAD_REQUEST", "ERROR", "FAIL", "FAILED", "UNAUTHORIZED"}:
        return True
    status_code = response.get("statusCode")
    if isinstance(status_code, str) and status_code.upper().startswith(("4", "5")):
        return True
    if response.get("errors"):
        return True
    message_fields = response.get("messageFields")
    return isinstance(message_fields, list) and bool(message_fields)


def lines_from_scan_response(response: dict[str, Any]) -> list[str]:
    obj = response.get("object")
    if not isinstance(obj, dict):
        return []

    lines: list[str] = []
    for key in ("lines", "paragraphs", "phrases"):
        raw = obj.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = str(item.get("text") or item.get("content") or "").strip()
            else:
                continue
            if text:
                lines.append(text)
    return lines


def parse_vat_invoice_response(response: dict[str, Any]) -> ParseResult:
    obj = response.get("object")
    if not isinstance(obj, dict):
        return _empty_parse_result()

    buyer_name = str(
        obj.get("buyer_company_name") or obj.get("buyer_name") or ""
    ).strip()
    seller_name = str(
        obj.get("seller_company_name")
        or obj.get("seller_name")
        or obj.get("provider_name")
        or ""
    ).strip()

    total_amount = parse_vnd(obj.get("grand_total_after_tax"))
    tax_amount = 0
    before_tax = parse_vnd(obj.get("grand_total_before_tax"))
    if before_tax > 0 and total_amount >= before_tax:
        tax_amount = total_amount - before_tax
    elif obj.get("tax_amount") is not None:
        tax_amount = parse_vnd(obj.get("tax_amount"))

    invoice_id = str(
        obj.get("invoice_number")
        or obj.get("invoice_id")
        or obj.get("invoice_symbol")
        or ""
    ).strip()
    issue_date = str(obj.get("invoice_date") or obj.get("issue_date") or "").strip()

    line_items = _line_items_from_details(obj.get("details"))
    fields = OcrExtractedFields(
        invoice_id=invoice_id,
        seller_name=seller_name,
        buyer_name=buyer_name,
        issue_date=issue_date,
        total_amount=total_amount,
        tax_amount=tax_amount,
        currency="VND",
        line_items=line_items,
    )

    required = ("seller_name", "buyer_name", "invoice_id", "total_amount")
    missing = [name for name in required if not _has_required(fields, name)]
    present = len(required) - len(missing)
    confidence = round(present / len(required), 2)
    if line_items:
        confidence = min(1.0, round(confidence + 0.1, 2))
    return ParseResult(fields=fields, confidence=confidence, missing_required=missing)


def parse_scan_response(response: dict[str, Any]) -> ParseResult:
    return parse_receipt_lines(lines_from_scan_response(response))


def _line_items_from_details(details: Any) -> list[InvoiceItem]:
    if not isinstance(details, list):
        return []

    items: list[InvoiceItem] = []
    for entry in details:
        if not isinstance(entry, dict):
            continue
        description = str(
            entry.get("item_name")
            or entry.get("name")
            or entry.get("description")
            or entry.get("product_name")
            or ""
        ).strip()
        amount = parse_vnd(
            entry.get("amount")
            or entry.get("total_amount")
            or entry.get("total")
            or entry.get("price")
        )
        if not description or amount <= 0:
            continue
        quantity = entry.get("quantity")
        unit_price = parse_vnd(entry.get("unit_price") or entry.get("price"))
        items.append(
            InvoiceItem(
                description=description,
                amount=amount,
                quantity=float(quantity) if quantity is not None else None,
                unit_price=unit_price if unit_price > 0 else amount,
            )
        )
    return items


def _has_required(fields: OcrExtractedFields, name: str) -> bool:
    value = getattr(fields, name)
    if isinstance(value, int):
        return value > 0
    return bool(str(value or "").strip())


def _empty_parse_result() -> ParseResult:
    return ParseResult(
        fields=OcrExtractedFields(),
        confidence=0.0,
        missing_required=["seller_name", "buyer_name", "invoice_id", "total_amount"],
    )
