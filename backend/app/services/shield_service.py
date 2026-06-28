from backend.app.models import Explanation, ShieldAnalyzeRequest, ShieldAnalyzeResponse

SCAM_PATTERNS = {
    "fake_authority": [
        "cong an",
        "công an",
        "vien kiem sat",
        "viện kiểm sát",
        "vu an",
        "vụ án",
        "xac minh",
        "xác minh",
        "bi mat",
        "bí mật",
    ],
    "otp_theft": ["otp", "ma xac thuc", "mã xác thực", "doc ma", "đọc mã"],
    "investment": ["loi nhuan", "lợi nhuận", "cam ket", "cam kết", "dau tu", "đầu tư"],
}


def analyze_shield_risk(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    transcript = request.transcript.lower()
    score = 10
    explanations: list[Explanation] = []
    scam_type: str | None = None

    if request.transaction_amount >= 50_000_000:
        score += 25
        explanations.append(
            Explanation(
                label="High-value transfer",
                detail="The transaction amount is large enough to require extra friction.",
                weight=25,
            )
        )

    if request.active_call:
        score += 20
        explanations.append(
            Explanation(
                label="Active call during transfer",
                detail="APP fraud often happens while the victim is being coached by phone.",
                weight=20,
            )
        )

    if request.caller_type in {"voip", "international", "unknown"}:
        score += 10
        explanations.append(
            Explanation(
                label="Caller context",
                detail=f"The caller type is marked as {request.caller_type}.",
                weight=10,
            )
        )

    for pattern_name, keywords in SCAM_PATTERNS.items():
        matches = [keyword for keyword in keywords if keyword in transcript]
        if matches:
            score += min(30, 10 + len(matches) * 5)
            scam_type = pattern_name
            explanations.append(
                Explanation(
                    label="Scam script detected",
                    detail=f"Transcript contains signals associated with {pattern_name.replace('_', ' ')}.",
                    weight=30,
                )
            )
            break

    risk_score = min(score, 100)
    if risk_score >= 75:
        risk_level = "critical"
        action = "pause_transfer"
    elif risk_score >= 45:
        risk_level = "elevated"
        action = "step_up_verification"
    else:
        risk_level = "low"
        action = "allow_with_notice"

    return ShieldAnalyzeResponse(
        risk_score=risk_score,
        risk_level=risk_level,
        action=action,
        scam_type=scam_type,
        explanations=explanations,
        intervention_message=_build_intervention_message(risk_level, request.recipient_name),
    )


def _build_intervention_message(risk_level: str, recipient_name: str) -> str:
    if risk_level == "critical":
        return (
            f"We paused this transfer to {recipient_name}. The call and transcript look similar "
            "to a coercion scam. Please hang up, contact the organization through an official "
            "number, and confirm with a trusted contact before continuing."
        )
    if risk_level == "elevated":
        return (
            f"This transfer to {recipient_name} has warning signs. Take a moment to verify the "
            "recipient independently before approving."
        )
    return "No strong manipulation pattern was detected, but continue only if you trust the recipient."

