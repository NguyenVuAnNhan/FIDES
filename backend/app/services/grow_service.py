from backend.app.models import Explanation, GrowAnalyzeRequest, GrowAnalyzeResponse
from backend.app.services.ml.credit_model import build_explainability, predict_credit_score


def analyze_invoice(request: GrowAnalyzeRequest) -> GrowAnalyzeResponse:
    explanations: list[Explanation] = []
    prediction = predict_credit_score(request)
    explainability = build_explainability(prediction)

    if request.input_mode != "manual_entry":
        explanations.append(
            Explanation(
                label="Minimal input captured",
                detail=f"Grow received this record through {request.input_mode}.",
                weight=0,
            )
        )

    if request.ocr.status == "completed":
        provider = request.ocr.provider or "OCR"
        confidence = ""
        if request.ocr.confidence is not None:
            confidence = f" Confidence: {request.ocr.confidence:.2f}."
        explanations.append(
            Explanation(
                label=f"{provider} extraction",
                detail=f"Invoice fields were extracted from {request.input_source or 'an uploaded image'}.{confidence}",
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

    top_contributions = explainability.feature_contributions[:3]
    contribution_detail = "; ".join(
        f"{item.feature} {item.shap_value:+.1f}" for item in top_contributions
    )
    model_label = "LightGBM credit model" if prediction.used_ml else "Rule-based credit scorer"
    explanations.append(
        Explanation(
            label="Explainable credit model",
            detail=(
                f"{model_label} ({explainability.model_type} "
                f"{explainability.model_version}): baseline "
                f"{explainability.baseline_score}, final "
                f"{explainability.final_score or prediction.trust_score}. "
                f"Top contributions: {contribution_detail or 'none'}."
            ),
            weight=0,
        )
    )

    trust_score = prediction.trust_score
    monthly_revenue = request.invoice_total * 4
    credit_band, readiness, recommended_action = _credit_band_from_score(trust_score)

    return GrowAnalyzeResponse(
        trust_score=trust_score,
        credit_band=credit_band,
        monthly_revenue_estimate=monthly_revenue,
        loan_readiness=readiness,
        explanations=explanations,
        recommended_action=recommended_action,
        credit_explainability=explainability,
    )


def compute_rule_trust_score(request: GrowAnalyzeRequest) -> int:
    """Deterministic rule-based score used for training labels and ML fallback."""
    score = 45

    if request.invoice_total >= 20_000_000:
        score += 18
    if request.paid_on_time:
        score += 22
    else:
        score -= 12
    if len(request.items) >= 2:
        score += 8

    return max(0, min(score, 100))


def _credit_band_from_score(trust_score: int) -> tuple[str, str, str]:
    if trust_score >= 75:
        return (
            "strong",
            "ready_for_small_working_capital_offer",
            "Prepare a small working-capital loan offer with invoice-backed limits.",
        )
    if trust_score >= 55:
        return (
            "emerging",
            "needs_more_transaction_history",
            "Ask for two more invoices or bank-statement snapshots to improve confidence.",
        )
    return (
        "thin_file",
        "not_ready",
        "Keep building invoice history before recommending credit.",
    )
