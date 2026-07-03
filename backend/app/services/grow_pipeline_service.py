from backend.app.models import (
    AlternativeCreditProfile,
    CapitalConnection,
    CashflowForecast,
    CashflowSummary,
    CreditExplainability,
    CreditFeatureContribution,
    EInvoiceStatus,
    GrowAnalyzeRequest,
    GrowOcrInput,
    GrowProcessRequest,
    GrowProcessResponse,
    GrowVoiceEntry,
    InvoiceItem,
    NormalizedLedgerEntry,
    OcrExtractedFields,
    PartnerCapitalOffer,
    SmartbotCapitalAdvice,
    TaxSummary,
    VoiceParsedFields,
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
        InvoiceItem(description="Goods and services", amount=process.invoice_total, quantity=1, unit_price=process.invoice_total)
    ]
    ocr_input = ocr if ocr is not None else _build_ocr(process, items)
    voice_entry = _build_voice(process)
    confidence = ocr_input.confidence if ocr_input.status == "completed" else voice_entry.confidence
    issue_date = (
        ocr_input.extracted_fields.issue_date
        if ocr_input.extracted_fields and ocr_input.extracted_fields.issue_date
        else "2026-06-28"
    )
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
    cashflow_summary = _build_cashflow_summary(process, confidence)
    cashflow_forecast = _build_cashflow_forecast(process)
    tax_summary = _build_tax_summary(process)
    einvoice_status = _build_einvoice_status(process)
    alternative_credit_profile = _build_alternative_credit_profile(process, items)
    capital_connection = _build_capital_connection(process, cashflow_forecast)

    return GrowAnalyzeRequest(
        business_id=process.business_id,
        business_name=process.business_name,
        input_mode=process.input_mode,
        input_source=process.input_source,
        ocr=ocr_input,
        voice_entry=voice_entry,
        normalized_ledger_entry=ledger,
        cashflow_summary=cashflow_summary,
        cashflow_forecast=cashflow_forecast,
        tax_summary=tax_summary,
        einvoice_status=einvoice_status,
        alternative_credit_profile=alternative_credit_profile,
        capital_connection=capital_connection,
        invoice_id=process.invoice_id,
        customer_name=process.customer_name,
        invoice_total=process.invoice_total,
        paid_on_time=process.paid_on_time,
        items=items,
    )


def _build_ocr(process: GrowProcessRequest, items: list[InvoiceItem]) -> GrowOcrInput:
    if process.input_mode != "invoice_photo":
        return GrowOcrInput(status="not_used")

    return GrowOcrInput(
        provider="SmartReader",
        status="completed",
        confidence=0.9,
        extracted_fields=OcrExtractedFields(
            invoice_id=process.invoice_id,
            seller_name=process.business_name,
            buyer_name=process.customer_name,
            issue_date="2026-06-28",
            due_date="2026-07-05",
            total_amount=process.invoice_total,
            tax_amount=round(process.invoice_total / 11),
            currency="VND",
            line_items=items,
        ),
    )


def _build_voice(process: GrowProcessRequest) -> GrowVoiceEntry:
    if process.input_mode != "voice_entry":
        return GrowVoiceEntry(status="not_used")

    return GrowVoiceEntry(
        provider="SmartVoice",
        status="completed",
        confidence=0.9,
        parsed_fields=VoiceParsedFields(
            transaction_type="sale",
            amount=process.invoice_total,
            description=process.customer_name,
            transaction_date="2026-06-28",
            category="sales_revenue",
        ),
    )


def _build_cashflow_summary(process: GrowProcessRequest, confidence: float | None) -> CashflowSummary:
    monthly_revenue = process.invoice_total * 4
    total_outflow = round(monthly_revenue * 0.58)
    return CashflowSummary(
        period="2026-06",
        total_inflow=monthly_revenue,
        total_outflow=total_outflow,
        net_cashflow=monthly_revenue - total_outflow,
        largest_customer=process.customer_name,
        revenue_confidence=confidence,
    )


def _build_cashflow_forecast(process: GrowProcessRequest) -> CashflowForecast:
    invoice_total = process.invoice_total
    paid_on_time = process.paid_on_time
    projected_inflow = invoice_total * (4 if paid_on_time else 3)
    projected_outflow = round(invoice_total * (3.1 if paid_on_time else 3.6))
    projected_net_cashflow = projected_inflow - projected_outflow
    minimum_cash_buffer = round(invoice_total * 0.75)
    shortfall_amount = max(0, minimum_cash_buffer - projected_net_cashflow)
    if shortfall_amount:
        liquidity_risk_level = "high" if shortfall_amount > invoice_total * 0.5 else "medium"
    else:
        liquidity_risk_level = "low"

    return CashflowForecast(
        forecast_period_days=30,
        projected_inflow=projected_inflow,
        projected_outflow=projected_outflow,
        projected_net_cashflow=projected_net_cashflow,
        minimum_cash_buffer=minimum_cash_buffer,
        liquidity_risk_level=liquidity_risk_level,
        shortfall_amount=shortfall_amount,
        shortfall_expected_date="2026-07-18" if shortfall_amount else None,
        recommended_borrowing_window="2026-07-10_to_2026-07-17" if shortfall_amount else "not_required",
        recommended_credit_amount=((shortfall_amount * 1.2 + 999_999) // 1_000_000) * 1_000_000 if shortfall_amount else 0,
        drivers=[
            "on_time_receivables" if paid_on_time else "late_receivable_risk",
            "projected_cash_buffer_gap" if shortfall_amount else "positive_cash_buffer",
            "meaningful_revenue_base" if invoice_total >= 20_000_000 else "thin_recent_revenue",
        ],
        confidence=0.74 if paid_on_time else 0.62,
    )


def _build_tax_summary(process: GrowProcessRequest) -> TaxSummary:
    monthly_revenue = process.invoice_total * 4
    total_outflow = round(monthly_revenue * 0.58)
    deductible_expenses = round(total_outflow * 0.55)
    return TaxSummary(
        period="2026-06",
        vat_estimate=round(monthly_revenue / 11),
        taxable_revenue=monthly_revenue,
        deductible_expenses=deductible_expenses,
        estimated_tax_due=max(0, round((monthly_revenue - deductible_expenses) * 0.05)),
        filing_status="draft_ready" if process.paid_on_time else "needs_review",
    )


def _build_einvoice_status(process: GrowProcessRequest) -> EInvoiceStatus:
    return EInvoiceStatus(
        status="draft_ready" if process.paid_on_time else "needs_review",
        invoice_id=process.invoice_id,
        validation_errors=[] if process.paid_on_time else ["payment_status_late"],
        compliance_notes=[
            "Required buyer and seller fields present",
            "VAT estimate generated",
            "Ledger entry linked to source document",
        ],
    )


def _build_alternative_credit_profile(
    process: GrowProcessRequest, items: list[InvoiceItem]
) -> AlternativeCreditProfile:
    invoice_total = process.invoice_total
    paid_on_time = process.paid_on_time
    has_meaningful_revenue = invoice_total >= 20_000_000
    trust_graph_score = (0.84 if has_meaningful_revenue else 0.62) if paid_on_time else 0.48
    vn_social_reputation_score = (0.78 if has_meaningful_revenue else 0.64) if paid_on_time else 0.52
    cashflow_stability_score = (0.8 if has_meaningful_revenue else 0.58) if paid_on_time else 0.42
    complaints = 0 if paid_on_time else 2
    alternative_credit_score = round(
        (trust_graph_score * 0.35 + vn_social_reputation_score * 0.3 + cashflow_stability_score * 0.35) * 100
    )

    return AlternativeCreditProfile(
        trust_graph_score=trust_graph_score,
        repeat_counterparty_count=12 if has_meaningful_revenue else 3,
        verified_counterparty_count=8 if has_meaningful_revenue else 1,
        network_centrality_score=0.68 if has_meaningful_revenue else 0.42,
        cashflow_stability_score=cashflow_stability_score,
        vn_social_reputation_score=vn_social_reputation_score,
        vn_social_mentions_30d=36 if has_meaningful_revenue else 10,
        vn_social_sentiment="positive" if paid_on_time else "mixed",
        vn_social_complaint_count_30d=complaints,
        alternative_credit_score=alternative_credit_score,
        confidence=0.76 if has_meaningful_revenue else 0.62,
        signals=[
            "on_time_payment_history" if paid_on_time else "late_payment_review",
            "repeat_buyer_relationships" if has_meaningful_revenue else "thin_network_history",
            "structured_invoice_detail" if len(items) >= 2 else "limited_invoice_detail",
        ],
        explainability=_build_credit_explainability(
            alternative_credit_score,
            trust_graph_score,
            12 if has_meaningful_revenue else 3,
            cashflow_stability_score,
            vn_social_reputation_score,
            complaints,
        ),
    )


def _build_credit_explainability(
    alternative_credit_score: int,
    trust_graph_score: float,
    repeat_counterparty_count: int,
    cashflow_stability_score: float,
    vn_social_reputation_score: float,
    complaints: int,
) -> CreditExplainability:
    contributions = [
        CreditFeatureContribution(
            feature="trust_graph_score",
            value=trust_graph_score,
            shap_value=_round_one((trust_graph_score - 0.5) * 22),
            direction="positive" if trust_graph_score >= 0.5 else "negative",
            reason="A stronger transaction graph improves confidence in real business activity.",
        ),
        CreditFeatureContribution(
            feature="repeat_counterparty_count",
            value=repeat_counterparty_count,
            shap_value=_round_one(min(repeat_counterparty_count, 18) * 0.45),
            direction="positive",
            reason="Repeat counterparties show durable buyer or supplier relationships.",
        ),
        CreditFeatureContribution(
            feature="cashflow_stability_score",
            value=cashflow_stability_score,
            shap_value=_round_one((cashflow_stability_score - 0.5) * 18),
            direction="positive" if cashflow_stability_score >= 0.5 else "negative",
            reason="Stable cashflow reduces short-term repayment uncertainty.",
        ),
        CreditFeatureContribution(
            feature="vn_social_reputation_score",
            value=vn_social_reputation_score,
            shap_value=_round_one((vn_social_reputation_score - 0.5) * 14),
            direction="positive" if vn_social_reputation_score >= 0.5 else "negative",
            reason="Positive public reputation supports business legitimacy.",
        ),
        CreditFeatureContribution(
            feature="vn_social_complaint_count_30d",
            value=complaints,
            shap_value=_round_one(complaints * -2.5),
            direction="negative" if complaints else "neutral",
            reason="Recent complaints reduce confidence and trigger review.",
        ),
    ]
    contributions.sort(key=lambda item: abs(item.shap_value), reverse=True)
    return CreditExplainability(
        baseline_score=55,
        final_score=alternative_credit_score,
        reason_codes=[item.feature for item in contributions if item.direction == "positive"][:3],
        feature_contributions=contributions,
    )


def _build_capital_connection(process: GrowProcessRequest, forecast: CashflowForecast) -> CapitalConnection:
    invoice_total = process.invoice_total
    paid_on_time = process.paid_on_time
    recommended_amount = forecast.recommended_credit_amount or min(invoice_total, 30_000_000)
    eligibility_status = (
        "prequalified" if paid_on_time and forecast.liquidity_risk_level != "high" else "needs_review"
    )
    working_capital_offer = PartnerCapitalOffer(
        offer_id=f"mock_wc_{recommended_amount}_6mo",
        partner_name="Mock Partner Bank A",
        product_type="working_capital_loan",
        max_amount=recommended_amount,
        term_months=6,
        monthly_payment_estimate=round((recommended_amount * 1.06) / 6),
        eligibility_status=eligibility_status,
        fit_score=0.84 if paid_on_time else 0.58,
        required_documents=["recent_invoices", "bank_statement_snapshot"],
        reason=(
            "Matches the projected cash-buffer gap."
            if forecast.shortfall_amount
            else "Optional working-capital line for growth inventory."
        ),
        next_step="show_prequalified_terms" if paid_on_time else "request_partner_review",
    )
    insurance_offer = PartnerCapitalOffer(
        offer_id="mock_inventory_cover_basic",
        partner_name="Mock Insurance Partner B",
        product_type="inventory_insurance",
        max_amount=round(invoice_total * 1.5),
        term_months=12,
        premium_estimate=max(250_000, round(invoice_total * 0.018)),
        eligibility_status="eligible",
        fit_score=0.56 if "positive_cash_buffer" in forecast.drivers else 0.7,
        required_documents=["inventory_photo", "recent_invoice"],
        reason="Protects stock or seasonal inventory tied to upcoming sales.",
        next_step="show_insurance_summary",
    )
    advice_message = (
        f"A short working-capital offer before {forecast.shortfall_expected_date} may cover the projected cash gap without over-borrowing."
        if forecast.shortfall_amount
        else "No urgent borrowing is required, but a small prequalified line can support planned inventory growth."
    )

    return CapitalConnection(
        status="matched",
        recommended_offer_id=working_capital_offer.offer_id,
        partner_offers=[working_capital_offer, insurance_offer],
        smartbot_advice=SmartbotCapitalAdvice(
            message=advice_message,
            confidence=forecast.confidence,
        ),
        data_sharing_scope=["business_profile", "cashflow_forecast", "recent_invoices"],
        consent_required=True,
    )


def _round_one(value: float) -> float:
    return round(value * 10) / 10
