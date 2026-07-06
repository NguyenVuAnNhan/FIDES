"""Path A call-listen: classify a scam call audio clip via SmartVoice STT + Smartbot NLP.

This reuses the same real VNPT pipeline as the Path B challenge (SmartVoice speech-to-text
followed by Smartbot intent/scam classification with a keyword fallback), but exposes it as a
standalone "listen to a call and detect scam" flow that can alert a guardian.
"""

from __future__ import annotations

from backend.app.config import get_settings
from backend.app.models import (
    CallListenResponse,
    Explanation,
    ShieldAnalyzeRequest,
    ShieldChallengeRequest,
)
from backend.app.services.shield_challenge_service import _smartbot_api, _smartvoice_api
from backend.app.services.shield_service import match_transcript_pattern
from backend.app.services.vnpt_client import VnptClient

SCAM_TYPE_LABELS = {
    "fake_authority": "Giả danh cơ quan chức năng (công an/viện kiểm sát)",
    "otp_theft": "Lừa lấy mã OTP / mã xác thực",
    "investment": "Dụ dỗ đầu tư lợi nhuận cao",
    "remote_support": "Yêu cầu cài app / điều khiển màn hình từ xa",
}

RISK_LEVEL_LABELS = {
    "high": "Nguy cơ cao",
    "medium": "Nguy cơ trung bình",
    "low": "An toàn",
}


def analyze_call_audio(
    audio_ref: str,
    client_session: str,
    transcript_override: str | None = None,
) -> CallListenResponse:
    settings = get_settings()
    vnpt_client = VnptClient(settings)
    provider_mode = vnpt_client.mode

    explanations: list[Explanation] = []

    # Build a minimal challenge object so we can reuse the real Path B STT + Smartbot helpers.
    challenge = ShieldChallengeRequest(
        transaction=ShieldAnalyzeRequest(
            transaction_amount=0,
            recipient_name="",
            recipient_account="",
        ),
        ekyc_image_ref="",
        ekyc_document_ref="",
        stt_audio_ref=audio_ref,
        client_session=client_session,
    )

    override = (transcript_override or "").strip()
    if override:
        transcript = override
        stt_confidence: float | None = 1.0
        explanations.append(
            Explanation(
                label="Bản ghi âm thanh (nhập tay)",
                detail=f"Sử dụng transcript nhập sẵn để phân loại: {override[:180]!r}.",
                weight=0,
            )
        )
    else:
        smartvoice_fields, smartvoice_call, _ = _smartvoice_api(challenge, vnpt_client)
        transcript = str(smartvoice_fields.get("stt_transcript", ""))
        raw_conf = smartvoice_fields.get("stt_confidence")
        stt_confidence = float(raw_conf) if isinstance(raw_conf, (int, float)) else None
        explanations.append(smartvoice_call)

    smartbot_fields, smartbot_call, _ = _smartbot_api(transcript, client_session, vnpt_client)
    explanations.append(smartbot_call)

    scam_type = smartbot_fields.get("llm_scam_type")
    scam_type = str(scam_type) if scam_type else None
    detected_patterns = list(smartbot_fields.get("detected_patterns") or [])
    raw_llm_conf = smartbot_fields.get("llm_confidence")
    confidence = float(raw_llm_conf) if isinstance(raw_llm_conf, (int, float)) else None

    # Extra safety net: if classification found nothing but the transcript clearly
    # matches a known scam script, treat it as scam.
    if scam_type is None and transcript.strip():
        keyword_match = match_transcript_pattern(transcript.lower())
        if keyword_match:
            scam_type = keyword_match[0]
            confidence = confidence or 0.72
            explanations.append(
                Explanation(
                    label="Đối chiếu kịch bản lừa đảo",
                    detail=f"Nội dung khớp mẫu lừa đảo '{scam_type}'.",
                    weight=0,
                )
            )

    is_scam = scam_type is not None
    scam_label = SCAM_TYPE_LABELS.get(scam_type, "Dấu hiệu lừa đảo") if is_scam else (
        "Không phát hiện dấu hiệu lừa đảo"
    )

    if is_scam:
        risk_level = "high" if (confidence or 0) >= 0.7 else "medium"
        recommended_action = "alert_guardian_and_hold"
        intervention_message = (
            f"Cuộc gọi có dấu hiệu {scam_label.lower()}. FIDES khuyến nghị KHÔNG làm theo yêu cầu "
            "chuyển tiền / cung cấp OTP, và đã gửi cảnh báo cho người giám hộ để xác nhận."
        )
        guardian_alert = True
        guardian_message = (
            "Người thân của bạn vừa nhận một cuộc gọi nghi lừa đảo "
            f"({scam_label}). Vui lòng liên hệ và xác nhận trước khi họ thực hiện giao dịch."
        )
    else:
        risk_level = "low"
        recommended_action = "no_action"
        intervention_message = (
            "Chưa phát hiện dấu hiệu lừa đảo trong đoạn hội thoại này. Vẫn nên cẩn trọng nếu được "
            "yêu cầu chuyển tiền gấp."
        )
        guardian_alert = False
        guardian_message = ""

    return CallListenResponse(
        stt_transcript=transcript,
        stt_confidence=stt_confidence,
        is_scam=is_scam,
        scam_type=scam_type,
        scam_type_label=scam_label,
        confidence=confidence,
        detected_patterns=detected_patterns,
        risk_level=risk_level,
        recommended_action=recommended_action,
        intervention_message=intervention_message,
        guardian_alert=guardian_alert,
        guardian_message=guardian_message,
        provider_mode=provider_mode,
        explanations=explanations,
    )
