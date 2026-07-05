from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from backend.app.services.shield_service import detected_patterns_for_challenge, match_transcript_pattern

SAFE_INTENT_HINTS = {"safe", "clear", "benign", "normal", "ok", "pass", "passed"}
SCAM_INTENT_ALIASES = {
    "fake_authority": ("fake_authority", "authority", "cong_an", "police"),
    "remote_support": ("remote_support", "remote", "screen"),
    "otp_theft": ("otp_theft", "otp"),
    "investment": ("investment", "invest"),
}


@dataclass(frozen=True)
class SmartbotClassification:
    llm_scam_type: str | None
    detected_patterns: list[str]
    llm_confidence: float | None
    reply_text: str
    intent_name: str | None
    parse_source: str


def parse_smartbot_response(response: dict[str, Any], transcript: str) -> SmartbotClassification:
    card_texts, intent_name = _extract_sb_payload(response)
    reply_text = "\n".join(text for text in card_texts if text.strip()).strip()

    structured = _parse_structured_json(reply_text)
    if structured is not None:
        scam_type = structured.get("scam_type") or structured.get("llm_scam_type")
        if structured.get("safe") is True:
            scam_type = None
        patterns = _normalize_patterns(structured.get("detected_patterns"))
        confidence = _normalize_confidence(structured.get("confidence") or structured.get("llm_confidence"))
        if scam_type and not patterns:
            patterns = detected_patterns_for_challenge(str(scam_type))
        return SmartbotClassification(
            llm_scam_type=str(scam_type) if scam_type else None,
            detected_patterns=patterns,
            llm_confidence=confidence,
            reply_text=reply_text,
            intent_name=intent_name,
            parse_source="json",
        )

    mapped = _map_intent_name(intent_name)
    if mapped is not None:
        return SmartbotClassification(
            llm_scam_type=mapped,
            detected_patterns=detected_patterns_for_challenge(mapped),
            llm_confidence=0.88,
            reply_text=reply_text,
            intent_name=intent_name,
            parse_source="intent_name",
        )

    keyword_source = f"{transcript}\n{reply_text}".lower()
    transcript_match = match_transcript_pattern(keyword_source)
    if transcript_match:
        scam_type = transcript_match[0]
        return SmartbotClassification(
            llm_scam_type=scam_type,
            detected_patterns=detected_patterns_for_challenge(scam_type),
            llm_confidence=0.75,
            reply_text=reply_text,
            intent_name=intent_name,
            parse_source="keyword_fallback",
        )

    return SmartbotClassification(
        llm_scam_type=None,
        detected_patterns=[],
        llm_confidence=None,
        reply_text=reply_text,
        intent_name=intent_name,
        parse_source="none",
    )


def _extract_sb_payload(response: dict[str, Any]) -> tuple[list[str], str | None]:
    root = response.get("object")
    if not isinstance(root, dict):
        return [], None

    sb = root.get("sb")
    if not isinstance(sb, dict):
        sb = root

    card_data = sb.get("card_data")
    texts: list[str] = []
    if isinstance(card_data, list):
        for item in card_data:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "chuyen_gdv":
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())

    intent_name = sb.get("intent_name")
    return texts, str(intent_name) if intent_name else None


def _parse_structured_json(text: str) -> dict[str, Any] | None:
    if not text.strip():
        return None

    candidates = [text.strip()]
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidates.insert(0, fence_match.group(1))
    brace_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _map_intent_name(intent_name: str | None) -> str | None:
    if not intent_name:
        return None
    normalized = intent_name.strip().lower()
    if any(hint in normalized for hint in SAFE_INTENT_HINTS):
        return None
    for scam_type, aliases in SCAM_INTENT_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return scam_type
    return None


def _normalize_patterns(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _normalize_confidence(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))
