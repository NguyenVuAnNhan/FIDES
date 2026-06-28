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

    if request.normalized_ledger_entry:
        explanations.append(
            Explanation(
                label="Ledger entry normalized",
                detail=(
                    f"Entry {request.normalized_ledger_entry.entry_id} records "
                    f"{request.normalized_ledger_entry.amount:,} {request.normalized_ledger_entry.currency} "
                    f"as {request.normalized_ledger_entry.category}."
                ),
                weight=0,
            )
        )

    if request.cashflow_summary:
        explanations.append(
            Explanation(
                label="Cashflow summary generated",
                detail=(
                    f"{request.cashflow_summary.period}: inflow {request.cashflow_summary.total_inflow:,} VND, "
                    f"outflow {request.cashflow_summary.total_outflow:,} VND, "
                    f"net {request.cashflow_summary.net_cashflow:,} VND."
                ),
                weight=0,
            )
        )

    if request.cashflow_forecast:
        shortfall = ""
        if request.cashflow_forecast.shortfall_amount:
            shortfall = (
                f" Expected shortfall {request.cashflow_forecast.shortfall_amount:,} VND"
                f" on {request.cashflow_forecast.shortfall_expected_date or 'the forecast horizon'}."
            )
        explanations.append(
            Explanation(
                label="Cashflow forecast",
                detail=(
                    f"{request.cashflow_forecast.forecast_period_days}-day liquidity risk is "
                    f"{request.cashflow_forecast.liquidity_risk_level}; projected net cashflow "
                    f"{request.cashflow_forecast.projected_net_cashflow:,} VND; recommended borrowing window "
                    f"{request.cashflow_forecast.recommended_borrowing_window or 'not required'}."
                    f"{shortfall}"
                ),
                weight=0,
            )
        )

    if request.tax_summary:
        explanations.append(
            Explanation(
                label="Tax draft prepared",
                detail=(
                    f"{request.tax_summary.period}: taxable revenue {request.tax_summary.taxable_revenue:,} VND, "
                    f"VAT estimate {request.tax_summary.vat_estimate:,} VND, "
                    f"filing status {request.tax_summary.filing_status}."
                ),
                weight=0,
            )
        )

    if request.einvoice_status:
        status_detail = f"e-invoice status {request.einvoice_status.status}"
        if request.einvoice_status.validation_errors:
            status_detail += f"; errors: {', '.join(request.einvoice_status.validation_errors)}"
        explanations.append(
            Explanation(
                label="E-invoice compliance status",
                detail=status_detail + ".",
                weight=0,
            )
        )

    if request.alternative_credit_profile:
        alternative_credit_weight = _alternative_credit_weight(request)
        profile = request.alternative_credit_profile
        details = []
        if profile.alternative_credit_score is not None:
            details.append(f"alternative score {profile.alternative_credit_score}/100")
        if profile.trust_graph_score is not None:
            details.append(f"trust graph {profile.trust_graph_score:.2f}")
        if profile.vn_social_reputation_score is not None:
            details.append(f"vnSocial reputation {profile.vn_social_reputation_score:.2f}")
        details.append(f"{profile.repeat_counterparty_count} repeat counterparty relationship(s)")
        if profile.vn_social_complaint_count_30d:
            details.append(f"{profile.vn_social_complaint_count_30d} recent complaint(s)")
        score += alternative_credit_weight
        explanations.append(
            Explanation(
                label="Alternative credit profile",
                detail=", ".join(details) + ".",
                weight=abs(alternative_credit_weight),
            )
        )
        if profile.explainability:
            top_contributions = profile.explainability.feature_contributions[:3]
            contribution_detail = "; ".join(
                f"{item.feature} {item.shap_value:+.1f}" for item in top_contributions
            )
            if not contribution_detail:
                contribution_detail = "No feature contributions supplied"
            explanations.append(
                Explanation(
                    label="Explainable credit model",
                    detail=(
                        f"{profile.explainability.model_type} "
                        f"{profile.explainability.model_version}: baseline "
                        f"{profile.explainability.baseline_score}, final "
                        f"{profile.explainability.final_score or profile.alternative_credit_score}. "
                        f"Top SHAP-style contributions: {contribution_detail}."
                    ),
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


def _alternative_credit_weight(request: GrowAnalyzeRequest) -> int:
    profile = request.alternative_credit_profile
    if profile is None:
        return 0

    score = profile.alternative_credit_score
    if score is not None:
        if score >= 80 and profile.vn_social_complaint_count_30d <= 1:
            return 10
        if score >= 65:
            return 6
        if score < 45 or profile.vn_social_complaint_count_30d >= 4:
            return -8
        return 0

    positive_graph = (profile.trust_graph_score or 0) >= 0.75
    positive_social = (profile.vn_social_reputation_score or 0) >= 0.7
    weak_social = profile.vn_social_complaint_count_30d >= 4 or profile.vn_social_sentiment == "negative"
    if positive_graph and positive_social:
        return 8
    if weak_social:
        return -8
    return 0
