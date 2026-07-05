"""In-app session monitoring for Shield Path B (context from app entry)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from backend.app.models import Explanation, ShieldAnalyzeRequest, ShieldSessionHeartbeatRequest, ShieldSessionHeartbeatResponse
from backend.app.services.shield_service import (
    _has_suspicious_prefix,
    _is_international_number,
    _smartux_weight,
)

SESSION_TTL_SECONDS = 2 * 60 * 60
SESSION_ELEVATED_THRESHOLD = 45


@dataclass
class ShieldSessionState:
    sdk_session_id: str
    created_at: float
    updated_at: float
    call_active_during_session: bool = False
    caller_type: str = "unknown"
    caller_number: str = ""
    remote_control_detected: bool = False
    installed_remote_access_app_detected: bool = False
    accessibility_service_risk: bool = False
    screen_sharing_detected: bool = False
    smartux_behavior_anomaly_score: float | None = None
    smartux_remote_control_score: float | None = None
    smartux_signals: list[str] = field(default_factory=list)
    session_risk_score: int = 10
    session_flags: list[Explanation] = field(default_factory=list)
    heartbeat_count: int = 0


_sessions: dict[str, ShieldSessionState] = {}


def process_session_heartbeat(request: ShieldSessionHeartbeatRequest) -> ShieldSessionHeartbeatResponse:
    now = time.time()
    _purge_expired_sessions(now)
    session = _sessions.get(request.sdk_session_id)
    if session is None:
        session = ShieldSessionState(
            sdk_session_id=request.sdk_session_id,
            created_at=now,
            updated_at=now,
        )
        _sessions[request.sdk_session_id] = session

    session.updated_at = now
    session.heartbeat_count += 1

    if request.active_call:
        session.call_active_during_session = True
        if request.caller_type and request.caller_type != "unknown":
            session.caller_type = request.caller_type
        if request.caller_number:
            session.caller_number = request.caller_number

    session.remote_control_detected = session.remote_control_detected or request.remote_control_detected
    session.installed_remote_access_app_detected = (
        session.installed_remote_access_app_detected or request.installed_remote_access_app_detected
    )
    session.accessibility_service_risk = session.accessibility_service_risk or request.accessibility_service_risk
    session.screen_sharing_detected = session.screen_sharing_detected or request.screen_sharing_detected

    if request.smartux_behavior_anomaly_score is not None:
        current = session.smartux_behavior_anomaly_score or 0.0
        session.smartux_behavior_anomaly_score = max(current, request.smartux_behavior_anomaly_score)
    if request.smartux_remote_control_score is not None:
        current = session.smartux_remote_control_score or 0.0
        session.smartux_remote_control_score = max(current, request.smartux_remote_control_score)
    if request.smartux_signals:
        session.smartux_signals = sorted(set(session.smartux_signals + request.smartux_signals))

    score, flags = _score_session_context(session, request.active_call)
    session.session_risk_score = score
    session.session_flags = flags

    return ShieldSessionHeartbeatResponse(
        sdk_session_id=session.sdk_session_id,
        session_risk_score=score,
        risk_level=_risk_level_for_score(score),
        call_active_during_session=session.call_active_during_session,
        call_active_now=request.active_call,
        heartbeat_count=session.heartbeat_count,
        session_age_seconds=max(0, int(now - session.created_at)),
        explanations=flags,
        early_warning=score >= SESSION_ELEVATED_THRESHOLD,
        intervention_message=_build_session_intervention_message(score, session.call_active_during_session),
    )


def merge_session_context(request: ShieldAnalyzeRequest) -> ShieldAnalyzeRequest:
    session_id = (request.sdk_session_id or "").strip()
    if not session_id:
        return request

    _purge_expired_sessions(time.time())
    session = _sessions.get(session_id)
    if session is None:
        return request

    updates: dict[str, object] = {}

    if session.call_active_during_session and not request.active_call:
        updates["active_call"] = True
    if not request.caller_number and session.caller_number:
        updates["caller_number"] = session.caller_number
    if request.caller_type == "unknown" and session.caller_type != "unknown":
        updates["caller_type"] = session.caller_type
    if session.remote_control_detected:
        updates["remote_control_detected"] = True
    if session.installed_remote_access_app_detected:
        updates["installed_remote_access_app_detected"] = True
    if session.accessibility_service_risk:
        updates["accessibility_service_risk"] = True
    if session.screen_sharing_detected:
        updates["screen_sharing_detected"] = True
    if session.smartux_behavior_anomaly_score is not None and request.smartux_behavior_anomaly_score is None:
        updates["smartux_behavior_anomaly_score"] = session.smartux_behavior_anomaly_score
    if session.smartux_remote_control_score is not None and request.smartux_remote_control_score is None:
        updates["smartux_remote_control_score"] = session.smartux_remote_control_score
    if session.smartux_signals and not request.smartux_signals:
        updates["smartux_signals"] = list(session.smartux_signals)

    if not updates:
        return request
    return request.model_copy(update=updates)


def _score_session_context(session: ShieldSessionState, call_active_now: bool) -> tuple[int, list[Explanation]]:
    score = 10
    explanations: list[Explanation] = []

    if call_active_now or session.call_active_during_session:
        score += 20
        detail = "A phone call was active during this app session."
        if session.call_active_during_session and not call_active_now:
            detail += " The call ended, but Shield still treats it as session context."
        explanations.append(
            Explanation(
                label="Active call during app session",
                detail=detail,
                weight=20,
            )
        )

    caller_type = session.caller_type
    if caller_type in {"voip", "international", "unknown"}:
        score += 10
        explanations.append(
            Explanation(
                label="Caller context (session)",
                detail=f"The caller type observed this session is {caller_type}.",
                weight=10,
            )
        )

    if session.caller_number and _is_international_number(session.caller_number):
        score += 10
        explanations.append(
            Explanation(
                label="International caller (session)",
                detail=f"The caller number {session.caller_number} is outside the local +84 context.",
                weight=10,
            )
        )

    if session.caller_number and _has_suspicious_prefix(session.caller_number):
        score += 10
        explanations.append(
            Explanation(
                label="Suspicious caller prefix (session)",
                detail=f"The caller number {session.caller_number} matches a high-risk demo prefix rule.",
                weight=10,
            )
        )

    if session.remote_control_detected:
        score += 20
        explanations.append(
            Explanation(
                label="Remote-control signal (session)",
                detail="Remote-support or screen-control telemetry was seen during this app session.",
                weight=20,
            )
        )

    smartux_weight = _smartux_weight_from_session(session)
    if smartux_weight:
        score += smartux_weight
        explanations.append(
            Explanation(
                label="SmartUX session telemetry",
                detail="Native telemetry during this app session raised the session risk score.",
                weight=smartux_weight,
            )
        )

    if session.heartbeat_count >= 2:
        explanations.append(
            Explanation(
                label="App session monitoring",
                detail=(
                    f"Shield has tracked this app session since launch "
                    f"({session.heartbeat_count} heartbeats)."
                ),
                weight=0,
            )
        )

    return min(score, 100), explanations


def _smartux_weight_from_session(session: ShieldSessionState) -> int:
    request = ShieldAnalyzeRequest(
        transaction_amount=0,
        recipient_name="session",
        recipient_account="session",
        smartux_behavior_anomaly_score=session.smartux_behavior_anomaly_score,
        smartux_remote_control_score=session.smartux_remote_control_score,
        smartux_signals=session.smartux_signals,
        remote_control_detected=session.remote_control_detected,
    )
    return _smartux_weight(request)


def _risk_level_for_score(score: int) -> str:
    if score >= SESSION_ELEVATED_THRESHOLD:
        return "elevated"
    if score >= 30:
        return "moderate"
    return "low"


def _build_session_intervention_message(score: int, call_during_session: bool) -> str:
    if score >= SESSION_ELEVATED_THRESHOLD:
        if call_during_session:
            return (
                "FIDES detected elevated risk while you are using the app — "
                "including an active or recent phone call. Extra verification may be required if you transfer money."
            )
        return (
            "FIDES detected elevated device or session risk while you are using the app. "
            "Extra verification may be required if you transfer money."
        )
    if call_during_session:
        return "FIDES is monitoring your app session. A phone call is active or was active recently."
    return "FIDES is monitoring your app session in the background."


def _purge_expired_sessions(now: float) -> None:
    expired = [
        session_id
        for session_id, session in _sessions.items()
        if now - session.updated_at > SESSION_TTL_SECONDS
    ]
    for session_id in expired:
        _sessions.pop(session_id, None)
