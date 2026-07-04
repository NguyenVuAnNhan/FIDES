from __future__ import annotations

import math

from backend.app.models import AlternativeCreditProfile, GrowAnalyzeRequest, InvoiceItem

INVOICE_FEATURE_NAMES: list[str] = [
    "paid_on_time",
    "invoice_total",
    "log_invoice_total",
    "item_count",
    "avg_line_amount",
    "tax_ratio",
    "ocr_confidence",
]

GRAPH_FEATURE_NAMES: list[str] = [
    "trust_graph_score",
    "repeat_counterparty_count",
    "verified_counterparty_count",
    "network_centrality_score",
]

FEATURE_NAMES: list[str] = INVOICE_FEATURE_NAMES + GRAPH_FEATURE_NAMES

FEATURE_REASONS: dict[str, str] = {
    "paid_on_time": "Payment timeliness is a direct repayment-quality signal.",
    "invoice_total": "Higher invoice volume strengthens the revenue evidence base.",
    "log_invoice_total": "Log-scaled revenue captures diminishing returns at very large ticket sizes.",
    "item_count": "Structured line items make revenue easier to validate and categorize.",
    "avg_line_amount": "Average line size helps detect unusually sparse or inflated invoices.",
    "tax_ratio": "Tax proportion supports invoice legitimacy and VAT consistency checks.",
    "ocr_confidence": "Higher OCR confidence increases trust in the extracted invoice evidence.",
    "trust_graph_score": "A stronger transaction graph improves confidence in real business activity.",
    "repeat_counterparty_count": "Repeat counterparties show durable buyer or supplier relationships.",
    "verified_counterparty_count": "Verified counterparties reduce identity and invoice-quality uncertainty.",
    "network_centrality_score": "Healthy network position reduces reliance on a single buyer edge.",
}


def extract_features(request: GrowAnalyzeRequest) -> dict[str, float]:
    invoice_total = request.invoice_total
    items = request.items
    item_count = len(items)
    tax_amount = _tax_amount(request, items)
    ocr_confidence = _ocr_confidence(request)

    divisor = max(item_count, 1)
    invoice_features = {
        "paid_on_time": 1.0 if request.paid_on_time else 0.0,
        "invoice_total": float(invoice_total),
        "log_invoice_total": math.log1p(invoice_total),
        "item_count": float(item_count),
        "avg_line_amount": float(invoice_total) / divisor,
        "tax_ratio": tax_amount / max(invoice_total, 1),
        "ocr_confidence": ocr_confidence,
    }
    return {**invoice_features, **_graph_features(request.alternative_credit_profile)}


def feature_vector(features: dict[str, float], names: list[str] | None = None) -> list[float]:
    active_names = names or FEATURE_NAMES
    return [features[name] for name in active_names]


def _graph_features(profile: AlternativeCreditProfile | None) -> dict[str, float]:
    if profile is None:
        return {
            "trust_graph_score": 0.0,
            "repeat_counterparty_count": 0.0,
            "verified_counterparty_count": 0.0,
            "network_centrality_score": 0.0,
        }
    return {
        "trust_graph_score": float(profile.trust_graph_score or 0.0),
        "repeat_counterparty_count": float(profile.repeat_counterparty_count),
        "verified_counterparty_count": float(profile.verified_counterparty_count),
        "network_centrality_score": float(profile.network_centrality_score or 0.0),
    }


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


def synthetic_graph_features(category: str) -> dict[str, float]:
    specs = {
        "strong_business": (0.86, 14, 9, 0.74),
        "emerging_thin_file": (0.52, 2, 0, 0.35),
        "late_payment": (0.48, 4, 1, 0.42),
        "seasonal_cashflow": (0.68, 6, 3, 0.58),
        "high_volume": (0.91, 18, 12, 0.82),
    }
    trust, repeat, verified, centrality = specs.get(category, (0.45, 1, 0, 0.3))
    return {
        "trust_graph_score": trust,
        "repeat_counterparty_count": float(repeat),
        "verified_counterparty_count": float(verified),
        "network_centrality_score": centrality,
    }
