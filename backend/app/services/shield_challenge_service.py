"""Path B transfer monitoring: in-app camera/voice challenge via VNPT."""

from __future__ import annotations

from typing import Any

from backend.app.config import get_settings
from backend.app.models import Explanation, ShieldAnalyzeResponse, ShieldChallengeRequest
from backend.app.services.shield_service import analyze_shield_risk, detected_patterns_for_challenge, match_transcript_pattern
from backend.app.services.smartbot.parser import parse_smartbot_response
from backend.app.services.smartvision.parser import (
    SmartvisionFaceEmotion,
    aggregate_smartvision_frames,
    parse_smartvision_face_emotion,
)
from backend.app.services.voice_stress import analyze_voice_stress
from backend.app.services.vnpt_client import VnptClient


def run_transfer_monitoring_challenge(challenge: ShieldChallengeRequest) -> ShieldAnalyzeResponse:
    """Run Path B in-app check, merge provider fields, and re-score with E0/E2."""
    settings = get_settings()
    vnpt_client = VnptClient(settings)
    provider_fields, provider_calls, raw_responses, provider_mode = _run_challenge_apis(
        challenge,
        vnpt_client,
    )
    profile = _challenge_profile_from_results(
        str(provider_fields.get("ekyc_verification_status", "failed")),
        str(provider_fields.get("stt_transcript", "")),
    )
    challenged_request = challenge.transaction.model_copy(update=provider_fields)
    response = analyze_shield_risk(challenged_request)

    return response.model_copy(
        update={
            "challenge_profile": profile,
            "provider_mode": provider_mode,
            "mock_provider_calls": provider_calls,
            "provider_raw_responses": raw_responses,
            "mock_provider_raw_responses": raw_responses,
            "explanations": [*provider_calls, *response.explanations],
        }
    )


def _run_challenge_apis(
    challenge: ShieldChallengeRequest,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], list[Explanation], dict[str, dict[str, Any]], str]:
    provider_mode = vnpt_client.mode
    ekyc_fields, ekyc_call, ekyc_raw = _ekyc_api(challenge, vnpt_client)
    smartvoice_fields, smartvoice_call, smartvoice_raw = _smartvoice_api(challenge, vnpt_client)
    smartbot_fields, smartbot_call, smartbot_raw = _smartbot_api(
        str(smartvoice_fields["stt_transcript"]),
        challenge.client_session,
        vnpt_client,
    )
    smartvision_fields, smartvision_call, smartvision_raw = _smartvision_api(challenge, vnpt_client)
    coercion_fields, coercion_call, voice_stress_raw = _coercion_api(
        challenge.stt_audio_ref,
        str(smartvoice_fields["stt_transcript"]),
        smartbot_fields.get("llm_scam_type") if isinstance(smartbot_fields.get("llm_scam_type"), str) else None,
        smartvision_fields.get("face_emotion_score"),
        smartvision_fields.get("face_emotion_labels"),
    )

    fields = {
        "consent_granted": True,
        "consent_transfer_check": True,
        "consent_call_monitoring": False,
        "shield_path": "transfer_monitoring",
        "audio_source": challenge.challenge_video_ref or challenge.stt_audio_ref,
        **ekyc_fields,
        **smartvoice_fields,
        **smartbot_fields,
        **smartvision_fields,
        **coercion_fields,
        "transcript": smartvoice_fields["stt_transcript"],
    }
    raw_responses = {
        "ekyc_face_liveness": ekyc_raw["face_liveness"],
        "ekyc_face_mask": ekyc_raw["face_mask"],
        "ekyc_face_compare": ekyc_raw["face_compare"],
        "smartvoice_stt": smartvoice_raw,
        "smartbot_conversation": smartbot_raw,
        "smartvision_detect_face": smartvision_raw,
        "smartvision_frame_count": smartvision_raw.get("frame_count"),
        "voice_stress": voice_stress_raw,
    }
    return fields, [ekyc_call, smartvoice_call, smartbot_call, smartvision_call, coercion_call], raw_responses, provider_mode


def _challenge_profile_from_results(
    ekyc_verification_status: str,
    stt_transcript: str,
) -> str:
    ekyc_passed = ekyc_verification_status == "passed"
    stt_passed = _stt_passed(stt_transcript)
    if ekyc_passed and stt_passed:
        return "clear_user"
    if not ekyc_passed and stt_passed:
        return "ekyc_failed"
    if ekyc_passed and not stt_passed:
        return "stt_failed"
    return "ekyc_and_stt_failed"


def _stt_passed(stt_transcript: str) -> bool:
    if not stt_transcript.strip():
        return False
    return match_transcript_pattern(stt_transcript.lower()) is None


def _object(response: dict[str, Any]) -> dict[str, Any]:
    value = response.get("object", {})
    if isinstance(value, dict):
        return value
    return {}


def _vnpt_call_failed(response: dict[str, Any]) -> bool:
    if response.get("status") == "error":
        return True
    http_status = response.get("http_status")
    if isinstance(http_status, int) and http_status >= 400:
        return True
    provider_status = str(response.get("status", "")).upper()
    if provider_status in {"BAD_REQUEST", "ERROR", "FAIL", "FAILED", "UNAUTHORIZED"}:
        return True
    status_code = response.get("statusCode")
    if isinstance(status_code, str) and status_code.upper().startswith(("4", "5")):
        return True
    if response.get("errors"):
        return True
    message_fields = response.get("messageFields")
    if isinstance(message_fields, list) and message_fields:
        return True
    return False


def _vnpt_error_detail(response: dict[str, Any]) -> str:
    message_fields = response.get("messageFields")
    if isinstance(message_fields, list) and message_fields:
        parts: list[str] = []
        for item in message_fields:
            if isinstance(item, dict):
                field_name = item.get("fieldName", "field")
                field_message = item.get("message", "")
                parts.append(f"{field_name}: {field_message}")
        if parts:
            return "; ".join(parts)

    errors = response.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(item) for item in errors)
    message = response.get("message")
    if message:
        return str(message)
    nested = response.get("error")
    if isinstance(nested, dict):
        body = nested.get("body")
        if isinstance(body, dict) and body.get("message"):
            return str(body["message"])
    return "VNPT eKYC call failed"


def _bounded_float(value: object, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _provider_score(value: object, default: float) -> float:
    score = _bounded_float(value, default)
    try:
        raw_number = float(value)
    except (TypeError, ValueError):
        return score
    if raw_number > 1:
        return _bounded_float(raw_number / 100, default)
    return score


def _truthy_provider_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "live", "masked", "match"}
    if isinstance(value, (int, float)):
        return value > 0
    return False


def _derive_injection_risk(face_is_live: bool, mask_detected: bool, face_match_score: float) -> float:
    risk = 0.04
    if not face_is_live:
        risk += 0.55
    if mask_detected:
        risk += 0.18
    if face_match_score < 0.5:
        risk += 0.18
    elif face_match_score < 0.75:
        risk += 0.08
    return round(min(risk, 0.95), 2)


def _ekyc_unconfigured_response(image_ref: str) -> tuple[dict[str, object], Explanation, dict[str, dict[str, Any]]]:
    message = "VNPT eKYC credentials are not configured. Set VNPT_EKYC_MODE=real and eKYC tokens in .env."
    failed = {
        "message": message,
        "object": {},
        "status": "error",
        "provider_mode": "disabled",
    }
    detail = f"VNPT eKYC API skipped for {image_ref}. {message}"
    fields = {
        "ekyc_verification_status": "failed",
        "ekyc_liveness_passed": False,
        "ekyc_liveness_score": None,
        "ekyc_mask_detected": False,
        "ekyc_face_match_score": 0.0,
        "ekyc_injection_risk_score": 0.77,
    }
    return (
        fields,
        Explanation(label="VNPT eKYC API", detail=detail, weight=0),
        {
            "face_liveness": failed,
            "face_mask": failed,
            "face_compare": failed,
        },
    )


def _smartvoice_unconfigured_response(
    audio_ref: str,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    message = (
        "VNPT SmartVoice credentials are not configured. "
        "Set VNPT_SMARTVOICE_MODE=real and SmartVoice tokens in .env."
    )
    failed = {
        "message": message,
        "object": {},
        "status": "error",
        "provider_mode": "disabled",
    }
    detail = f"VNPT SmartVoice API skipped for {audio_ref}. {message}"
    return (
        {"stt_transcript": "", "stt_confidence": 0.0},
        Explanation(label="VNPT SmartVoice API", detail=detail, weight=0),
        failed,
    )


def _smartvision_unconfigured_response(
    image_ref: str,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    message = (
        "VNPT SmartVision is not configured. Set VNPT_SMARTVISION_MODE=real and SmartVision tokens in .env."
    )
    failed = {
        "message": message,
        "object": {},
        "status": "error",
        "provider_mode": "disabled",
    }
    detail = f"VNPT SmartVision API skipped for {image_ref}. {message}"
    return (
        {
            "face_emotion_score": None,
            "face_emotion_labels": [],
        },
        Explanation(label="VNPT SmartVision API", detail=detail, weight=0),
        failed,
    )


def _smartbot_unconfigured_response(
    client_session: str,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    message = (
        "VNPT Smartbot is not configured. Set VNPT_SMARTBOT_MODE=real, Smartbot tokens, "
        "and VNPT_SMARTBOT_BOT_ID in .env."
    )
    failed = {
        "message": message,
        "object": {},
        "status": "error",
        "provider_mode": "disabled",
    }
    detail = f"VNPT Smartbot API skipped for session={client_session}. {message}"
    return (
        {
            "detected_patterns": [],
            "llm_scam_type": None,
            "llm_confidence": None,
        },
        Explanation(label="VNPT Smartbot API", detail=detail, weight=0),
        failed,
    )


def _ekyc_api(
    challenge: ShieldChallengeRequest,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], Explanation, dict[str, dict[str, Any]]]:
    if not vnpt_client.ekyc_enabled:
        return _ekyc_unconfigured_response(challenge.ekyc_image_ref)

    liveness_response = vnpt_client.face_liveness(challenge.ekyc_image_ref, challenge.client_session)
    mask_response = vnpt_client.face_mask(challenge.ekyc_image_ref, challenge.client_session)
    compare_response = vnpt_client.face_compare(
        challenge.ekyc_document_ref,
        challenge.ekyc_image_ref,
        challenge.client_session,
    )
    provider_label = "VNPT eKYC API"
    source_detail = "called VNPT eKYC liveness, mask, and face-compare endpoints"

    liveness_object = _object(liveness_response)
    mask_object = _object(mask_response)
    compare_object = _object(compare_response)

    liveness_failed = _vnpt_call_failed(liveness_response)
    mask_failed = _vnpt_call_failed(mask_response)
    compare_failed = _vnpt_call_failed(compare_response)

    face_is_live = False if liveness_failed else _truthy_provider_bool(liveness_object.get("liveness"))
    mask_detected = False if mask_failed else _truthy_provider_bool(mask_object.get("masked"))
    face_match_score = 0.0 if compare_failed else _provider_score(compare_object.get("prob"), default=0.5)
    face_match_result = str(compare_object.get("result", "")).upper()
    verification_status = "failed"
    if liveness_failed or mask_failed or compare_failed:
        verification_status = "failed"
    elif not face_is_live or mask_detected or face_match_result == "NOMATCH" or face_match_score < 0.5:
        verification_status = "failed"
    elif face_match_score < 0.75:
        verification_status = "review"
    else:
        verification_status = "passed"

    injection_risk = _derive_injection_risk(face_is_live, mask_detected, face_match_score)
    provider_notes = []
    if liveness_failed:
        provider_notes.append(f"liveness: {_vnpt_error_detail(liveness_response)}")
    if mask_failed:
        provider_notes.append(f"mask: {_vnpt_error_detail(mask_response)}")
    if compare_failed:
        provider_notes.append(f"compare: {_vnpt_error_detail(compare_response)}")
    note_suffix = f" Provider notes: {' | '.join(provider_notes)}." if provider_notes else ""
    detail = (
        f"{provider_label} {source_detail} for {challenge.ekyc_image_ref}. "
        f"Status={verification_status}, liveness={liveness_object.get('liveness_msg')}, "
        f"compare={compare_object.get('msg')}.{note_suffix}"
    )

    fields = {
        "ekyc_verification_status": verification_status,
        "ekyc_liveness_passed": face_is_live,
        "ekyc_liveness_score": None,
        "ekyc_mask_detected": mask_detected,
        "ekyc_face_match_score": face_match_score,
        "ekyc_injection_risk_score": injection_risk,
    }
    return (
        fields,
        Explanation(label=provider_label, detail=detail, weight=0),
        {
            "face_liveness": liveness_response,
            "face_mask": mask_response,
            "face_compare": compare_response,
        },
    )


def _stt_transcript_and_confidence(stt_object: dict[str, Any]) -> tuple[str, float]:
    direct = str(stt_object.get("transcript") or "").strip()
    if direct:
        confidence = _stt_confidence_value(stt_object.get("confidence"))
        if confidence <= 0 and stt_object.get("transcript_list"):
            first = stt_object["transcript_list"][0]
            if isinstance(first, dict):
                confidence = _stt_confidence_value(first.get("confidence"))
        return direct, confidence

    results = stt_object.get("results")
    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            alternatives = result.get("alternatives") or []
            for alternative in alternatives:
                if not isinstance(alternative, dict):
                    continue
                transcript = str(alternative.get("transcript") or "").strip()
                if transcript:
                    return transcript, _stt_confidence_value(alternative.get("confidence"))

    alternatives = stt_object.get("transcript_list") or []
    first_alternative = alternatives[0] if alternatives else {}
    if isinstance(first_alternative, dict):
        transcript = str(first_alternative.get("transcript") or "")
        confidence = _stt_confidence_value(first_alternative.get("confidence"))
        return transcript, confidence

    return "", 0.0


def _stt_confidence_value(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number < 0:
        return _bounded_float(abs(number) / 10, default=0.0)
    return _bounded_float(number, default=0.0)


def _smartvoice_api(
    challenge: ShieldChallengeRequest,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    if not vnpt_client.smartvoice_enabled:
        return _smartvoice_unconfigured_response(challenge.stt_audio_ref)

    stt_response = vnpt_client.smartvoice_stt(challenge.stt_audio_ref, challenge.client_session)
    provider_label = "VNPT SmartVoice API"
    source_detail = "called VNPT STT gRPC standard"

    stt_object = _object(stt_response)
    stt_failed = _vnpt_call_failed(stt_response)
    transcript, confidence = ("", 0.0) if stt_failed else _stt_transcript_and_confidence(stt_object)
    if not stt_failed and not transcript.strip():
        stt_failed = True

    provider_notes = []
    if stt_failed:
        provider_notes.append(_vnpt_error_detail(stt_response))
        if not transcript.strip():
            provider_notes.append(
                "STT returned no transcript. Speak clearly in Vietnamese during the live check "
                "(e.g. confirm the transfer in your own words)."
            )
    note_suffix = f" Provider notes: {' | '.join(provider_notes)}." if provider_notes else ""
    detail = (
        f"{provider_label} {source_detail} for {challenge.stt_audio_ref}. "
        f"status={stt_object.get('status')}, duration={stt_object.get('audio_duration')}, "
        f"transcript_len={len(transcript.strip())}, confidence={confidence:.2f}.{note_suffix}"
    )
    return (
        {
            "stt_transcript": transcript,
            "stt_confidence": confidence,
        },
        Explanation(label=provider_label, detail=detail, weight=0),
        stt_response,
    )


def _smartbot_api(
    transcript: str,
    client_session: str,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    if not vnpt_client.smartbot_enabled:
        return _smartbot_unconfigured_response(client_session)

    response = vnpt_client.smartbot_conversation(transcript, client_session)
    provider_label = "VNPT Smartbot API"
    source_detail = "called assistant-stream /v1/conversation"
    smartbot_failed = _vnpt_call_failed(response)

    classification = parse_smartbot_response(response, transcript)
    if smartbot_failed:
        keyword_match = match_transcript_pattern(transcript.lower())
        scam_type = keyword_match[0] if keyword_match else None
        classification = type(classification)(
            llm_scam_type=scam_type,
            detected_patterns=detected_patterns_for_challenge(scam_type),
            llm_confidence=0.75 if scam_type else None,
            reply_text=classification.reply_text,
            intent_name=classification.intent_name,
            parse_source="keyword_fallback_after_error",
        )

    provider_notes = []
    if smartbot_failed:
        provider_notes.append(_vnpt_error_detail(response))
    note_suffix = f" Provider notes: {' | '.join(provider_notes)}." if provider_notes else ""
    detail = (
        f"{provider_label} {source_detail} for session={client_session}. "
        f"parse={classification.parse_source}, scam_type={classification.llm_scam_type}, "
        f"confidence={classification.llm_confidence}, intent={classification.intent_name}."
    )
    if classification.reply_text:
        preview = classification.reply_text.replace("\n", " ")[:180]
        detail += f" reply={preview!r}."
    detail += note_suffix

    return (
        {
            "detected_patterns": classification.detected_patterns,
            "llm_scam_type": classification.llm_scam_type,
            "llm_confidence": classification.llm_confidence,
        },
        Explanation(label=provider_label, detail=detail, weight=0),
        response,
    )


def _smartvision_frame_refs(challenge: ShieldChallengeRequest) -> list[str]:
    refs: list[str] = []
    for candidate in [challenge.ekyc_image_ref, *challenge.challenge_frame_refs]:
        normalized = str(candidate).strip()
        if normalized and normalized not in refs:
            refs.append(normalized)
    return refs


def _smartvision_api(
    challenge: ShieldChallengeRequest,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], Explanation, dict[str, Any]]:
    frame_refs = _smartvision_frame_refs(challenge)
    primary_ref = frame_refs[0] if frame_refs else challenge.ekyc_image_ref

    if not vnpt_client.smartvision_enabled:
        return _smartvision_unconfigured_response(primary_ref)

    provider_label = "VNPT SmartVision API"
    source_detail = f"called {vnpt_client.settings.vnpt_smartvision_detect_face_path}"
    parsed_frames: list[SmartvisionFaceEmotion] = []
    frame_responses: list[dict[str, Any]] = []
    provider_notes: list[str] = []
    any_success = False

    for frame_ref in frame_refs:
        response = vnpt_client.smartvision_detect_face(frame_ref, challenge.client_session)
        frame_responses.append({"frame_ref": frame_ref, "response": response})
        frame_failed = _vnpt_call_failed(response)
        if frame_failed:
            provider_notes.append(f"{frame_ref}: {_vnpt_error_detail(response)}")
            parsed_frames.append(
                SmartvisionFaceEmotion(
                    face_emotion_score=None,
                    face_emotion_labels=[],
                    dominant_emotion=None,
                    parse_source="error",
                )
            )
            continue

        any_success = True
        parsed = parse_smartvision_face_emotion(response)
        parsed_frames.append(parsed)
        if parsed.face_emotion_score is None:
            provider_notes.append(f"{frame_ref}: response did not include a usable emotion score")

    parsed = aggregate_smartvision_frames(parsed_frames)
    smartvision_failed = not any_success

    note_suffix = f" Provider notes: {' | '.join(provider_notes)}." if provider_notes else ""
    frame_summary = f"{len(frame_refs)} frame(s)" if len(frame_refs) > 1 else primary_ref
    detail = (
        f"{provider_label} {source_detail} on {frame_summary}. "
        f"parse={parsed.parse_source}, dominant={parsed.dominant_emotion}, "
        f"score={parsed.face_emotion_score}, labels={parsed.face_emotion_labels}.{note_suffix}"
    )

    combined_raw: dict[str, Any] = {
        "frame_count": len(frame_refs),
        "frames": frame_responses,
    }
    if len(frame_responses) == 1:
        combined_raw["primary"] = frame_responses[0]["response"]

    return (
        {
            "face_emotion_score": parsed.face_emotion_score,
            "face_emotion_labels": parsed.face_emotion_labels,
        },
        Explanation(label=provider_label, detail=detail, weight=0),
        combined_raw,
    )


def _coercion_api(
    stt_audio_ref: str,
    stt_transcript: str = "",
    llm_scam_type: str | None = None,
    face_emotion_score: object = None,
    face_emotion_labels: object = None,
) -> tuple[dict[str, object], Explanation, dict[str, object]]:
    settings = get_settings()
    voice_result = analyze_voice_stress(stt_audio_ref, settings)

    stt_failed = not _stt_passed(stt_transcript)
    scripted_score, scripted_labels = _scripted_behavior(stt_transcript, stt_failed, llm_scam_type)
    face_score = float(face_emotion_score) if isinstance(face_emotion_score, (int, float)) else 0.0
    face_labels = (
        [str(item) for item in face_emotion_labels if str(item).strip()]
        if isinstance(face_emotion_labels, list)
        else []
    )

    if isinstance(face_emotion_score, (int, float)):
        voice_weight, face_weight, scripted_weight = 0.5, 0.25, 0.25
    else:
        voice_weight, face_weight, scripted_weight = 0.625, 0.0, 0.375

    coercion_score = round(
        voice_weight * voice_result.voice_stress_score
        + face_weight * face_score
        + scripted_weight * scripted_score,
        3,
    )
    coercion_confidence = round(0.82 if voice_result.model_used else 0.68, 3)

    face_detail = (
        f"face={face_score:.2f}"
        if isinstance(face_emotion_score, (int, float))
        else "face=skipped"
    )
    detail = (
        f"{voice_result.detail} "
        f"Fusion coercion={coercion_score:.2f} "
        f"({face_detail}, scripted={scripted_score:.2f})."
    )
    provider_label = "Voice stress analyzer"
    if voice_result.model_used and voice_result.model_backend == "emotion2vec":
        provider_label = f"Voice stress analyzer (emotion2vec + prosody, locale={voice_result.locale})"
    elif voice_result.model_used:
        provider_label = "Voice stress analyzer (wav2vec arousal + prosody)"

    raw = {
        "voice_stress_score": voice_result.voice_stress_score,
        "voice_stress_labels": voice_result.voice_stress_labels,
        "arousal": voice_result.arousal,
        "valence": voice_result.valence,
        "dominance": voice_result.dominance,
        "distress_score": voice_result.distress_score,
        "top_emotions": voice_result.top_emotions,
        "locale": voice_result.locale,
        "model_backend": voice_result.model_backend,
        "model_used": voice_result.model_used,
        "model_name": voice_result.model_name,
        "prosody": {
            "f0_mean_hz": voice_result.prosody.f0_mean_hz,
            "f0_std_hz": voice_result.prosody.f0_std_hz,
            "pause_ratio": voice_result.prosody.pause_ratio,
            "long_pause_count": voice_result.prosody.long_pause_count,
            "speech_rate_syms_per_s": voice_result.prosody.speech_rate_syms_per_s,
            "prosody_stress_score": voice_result.prosody.prosody_stress_score,
        },
        **voice_result.raw,
    }

    return (
        {
            "voice_stress_score": voice_result.voice_stress_score,
            "voice_stress_labels": voice_result.voice_stress_labels,
            "scripted_behavior_score": scripted_score,
            "scripted_behavior_labels": scripted_labels,
            "coercion_score": coercion_score,
            "coercion_confidence": coercion_confidence,
        },
        Explanation(label=provider_label, detail=detail, weight=0),
        raw,
    )


def _scripted_behavior(
    stt_transcript: str,
    stt_failed: bool,
    llm_scam_type: str | None = None,
) -> tuple[float, list[str]]:
    if llm_scam_type:
        return 0.81, ["monotone_reading", "repeats_caller_phrasing"]
    if stt_failed:
        return 0.81, ["monotone_reading", "repeats_caller_phrasing"]
    if match_transcript_pattern(stt_transcript.lower()):
        return 0.74, ["repeats_caller_phrasing"]
    return 0.12, ["free_response"]
