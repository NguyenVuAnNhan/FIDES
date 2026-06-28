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
    "remote_support": [
        "dieu khien man hinh",
        "điều khiển màn hình",
        "chia se man hinh",
        "chia sẻ màn hình",
        "ho tro tu xa",
        "hỗ trợ từ xa",
        "ung dung la",
        "ứng dụng lạ",
    ],
}

SUSPICIOUS_CALL_PREFIXES = ("+882", "+883", "+870", "+979", "1900")


def analyze_shield_risk(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    transcript = _effective_transcript(request).lower()
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

    if request.caller_number and _is_international_number(request.caller_number):
        score += 10
        explanations.append(
            Explanation(
                label="International caller number",
                detail=f"The caller number {request.caller_number} is outside the local +84 numbering context.",
                weight=10,
            )
        )

    if request.caller_number and _has_suspicious_prefix(request.caller_number):
        score += 10
        explanations.append(
            Explanation(
                label="Suspicious caller prefix",
                detail=f"The caller number {request.caller_number} matches a high-risk demo prefix rule.",
                weight=10,
            )
        )

    if not request.recipient_known:
        score += 10
        explanations.append(
            Explanation(
                label="Unknown recipient",
                detail="The recipient is not in the user's trusted payee or recent invoice history.",
                weight=10,
            )
        )

    vn_social_weight = _vn_social_weight(request.vn_social_report_count)
    if vn_social_weight:
        score += vn_social_weight
        explanations.append(
            Explanation(
                label="vnSocial scam reports",
                detail=_build_vn_social_detail(request),
                weight=vn_social_weight,
            )
        )

    simo_weight = _simo_weight(request.simo_status)
    if simo_weight:
        score += simo_weight
        explanations.append(
            Explanation(
                label="SIMO recipient status",
                detail=_build_simo_detail(request),
                weight=simo_weight,
            )
        )

    graph_weight = _recipient_graph_weight(request)
    if graph_weight:
        score += graph_weight
        explanations.append(
            Explanation(
                label="Recipient graph risk",
                detail=_build_recipient_graph_detail(request),
                weight=graph_weight,
            )
        )

    if request.remote_control_detected:
        score += 20
        explanations.append(
            Explanation(
                label="Remote-control signal",
                detail="A remote-support or screen-control signal is active during the transfer.",
                weight=20,
            )
        )

    ekyc_weight = _ekyc_weight(request)
    if ekyc_weight:
        score += ekyc_weight
        explanations.append(
            Explanation(
                label="eKYC verification risk",
                detail=_build_ekyc_detail(request),
                weight=ekyc_weight,
            )
        )

    smartux_weight = _smartux_weight(request)
    if smartux_weight:
        score += smartux_weight
        explanations.append(
            Explanation(
                label="SmartUX native telemetry risk",
                detail=_build_smartux_detail(request),
                weight=smartux_weight,
            )
        )

    if request.consent_granted and request.audio_source:
        explanations.append(
            Explanation(
                label="Audio consent granted",
                detail=f"Audio source {request.audio_source} is available for SmartVoice transcription.",
                weight=0,
            )
        )

    if request.consent_granted and request.stt_transcript:
        confidence_detail = ""
        if request.stt_confidence is not None:
            confidence_detail = f" Confidence: {request.stt_confidence:.2f}."
        explanations.append(
            Explanation(
                label="SmartVoice transcript",
                detail=f"Speech-to-text transcript is available for scam-script analysis.{confidence_detail}",
                weight=0,
            )
        )

    if request.consent_granted and (request.llm_scam_type or request.detected_patterns):
        scam_type = request.llm_scam_type or _scam_type_from_patterns(request.detected_patterns)
        llm_weight = _llm_pattern_weight(request.llm_confidence)
        score += llm_weight
        explanations.append(
            Explanation(
                label="Smartbot pattern classification",
                detail=_build_llm_detail(request),
                weight=llm_weight,
            )
        )
    elif request.consent_granted:
        transcript_match = _match_transcript_pattern(transcript)
        if transcript_match:
            pattern_name, match_count = transcript_match
            score += min(30, 10 + match_count * 5)
            scam_type = pattern_name
            explanations.append(
                Explanation(
                    label="Scam script detected",
                    detail=f"Transcript contains signals associated with {pattern_name.replace('_', ' ')}.",
                    weight=30,
                )
            )
    elif request.active_call:
        explanations.append(
            Explanation(
                label="Audio analysis skipped",
                detail="The user has not granted consent, so Shield uses telecom and transaction context only.",
                weight=0,
            )
        )

    coercion_weight = _coercion_weight(request.coercion_score, request.coercion_confidence)
    if coercion_weight:
        score += coercion_weight
        explanations.append(
            Explanation(
                label="Coercion and distress signals",
                detail=_build_coercion_detail(request),
                weight=coercion_weight,
            )
        )

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


def _is_international_number(caller_number: str) -> bool:
    normalized = _normalize_phone(caller_number)
    return normalized.startswith("+") and not normalized.startswith("+84")


def _has_suspicious_prefix(caller_number: str) -> bool:
    normalized = _normalize_phone(caller_number)
    return any(normalized.startswith(prefix) for prefix in SUSPICIOUS_CALL_PREFIXES)


def _normalize_phone(caller_number: str) -> str:
    return caller_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def _effective_transcript(request: ShieldAnalyzeRequest) -> str:
    return request.stt_transcript or request.transcript


def _match_transcript_pattern(transcript: str) -> tuple[str, int] | None:
    for pattern_name, keywords in SCAM_PATTERNS.items():
        matches = [keyword for keyword in keywords if keyword in transcript]
        if matches:
            return pattern_name, len(matches)
    return None


def _scam_type_from_patterns(patterns: list[str]) -> str | None:
    for pattern in patterns:
        if pattern in SCAM_PATTERNS:
            return pattern
    return None


def _llm_pattern_weight(confidence: float | None) -> int:
    if confidence is None or confidence >= 0.75:
        return 30
    if confidence >= 0.55:
        return 22
    return 12


def _build_llm_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = []
    if request.llm_scam_type:
        pieces.append(f"Scam type: {request.llm_scam_type.replace('_', ' ')}.")
    if request.detected_patterns:
        pieces.append(f"Patterns: {', '.join(request.detected_patterns)}.")
    if request.llm_confidence is not None:
        pieces.append(f"Confidence: {request.llm_confidence:.2f}.")
    return " ".join(pieces)


def _coercion_weight(coercion_score: float | None, confidence: float | None) -> int:
    if coercion_score is None:
        return 0
    confidence_multiplier = 1.0 if confidence is None else confidence
    effective_score = coercion_score * confidence_multiplier
    if effective_score >= 0.75:
        return 20
    if effective_score >= 0.5:
        return 12
    if effective_score >= 0.35:
        return 6
    return 0


def _build_coercion_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = []
    if request.coercion_score is not None:
        pieces.append(f"Aggregate coercion score: {request.coercion_score:.2f}.")
    if request.coercion_confidence is not None:
        pieces.append(f"Confidence: {request.coercion_confidence:.2f}.")
    if request.voice_stress_score is not None:
        pieces.append(_signal_detail("Voice stress", request.voice_stress_score, request.voice_stress_labels))
    if request.face_emotion_score is not None:
        pieces.append(_signal_detail("Visual distress", request.face_emotion_score, request.face_emotion_labels))
    if request.scripted_behavior_score is not None:
        pieces.append(
            _signal_detail("Scripted behavior", request.scripted_behavior_score, request.scripted_behavior_labels)
        )
    return " ".join(piece for piece in pieces if piece)


def _signal_detail(label: str, score: float, labels: list[str]) -> str:
    label_text = f" Labels: {', '.join(labels)}." if labels else ""
    return f"{label}: {score:.2f}.{label_text}"


def _vn_social_weight(report_count: int) -> int:
    if report_count >= 20:
        return 20
    if report_count >= 5:
        return 12
    if report_count > 0:
        return 6
    return 0


def _build_vn_social_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = [f"{request.vn_social_report_count} recent report(s) reference this recipient."]
    if request.vn_social_recent_keywords:
        pieces.append(f"Keywords: {', '.join(request.vn_social_recent_keywords)}.")
    if request.recipient_phone:
        pieces.append(f"Recipient phone: {request.recipient_phone}.")
    return " ".join(pieces)


def _simo_weight(status: str) -> int:
    normalized = status.lower()
    if normalized == "listed":
        return 25
    if normalized == "watchlisted":
        return 15
    if normalized == "not_listed":
        return 0
    return 0


def _build_simo_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = [f"SIMO status is {request.simo_status}."]
    if request.simo_last_checked_at:
        pieces.append(f"Last checked at {request.simo_last_checked_at}.")
    return " ".join(pieces)


def _recipient_graph_weight(request: ShieldAnalyzeRequest) -> int:
    if request.graph_risk_score is not None:
        if request.graph_risk_score >= 0.85:
            return 25
        if request.graph_risk_score >= 0.65:
            return 16
        if request.graph_risk_score >= 0.45:
            return 8
    if request.funds_moved_within_minutes and request.inbound_sender_count_10m >= 5:
        return 12
    return 0


def _build_recipient_graph_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = []
    if request.graph_risk_score is not None:
        pieces.append(f"Graph risk score: {request.graph_risk_score:.2f}.")
    if request.graph_pattern:
        pieces.append(f"Pattern: {request.graph_pattern}.")
    if request.recipient_risk_level != "unknown":
        pieces.append(f"Recipient risk level: {request.recipient_risk_level}.")
    pieces.append(f"Inbound senders in 10m: {request.inbound_sender_count_10m}.")
    pieces.append(f"Outbound accounts in 10m: {request.outbound_account_count_10m}.")
    if request.median_pass_through_minutes is not None:
        pieces.append(f"Median pass-through: {request.median_pass_through_minutes:.1f} min.")
    if request.account_age_days is not None:
        pieces.append(f"Account age: {request.account_age_days} day(s).")
    if request.shared_device_cluster_size:
        pieces.append(f"Shared-device cluster size: {request.shared_device_cluster_size}.")
    if request.funds_moved_within_minutes:
        pieces.append("Funds moved onward within minutes.")
    return " ".join(pieces)


def _ekyc_weight(request: ShieldAnalyzeRequest) -> int:
    weight = 0
    status = request.ekyc_verification_status.lower()
    if status == "failed":
        weight += 25
    elif status == "review":
        weight += 12
    if request.ekyc_liveness_score is not None:
        if request.ekyc_liveness_score < 0.5:
            weight += 20
        elif request.ekyc_liveness_score < 0.7:
            weight += 10
    if request.ekyc_mask_detected:
        weight += 10
    if request.ekyc_face_match_score is not None:
        if request.ekyc_face_match_score < 0.5:
            weight += 18
        elif request.ekyc_face_match_score < 0.75:
            weight += 8
    if request.ekyc_injection_risk_score is not None:
        if request.ekyc_injection_risk_score >= 0.75:
            weight += 25
        elif request.ekyc_injection_risk_score >= 0.45:
            weight += 14
    return min(weight, 30)


def _build_ekyc_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = [f"Verification status: {request.ekyc_verification_status}."]
    if request.ekyc_liveness_score is not None:
        pieces.append(f"Liveness score: {request.ekyc_liveness_score:.2f}.")
    pieces.append(f"Mask detected: {str(request.ekyc_mask_detected).lower()}.")
    if request.ekyc_face_match_score is not None:
        pieces.append(f"Face match score: {request.ekyc_face_match_score:.2f}.")
    if request.ekyc_injection_risk_score is not None:
        pieces.append(f"Injection risk score: {request.ekyc_injection_risk_score:.2f}.")
    return " ".join(pieces)


def _smartux_weight(request: ShieldAnalyzeRequest) -> int:
    weight = 0
    if request.installed_remote_access_app_detected:
        weight += 10
    if request.accessibility_service_risk:
        weight += 10
    if request.screen_sharing_detected:
        weight += 12
    if request.smartux_behavior_anomaly_score is not None:
        if request.smartux_behavior_anomaly_score >= 0.75:
            weight += 14
        elif request.smartux_behavior_anomaly_score >= 0.5:
            weight += 8
    if request.smartux_remote_control_score is not None:
        if request.smartux_remote_control_score >= 0.75:
            weight += 18
        elif request.smartux_remote_control_score >= 0.5:
            weight += 10
    return min(weight, 25)


def _build_smartux_detail(request: ShieldAnalyzeRequest) -> str:
    pieces = []
    if request.native_telemetry_available:
        source = request.native_telemetry_source or "sdk_consumer"
        pieces.append(f"Native telemetry source: {source}.")
    pieces.append(
        "Installed remote-access app detected: "
        f"{str(request.installed_remote_access_app_detected).lower()}."
    )
    pieces.append(f"Accessibility service risk: {str(request.accessibility_service_risk).lower()}.")
    pieces.append(f"Screen sharing detected: {str(request.screen_sharing_detected).lower()}.")
    if request.smartux_behavior_anomaly_score is not None:
        pieces.append(f"Behavior anomaly score: {request.smartux_behavior_anomaly_score:.2f}.")
    if request.smartux_remote_control_score is not None:
        pieces.append(f"Remote-control score: {request.smartux_remote_control_score:.2f}.")
    if request.smartux_signals:
        pieces.append(f"Signals: {', '.join(request.smartux_signals)}.")
    return " ".join(pieces)
