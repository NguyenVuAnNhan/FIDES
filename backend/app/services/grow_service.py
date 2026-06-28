from backend.app.models import Explanation, GrowAnalyzeRequest, GrowAnalyzeResponse


def analyze_invoice(request: GrowAnalyzeRequest) -> GrowAnalyzeResponse:
    score = 45
    explanations: list[Explanation] = []

    if request.input_mode != "manual_entry":
        explanations.append(
            Explanation(
                label="Minimal input captured",
                detail=f"Grow received this record through {request.input_mode}.",
                weight=0,
            )
        )

    if request.ocr.status == "completed":
        confidence = ""
        if request.ocr.confidence is not None:
            confidence = f" Confidence: {request.ocr.confidence:.2f}."
        explanations.append(
            Explanation(
                label="SmartReader OCR extraction",
                detail=f"Invoice fields were extracted from {request.input_source or 'an uploaded image'}.{confidence}",
                weight=0,
            )
        )

    if request.voice_entry.status == "completed":
        confidence = ""
        if request.voice_entry.confidence is not None:
            confidence = f" Confidence: {request.voice_entry.confidence:.2f}."
        explanations.append(
            Explanation(
                label="SmartVoice bookkeeping entry",
                detail=f"Vietnamese voice entry was parsed into ledger fields.{confidence}",
                weight=0,
            )
        )

    if request.invoice_total >= 20_000_000:
        score += 18
        explanations.append(
            Explanation(
                label="Meaningful revenue signal",
                detail="This invoice shows enough transaction volume to strengthen the business profile.",
                weight=18,
            )
        )

    if request.paid_on_time:
        score += 22
        explanations.append(
            Explanation(
                label="On-time payment",
                detail="The invoice is marked as paid on time, improving repayment confidence.",
                weight=22,
            )
        )
    else:
        score -= 12
        explanations.append(
            Explanation(
                label="Late payment",
                detail="Late payment weakens short-term cashflow confidence.",
                weight=12,
            )
        )

    if len(request.items) >= 2:
        score += 8
        explanations.append(
            Explanation(
                label="Structured invoice detail",
                detail="Line items make revenue easier to validate and categorize.",
                weight=8,
            )
        )

    trust_score = max(0, min(score, 100))
    monthly_revenue = request.invoice_total * 4

    if trust_score >= 75:
        credit_band = "strong"
        readiness = "ready_for_small_working_capital_offer"
        recommended_action = "Prepare a small working-capital loan offer with invoice-backed limits."
    elif trust_score >= 55:
        credit_band = "emerging"
        readiness = "needs_more_transaction_history"
        recommended_action = "Ask for two more invoices or bank-statement snapshots to improve confidence."
    else:
        credit_band = "thin_file"
        readiness = "not_ready"
        recommended_action = "Keep building invoice history before recommending credit."

    return GrowAnalyzeResponse(
        trust_score=trust_score,
        credit_band=credit_band,
        monthly_revenue_estimate=monthly_revenue,
        loan_readiness=readiness,
        explanations=explanations,
        recommended_action=recommended_action,
    )
