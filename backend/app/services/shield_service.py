from backend.app.models import Explanation, ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldChallengeRequest

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
OUTER_BREAKER_THRESHOLD = 45
INVASIVE_FAIL_THRESHOLD = 25
TRANSACTION_HOLD_HOURS = 24
SUPPORTED_CHALLENGE_PROFILES = {
    "clear_user",
    "coerced_authority",
    "deepfake_injection",
    "scripted_remote_support",
}


def run_mock_camera_voice_challenge(challenge: ShieldChallengeRequest) -> ShieldAnalyzeResponse:
    profile = _normalize_challenge_profile(challenge.challenge_profile)
    provider_fields, provider_calls = _run_mock_challenge_apis(challenge, profile)
    challenged_request = challenge.transaction.model_copy(update=provider_fields)
    response = analyze_shield_risk(challenged_request)

    return response.model_copy(
        update={
            "challenge_profile": profile,
            "mock_provider_calls": provider_calls,
            "explanations": [*provider_calls, *response.explanations],
        }
    )


def _normalize_challenge_profile(profile: str) -> str:
    normalized = profile.strip().lower() or "clear_user"
    if normalized in SUPPORTED_CHALLENGE_PROFILES:
        return normalized
    return "clear_user"


def _run_mock_challenge_apis(
    challenge: ShieldChallengeRequest,
    profile: str,
) -> tuple[dict[str, object], list[Explanation]]:
    ekyc_fields, ekyc_call = _mock_ekyc_api(profile)
    smartvoice_fields, smartvoice_call = _mock_smartvoice_api(challenge.spoken_response, profile)
    smartbot_fields, smartbot_call = _mock_smartbot_api(str(smartvoice_fields["stt_transcript"]), profile)
    coercion_fields, coercion_call = _mock_coercion_api(profile)

    fields = {
        "consent_granted": True,
        "audio_source": f"mock://shield-challenge/{profile}.wav",
        **ekyc_fields,
        **smartvoice_fields,
        **smartbot_fields,
        **coercion_fields,
        "transcript": smartvoice_fields["stt_transcript"],
    }
    return fields, [ekyc_call, smartvoice_call, smartbot_call, coercion_call]


def _mock_ekyc_api(profile: str) -> tuple[dict[str, object], Explanation]:
    profiles = {
        "clear_user": {
            "status": "passed",
            "liveness": 0.94,
            "mask": False,
            "face_match": 0.91,
            "injection": 0.04,
            "detail": "Mock eKYC returned passed liveness, face match, and low injection risk.",
        },
        "coerced_authority": {
            "status": "passed",
            "liveness": 0.9,
            "mask": False,
            "face_match": 0.88,
            "injection": 0.07,
            "detail": "Mock eKYC verified the user but did not clear coercion risk.",
        },
        "deepfake_injection": {
            "status": "failed",
            "liveness": 0.32,
            "mask": True,
            "face_match": 0.42,
            "injection": 0.86,
            "detail": "Mock eKYC flagged failed liveness, possible mask, and high injection risk.",
        },
        "scripted_remote_support": {
            "status": "review",
            "liveness": 0.74,
            "mask": False,
            "face_match": 0.79,
            "injection": 0.22,
            "detail": "Mock eKYC asked for review but did not detect biometric injection.",
        },
    }
    selected = profiles[profile]
    return (
        {
            "ekyc_verification_status": selected["status"],
            "ekyc_liveness_score": selected["liveness"],
            "ekyc_mask_detected": selected["mask"],
            "ekyc_face_match_score": selected["face_match"],
            "ekyc_injection_risk_score": selected["injection"],
        },
        Explanation(label="Mock eKYC API", detail=str(selected["detail"]), weight=0),
    )


def _mock_smartvoice_api(spoken_response: str, profile: str) -> tuple[dict[str, object], Explanation]:
    transcript = spoken_response.strip() or _default_challenge_transcript(profile)
    confidences = {
        "clear_user": 0.92,
        "coerced_authority": 0.9,
        "deepfake_injection": 0.73,
        "scripted_remote_support": 0.88,
    }
    return (
        {
            "stt_transcript": transcript,
            "stt_confidence": confidences[profile],
        },
        Explanation(
            label="Mock SmartVoice API",
            detail=f"Speech-to-text returned a transcript with confidence {confidences[profile]:.2f}.",
            weight=0,
        ),
    )


def _mock_smartbot_api(transcript: str, profile: str) -> tuple[dict[str, object], Explanation]:
    profile_scam_types = {
        "clear_user": None,
        "coerced_authority": "fake_authority",
        "deepfake_injection": None,
        "scripted_remote_support": "remote_support",
    }
    scam_type = profile_scam_types[profile]
    transcript_match = _match_transcript_pattern(transcript.lower())
    if scam_type is None and transcript_match:
        scam_type = transcript_match[0]

    detected_patterns = detected_patterns_for_challenge(profile, scam_type)
    confidence = None
    if scam_type:
        confidence = 0.91 if profile != "scripted_remote_support" else 0.88

    detail = (
        f"Smartbot classified {scam_type.replace('_', ' ')}."
        if scam_type
        else "Smartbot did not find a scam-script pattern."
    )
    return (
        {
            "detected_patterns": detected_patterns,
            "llm_scam_type": scam_type,
            "llm_confidence": confidence,
        },
        Explanation(label="Mock Smartbot API", detail=detail, weight=0),
    )


def _mock_coercion_api(profile: str) -> tuple[dict[str, object], Explanation]:
    profiles = {
        "clear_user": {
            "voice": 0.18,
            "voice_labels": ["steady_voice"],
            "face": 0.16,
            "face_labels": ["calm"],
            "scripted": 0.12,
            "scripted_labels": ["free_response"],
            "coercion": 0.14,
            "confidence": 0.82,
            "detail": "Mock coercion API found calm speech and unscripted response.",
        },
        "coerced_authority": {
            "voice": 0.83,
            "voice_labels": ["elevated_pitch", "speech_hesitation"],
            "face": 0.77,
            "face_labels": ["fear", "low_eye_contact"],
            "scripted": 0.81,
            "scripted_labels": ["monotone_reading", "repeats_caller_phrasing"],
            "coercion": 0.84,
            "confidence": 0.86,
            "detail": "Mock coercion API found distress and scripted behavior.",
        },
        "deepfake_injection": {
            "voice": 0.38,
            "voice_labels": ["synthetic_audio_artifact"],
            "face": 0.46,
            "face_labels": ["visual_artifact"],
            "scripted": 0.25,
            "scripted_labels": [],
            "coercion": 0.32,
            "confidence": 0.78,
            "detail": "Mock coercion API did not find coercion, but biometric artifacts remain.",
        },
        "scripted_remote_support": {
            "voice": 0.76,
            "voice_labels": ["speech_hesitation", "fast_breathing"],
            "face": 0.68,
            "face_labels": ["distress", "reduced_attention"],
            "scripted": 0.88,
            "scripted_labels": ["screen_instruction_following", "repeats_caller_phrasing"],
            "coercion": 0.78,
            "confidence": 0.84,
            "detail": "Mock coercion API found remote-support scripting and distress.",
        },
    }
    selected = profiles[profile]
    return (
        {
            "voice_stress_score": selected["voice"],
            "voice_stress_labels": selected["voice_labels"],
            "face_emotion_score": selected["face"],
            "face_emotion_labels": selected["face_labels"],
            "scripted_behavior_score": selected["scripted"],
            "scripted_behavior_labels": selected["scripted_labels"],
            "coercion_score": selected["coercion"],
            "coercion_confidence": selected["confidence"],
        },
        Explanation(label="Mock coercion API", detail=str(selected["detail"]), weight=0),
    )


def _default_challenge_transcript(profile: str) -> str:
    transcripts = {
        "clear_user": (
            "Toi dang tu minh xac nhan giao dich nay. Khong co ai huong dan toi qua dien thoai. "
            "Toi da tu kiem tra nguoi nhan va muon tiep tuc."
        ),
        "coerced_authority": (
            "Toi dang lam theo yeu cau cua cong an. Tai khoan cua toi lien quan vu an "
            "nen toi phai chuyen tien de xac minh va giu bi mat."
        ),
        "deepfake_injection": "Toi dang tu xac nhan giao dich nay va muon tiep tuc.",
        "scripted_remote_support": (
            "Nhan vien ho tro dang dieu khien man hinh de sua loi. Toi can chuyen tien test "
            "he thong va se duoc hoan lai."
        ),
    }
    return transcripts[profile]


def detected_patterns_for_challenge(profile: str, scam_type: str | None) -> list[str]:
    profile_patterns = {
        "clear_user": [],
        "coerced_authority": [
            "fake_authority",
            "case_involvement",
            "transfer_for_verification",
            "secrecy_pressure",
        ],
        "deepfake_injection": [],
        "scripted_remote_support": [
            "remote_support",
            "screen_control",
            "refund_promise",
            "transfer_test",
        ],
    }
    if profile_patterns[profile]:
        return profile_patterns[profile]
    return [scam_type] if scam_type else []


def analyze_shield_risk(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    stage_one_score, stage_one_flags = _score_outer_context(request)
    circuit_breaker_triggered = stage_one_score >= OUTER_BREAKER_THRESHOLD

    if not circuit_breaker_triggered:
        return ShieldAnalyzeResponse(
            risk_score=stage_one_score,
            risk_level="low",
            action="allow_with_notice",
            circuit_breaker_stage="outer_context_clear",
            circuit_breaker_triggered=False,
            invasive_check_required=False,
            stage_one_score=stage_one_score,
            stage_two_score=None,
            stage_one_flags=stage_one_flags,
            stage_two_flags=[],
            scam_type=None,
            explanations=stage_one_flags,
            intervention_message=_build_intervention_message("allow_with_notice", request.recipient_name),
        )

    if not _has_invasive_check_evidence(request):
        challenge_explanation = Explanation(
            label="Camera and voice challenge required",
            detail=(
                "The outer circuit breaker tripped, so Shield needs a consented camera "
                "and voice check before the transfer can continue."
            ),
            weight=0,
        )
        return ShieldAnalyzeResponse(
            risk_score=stage_one_score,
            risk_level="elevated",
            action="require_camera_voice_check",
            circuit_breaker_stage="invasive_check_required",
            circuit_breaker_triggered=True,
            invasive_check_required=True,
            stage_one_score=stage_one_score,
            stage_two_score=None,
            stage_one_flags=stage_one_flags,
            stage_two_flags=[],
            scam_type=None,
            explanations=[*stage_one_flags, challenge_explanation],
            intervention_message=_build_intervention_message(
                "require_camera_voice_check", request.recipient_name
            ),
        )

    stage_two_score, stage_two_flags, scam_type = _score_invasive_check(request)
    stage_two_failed = stage_two_score >= INVASIVE_FAIL_THRESHOLD

    if stage_two_failed:
        risk_score = min(100, stage_one_score + stage_two_score)
        return ShieldAnalyzeResponse(
            risk_score=risk_score,
            risk_level="critical",
            action="withhold_24h_notify_trusted_authority",
            circuit_breaker_stage="withhold_and_notify",
            circuit_breaker_triggered=True,
            invasive_check_required=False,
            stage_one_score=stage_one_score,
            stage_two_score=stage_two_score,
            stage_one_flags=stage_one_flags,
            stage_two_flags=stage_two_flags,
            trusted_authority_notification=True,
            trusted_authority_message=_build_trusted_authority_message(request.recipient_name),
            transaction_hold_hours=TRANSACTION_HOLD_HOURS,
            scam_type=scam_type,
            explanations=[*stage_one_flags, *stage_two_flags],
            intervention_message=_build_intervention_message(
                "withhold_24h_notify_trusted_authority", request.recipient_name
            ),
        )

    cleared_explanation = Explanation(
        label="Camera and voice challenge cleared",
        detail=(
            "The outer circuit breaker tripped, but the consented eKYC, voice, and "
            "distress checks did not show enough evidence to hold the transfer."
        ),
        weight=0,
    )
    return ShieldAnalyzeResponse(
        risk_score=min(44, 10 + stage_two_score),
        risk_level="low",
        action="allow_after_challenge",
        circuit_breaker_stage="invasive_check_cleared",
        circuit_breaker_triggered=True,
        invasive_check_required=False,
        stage_one_score=stage_one_score,
        stage_two_score=stage_two_score,
        stage_one_flags=stage_one_flags,
        stage_two_flags=stage_two_flags,
        scam_type=scam_type,
        explanations=[*stage_one_flags, *stage_two_flags, cleared_explanation],
        intervention_message=_build_intervention_message("allow_after_challenge", request.recipient_name),
    )


def _score_outer_context(request: ShieldAnalyzeRequest) -> tuple[int, list[Explanation]]:
    score = 10
    explanations: list[Explanation] = []

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

    return min(score, 100), explanations


def _score_invasive_check(request: ShieldAnalyzeRequest) -> tuple[int, list[Explanation], str | None]:
    transcript = _effective_transcript(request).lower()
    score = 0
    explanations: list[Explanation] = []
    scam_type: str | None = None

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
            keyword_weight = min(30, 10 + match_count * 5)
            score += keyword_weight
            scam_type = pattern_name
            explanations.append(
                Explanation(
                    label="Scam script detected",
                    detail=f"Transcript contains signals associated with {pattern_name.replace('_', ' ')}.",
                    weight=keyword_weight,
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

    return min(score, 100), explanations, scam_type


def _has_invasive_check_evidence(request: ShieldAnalyzeRequest) -> bool:
    return any(
        [
            request.ekyc_verification_status != "not_checked",
            request.ekyc_liveness_score is not None,
            request.ekyc_mask_detected,
            request.ekyc_face_match_score is not None,
            request.ekyc_injection_risk_score is not None,
            request.audio_source is not None,
            bool(request.stt_transcript),
            bool(request.detected_patterns),
            request.llm_scam_type is not None,
            request.voice_stress_score is not None,
            request.face_emotion_score is not None,
            request.scripted_behavior_score is not None,
            request.coercion_score is not None,
        ]
    )


def _build_intervention_message(action: str, recipient_name: str) -> str:
    if action == "withhold_24h_notify_trusted_authority":
        return (
            f"We are holding this transfer to {recipient_name} for 24 hours and notifying the "
            "bank fraud desk. The camera and voice check matched high-risk scam or coercion "
            "signals. Hang up, do not share codes, and use an official bank channel for help."
        )
    if action == "require_camera_voice_check":
        return (
            f"This transfer to {recipient_name} needs a short camera and voice safety check "
            "before it can continue. Please move away from the caller, open the camera, and "
            "answer the prompts in your own words."
        )
    if action == "allow_after_challenge":
        return (
            f"The extra safety check for {recipient_name} did not find enough evidence to hold "
            "the transfer. Continue only if you independently trust the recipient."
        )
    return "No strong manipulation pattern was detected, but continue only if you trust the recipient."


def _build_trusted_authority_message(recipient_name: str) -> str:
    return (
        f"Notify the bank fraud desk that a high-risk transfer to {recipient_name} was held "
        "for 24 hours after the invasive camera and voice challenge failed."
    )


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
