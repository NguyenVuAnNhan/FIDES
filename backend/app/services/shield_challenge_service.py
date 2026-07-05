"""Path B transfer monitoring: in-app camera/voice challenge via VNPT."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import get_settings
from backend.app.models import Explanation, ShieldAnalyzeResponse, ShieldChallengeRequest
from backend.app.services.shield_service import analyze_shield_risk, match_transcript_pattern
from backend.app.services.vnpt_client import VnptClient

VNPT_MOCK_DIR = Path(__file__).resolve().parents[1] / "data" / "vnpt_mocks"


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
        challenge.stt_audio_ref,
        vnpt_client.smartvoice_enabled,
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


# Backward-compatible alias
run_mock_camera_voice_challenge = run_transfer_monitoring_challenge


def _run_challenge_apis(
    challenge: ShieldChallengeRequest,
    vnpt_client: VnptClient,
) -> tuple[dict[str, object], list[Explanation], dict[str, dict[str, Any]], str]:
    provider_mode = vnpt_client.mode
    ekyc_fields, ekyc_call, ekyc_raw = _ekyc_api(challenge, vnpt_client)
    smartvoice_fields, smartvoice_call, smartvoice_raw = _smartvoice_api(challenge, vnpt_client)
    smartbot_fields, smartbot_call = _mock_smartbot_api(str(smartvoice_fields["stt_transcript"]))
    coercion_fields, coercion_call = _mock_coercion_api(
        str(ekyc_fields["ekyc_verification_status"]),
        challenge.stt_audio_ref,
        str(smartvoice_fields["stt_transcript"]),
        vnpt_client.smartvoice_enabled,
    )

    fields = {
        "consent_granted": True,
        "consent_transfer_check": True,
        "consent_call_monitoring": False,
        "shield_path": "transfer_monitoring",
        "audio_source": challenge.stt_audio_ref,
        **ekyc_fields,
        **smartvoice_fields,
        **smartbot_fields,
        **coercion_fields,
        "transcript": smartvoice_fields["stt_transcript"],
    }
    raw_responses = {
        "ekyc_face_liveness": ekyc_raw["face_liveness"],
        "ekyc_face_mask": ekyc_raw["face_mask"],
        "ekyc_face_compare": ekyc_raw["face_compare"],
        "smartvoice_stt": smartvoice_raw,
    }
    return fields, [ekyc_call, smartvoice_call, smartbot_call, coercion_call], raw_responses, provider_mode


def _challenge_profile_from_results(
    ekyc_verification_status: str,
    stt_transcript: str,
    stt_audio_ref: str,
    smartvoice_real: bool,
) -> str:
    ekyc_passed = ekyc_verification_status == "passed"
    stt_passed = _stt_passed(stt_transcript, stt_audio_ref, smartvoice_real)
    if ekyc_passed and stt_passed:
        return "clear_user"
    if not ekyc_passed and stt_passed:
        return "ekyc_failed"
    if ekyc_passed and not stt_passed:
        return "stt_failed"
    return "ekyc_and_stt_failed"


def _stt_passed(stt_transcript: str, stt_audio_ref: str, smartvoice_real: bool) -> bool:
    if smartvoice_real:
        if not stt_transcript.strip():
            return False
        return match_transcript_pattern(stt_transcript.lower()) is None
    return _artifact_name(stt_audio_ref) == "stt_audio_1"


def _artifact_name(ref: str) -> str:
    return ref.rstrip("/").split("/")[-1]


def _load_vnpt_mock(product: str, filename: str) -> dict[str, Any]:
    path = VNPT_MOCK_DIR / product / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "message": "Mock response not found",
        "object": {},
        "error": {"mock_path": str(path)},
    }


def _object(response: dict[str, Any]) -> dict[str, Any]:
    value = response.get("object", {})
    if isinstance(value, dict):
        return value
    return {}


def _vnpt_call_failed(response: dict[str, Any]) -> bool:
    if response.get("status") == "error":
        return True
    provider_status = str(response.get("status", "")).upper()
    if provider_status in {"BAD_REQUEST", "ERROR", "FAIL", "FAILED"}:
        return True
    status_code = response.get("statusCode")
    if isinstance(status_code, int) and status_code >= 400:
        return True
    if isinstance(status_code, str) and status_code.isdigit() and int(status_code) >= 400:
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
    results = stt_object.get("results")
    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            alternatives = result.get("alternatives") or []
            if alternatives and isinstance(alternatives[0], dict):
                first = alternatives[0]
                transcript = str(first.get("transcript") or "")
                confidence = _stt_confidence_value(first.get("confidence"))
                if transcript:
                    return transcript, confidence

    alternatives = stt_object.get("transcript_list") or []
    first_alternative = alternatives[0] if alternatives else {}
    if isinstance(first_alternative, dict):
        transcript = str(stt_object.get("transcript") or first_alternative.get("transcript") or "")
        confidence = _stt_confidence_value(first_alternative.get("confidence"))
        return transcript, confidence

    return str(stt_object.get("transcript") or ""), 0.0


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
    if vnpt_client.smartvoice_enabled:
        stt_response = vnpt_client.smartvoice_stt(challenge.stt_audio_ref, challenge.client_session)
        provider_label = "VNPT SmartVoice API"
        source_detail = "called VNPT STT gRPC standard"
    else:
        artifact = _artifact_name(challenge.stt_audio_ref)
        stt_response = _load_vnpt_mock("smartvoice", f"{artifact}_stt.json")
        provider_label = "Mock SmartVoice API"
        source_detail = "loaded VNPT-like STT response"

    stt_object = _object(stt_response)
    stt_failed = _vnpt_call_failed(stt_response)
    transcript, confidence = ("", 0.0) if stt_failed else _stt_transcript_and_confidence(stt_object)
    if not stt_failed and not transcript.strip():
        stt_failed = True

    provider_notes = []
    if stt_failed:
        provider_notes.append(_vnpt_error_detail(stt_response))
    note_suffix = f" Provider notes: {' | '.join(provider_notes)}." if provider_notes else ""
    detail = (
        f"{provider_label} {source_detail} for {challenge.stt_audio_ref}. "
        f"status={stt_object.get('status')}, duration={stt_object.get('audio_duration')}, "
        f"confidence={confidence:.2f}.{note_suffix}"
    )
    return (
        {
            "stt_transcript": transcript,
            "stt_confidence": confidence,
        },
        Explanation(label=provider_label, detail=detail, weight=0),
        stt_response,
    )


def _mock_smartbot_api(transcript: str) -> tuple[dict[str, object], Explanation]:
    scam_type = None
    transcript_match = match_transcript_pattern(transcript.lower())
    if transcript_match:
        scam_type = transcript_match[0]

    detected_patterns = detected_patterns_for_challenge(scam_type)
    confidence = 0.91 if scam_type else None

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


def _mock_coercion_api(
    ekyc_verification_status: str,
    stt_audio_ref: str,
    stt_transcript: str = "",
    smartvoice_enabled: bool = False,
) -> tuple[dict[str, object], Explanation]:
    stt_failed = not _stt_passed(stt_transcript, stt_audio_ref, smartvoice_enabled)
    ekyc_failed = ekyc_verification_status not in {"passed", "review"}
    if stt_failed:
        selected = {
            "voice": 0.83,
            "voice_labels": ["elevated_pitch", "speech_hesitation"],
            "face": 0.77 if not ekyc_failed else 0.68,
            "face_labels": ["fear", "low_eye_contact"],
            "scripted": 0.81,
            "scripted_labels": ["monotone_reading", "repeats_caller_phrasing"],
            "coercion": 0.84,
            "confidence": 0.86,
            "detail": f"Mock coercion API used {stt_audio_ref} and found distress plus scripted behavior.",
        }
    elif ekyc_failed:
        selected = {
            "voice": 0.28,
            "voice_labels": ["steady_voice"],
            "face": 0.46,
            "face_labels": ["visual_artifact"],
            "scripted": 0.18,
            "scripted_labels": [],
            "coercion": 0.22,
            "confidence": 0.78,
            "detail": "Mock coercion API found biometric verification failure without coercion signals.",
        }
    else:
        selected = {
            "voice": 0.18,
            "voice_labels": ["steady_voice"],
            "face": 0.16,
            "face_labels": ["calm"],
            "scripted": 0.12,
            "scripted_labels": ["free_response"],
            "coercion": 0.14,
            "confidence": 0.82,
            "detail": f"Mock coercion API used {stt_audio_ref}; no distress pattern found.",
        }
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


def detected_patterns_for_challenge(scam_type: str | None) -> list[str]:
    if scam_type == "fake_authority":
        return [
            "fake_authority",
            "case_involvement",
            "transfer_for_verification",
            "secrecy_pressure",
        ]
    if scam_type == "remote_support":
        return [
            "remote_support",
            "screen_control",
            "refund_promise",
            "transfer_test",
        ]
    return [scam_type] if scam_type else []
