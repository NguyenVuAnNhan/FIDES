from backend.app.models import (
    GrowAnalyzeRequest,
    GrowOcrInput,
    GrowProcessRequest,
    GrowProcessResponse,
    GrowVoiceEntry,
    InvoiceItem,
    NormalizedLedgerEntry,
)
from backend.app.services.grow_service import analyze_invoice
from backend.app.services.ocr.paddle_provider import get_paddle_provider
from backend.app.services.ocr.paths import ReceiptPathError, resolve_receipt_path


class GrowOcrError(Exception):
    """Raised when receipt OCR cannot produce a usable invoice payload."""


def process_invoice(process: GrowProcessRequest) -> GrowProcessResponse:
    request = _resolve_grow_request(process)
    analysis = analyze_invoice(request)
    return GrowProcessResponse(request=request, analysis=analysis)


def _resolve_grow_request(process: GrowProcessRequest) -> GrowAnalyzeRequest:
    if process.input_mode == "invoice_photo":
        return _resolve_from_receipt_image(process)
    return _build_from_minimal(process)


def _resolve_from_receipt_image(process: GrowProcessRequest) -> GrowAnalyzeRequest:
    try:
        image_path = resolve_receipt_path(process.input_source)
    except ReceiptPathError as exc:
        raise GrowOcrError(str(exc)) from exc

    ocr = get_paddle_provider().extract(image_path)
    fields = ocr.extracted_fields
    if ocr.status != "completed" or fields is None:
        raise GrowOcrError("OCR failed to extract required invoice fields from the receipt image.")

    enriched = process.model_copy(
        update={
            "business_name": fields.seller_name or process.business_name,
            "customer_name": fields.buyer_name or process.customer_name,
            "invoice_id": fields.invoice_id or process.invoice_id,
            "invoice_total": fields.total_amount or process.invoice_total,
            "items": fields.line_items or process.items,
        }
    )
    return _build_from_minimal(enriched, ocr=ocr)


def _build_from_minimal(
    process: GrowProcessRequest,
    ocr: GrowOcrInput | None = None,
) -> GrowAnalyzeRequest:
    items = process.items or [
        InvoiceItem(
            description="Goods and services",
            amount=process.invoice_total,
            quantity=1,
            unit_price=process.invoice_total,
        )
    ]
    ocr_input = ocr if ocr is not None else GrowOcrInput(status="not_used")
    issue_date = "2026-06-28"
    confidence = None
    if ocr_input.extracted_fields and ocr_input.extracted_fields.issue_date:
        issue_date = ocr_input.extracted_fields.issue_date
    if ocr_input.status == "completed":
        confidence = ocr_input.confidence

    ledger = NormalizedLedgerEntry(
        entry_id=f"ledger_{process.invoice_id.lower().replace('-', '_')}",
        source_type=process.input_mode,
        transaction_type="sale",
        counterparty_name=process.customer_name,
        amount=process.invoice_total,
        currency="VND",
        transaction_date=issue_date,
        category="sales_revenue",
        confidence=confidence,
    )

    return GrowAnalyzeRequest(
        business_id=process.business_id,
        business_name=process.business_name,
        input_mode=process.input_mode,
        input_source=process.input_source,
        ocr=ocr_input,
        voice_entry=GrowVoiceEntry(status="not_used"),
        normalized_ledger_entry=ledger,
        cashflow_summary=None,
        cashflow_forecast=None,
        tax_summary=None,
        einvoice_status=None,
        alternative_credit_profile=None,
        capital_connection=None,
        invoice_id=process.invoice_id,
        customer_name=process.customer_name,
        invoice_total=process.invoice_total,
        paid_on_time=process.paid_on_time,
        items=items,
    )
