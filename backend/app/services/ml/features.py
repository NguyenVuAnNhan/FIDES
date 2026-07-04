from __future__ import annotations

import math

from backend.app.models import GrowAnalyzeRequest, InvoiceItem

FEATURE_NAMES: list[str] = [
    "paid_on_time",
    "invoice_total",
    "log_invoice_total",
    "item_count",
    "avg_line_amount",
    "tax_ratio",
    "ocr_confidence",
]

FEATURE_REASONS: dict[str, str] = {
    "paid_on_time": "Payment timeliness is a direct repayment-quality signal.",
    "invoice_total": "Higher invoice volume strengthens the revenue evidence base.",
    "log_invoice_total": "Log-scaled revenue captures diminishing returns at very large ticket sizes.",
    "item_count": "Structured line items make revenue easier to validate and categorize.",
    "avg_line_amount": "Average line size helps detect unusually sparse or inflated invoices.",
    "tax_ratio": "Tax proportion supports invoice legitimacy and VAT consistency checks.",
    "ocr_confidence": "Higher OCR confidence increases trust in the extracted invoice evidence.",
}


def extract_features(request: GrowAnalyzeRequest) -> dict[str, float]:
    invoice_total = request.invoice_total
    items = request.items
    item_count = len(items)
    tax_amount = _tax_amount(request, items)
    ocr_confidence = _ocr_confidence(request)

    divisor = max(item_count, 1)
    return {
        "paid_on_time": 1.0 if request.paid_on_time else 0.0,
        "invoice_total": float(invoice_total),
        "log_invoice_total": math.log1p(invoice_total),
        "item_count": float(item_count),
        "avg_line_amount": float(invoice_total) / divisor,
        "tax_ratio": tax_amount / max(invoice_total, 1),
        "ocr_confidence": ocr_confidence,
    }


def feature_vector(features: dict[str, float]) -> list[float]:
    return [features[name] for name in FEATURE_NAMES]


def _tax_amount(request: GrowAnalyzeRequest, items: list[InvoiceItem]) -> float:
    fields = request.ocr.extracted_fields
    if fields is not None and fields.tax_amount:
        return float(fields.tax_amount)
    if invoice_total := request.invoice_total:
        return float(invoice_total) / 11.0
    return sum(item.amount for item in items) / 11.0 if items else 0.0


def _ocr_confidence(request: GrowAnalyzeRequest) -> float:
    if request.ocr.status == "completed" and request.ocr.confidence is not None:
        return request.ocr.confidence
    if request.normalized_ledger_entry and request.normalized_ledger_entry.confidence is not None:
        return request.normalized_ledger_entry.confidence
    return 0.85
