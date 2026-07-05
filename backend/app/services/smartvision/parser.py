from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DISTRESS_EMOTIONS = {
    "fear",
    "sad",
    "sadness",
    "angry",
    "anger",
    "disgust",
    "surprise",
    "stress",
    "distress",
    "anxious",
    "anxiety",
    "worried",
    "worry",
    "tense",
    "tension",
    "panic",
    "frustrated",
    "frustration",
}

CALM_EMOTIONS = {"happy", "happiness", "neutral", "calm", "relaxed", "joy"}

LABEL_ALIASES = {
    "fear": "fear",
    "sad": "distress",
    "sadness": "distress",
    "angry": "distress",
    "anger": "distress",
    "disgust": "distress",
    "surprise": "distress",
    "stress": "distress",
    "distress": "distress",
    "anxious": "fear",
    "anxiety": "fear",
    "worried": "fear",
    "worry": "fear",
    "tense": "distress",
    "tension": "distress",
    "panic": "fear",
    "frustrated": "distress",
    "frustration": "distress",
    "low_eye_contact": "low_eye_contact",
    "eye_closed": "low_eye_contact",
    "eyes_closed": "low_eye_contact",
}


@dataclass(frozen=True)
class SmartvisionFaceEmotion:
    face_emotion_score: float | None
    face_emotion_labels: list[str]
    dominant_emotion: str | None
    parse_source: str


METADATA_KEYS = {
    "http_status",
    "statuscode",
    "status",
    "message",
    "error",
    "provider_mode",
    "messageobjects",
    "messagefields",
}


def parse_smartvision_face_emotion(response: dict[str, Any]) -> SmartvisionFaceEmotion:
    obj = response.get("object")
    if not isinstance(obj, dict) or not obj:
        return SmartvisionFaceEmotion(
            face_emotion_score=None,
            face_emotion_labels=[],
            dominant_emotion=None,
            parse_source="empty",
        )

    direct_score = _first_score(
        obj,
        (
            "distress_score",
            "stress_score",
            "face_emotion_score",
            "emotion_score",
            "score",
            "prob",
            "probability",
        ),
    )
    if direct_score is not None:
        labels = _normalize_labels(obj.get("labels") or obj.get("face_emotion_labels"))
        dominant = _normalize_label(obj.get("dominant_emotion") or obj.get("emotion"))
        if dominant and not labels:
            labels = [_label_for_emotion(dominant)]
        return SmartvisionFaceEmotion(
            face_emotion_score=direct_score,
            face_emotion_labels=labels,
            dominant_emotion=dominant,
            parse_source="direct_score",
        )

    emotion_scores = _collect_emotion_scores(obj)
    if not emotion_scores:
        return SmartvisionFaceEmotion(
            face_emotion_score=None,
            face_emotion_labels=[],
            dominant_emotion=None,
            parse_source="empty",
        )

    dominant, dominant_score = max(emotion_scores.items(), key=lambda item: item[1])
    distress_score = _distress_score(emotion_scores)
    labels = _labels_from_scores(emotion_scores)
    if dominant in DISTRESS_EMOTIONS and _label_for_emotion(dominant) not in labels:
        labels.insert(0, _label_for_emotion(dominant))

    return SmartvisionFaceEmotion(
        face_emotion_score=round(distress_score if distress_score is not None else dominant_score, 3),
        face_emotion_labels=labels,
        dominant_emotion=dominant,
        parse_source="emotion_map",
    )


def _collect_emotion_scores(obj: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}

    for key, value in obj.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in METADATA_KEYS:
            continue
        if normalized_key in {"labels", "face_emotion_labels", "dominant_emotion", "emotion"}:
            continue
        score = _normalize_score(value)
        if score is None:
            continue
        if normalized_key.endswith("_score"):
            normalized_key = normalized_key[: -len("_score")]
        if normalized_key.endswith("_prob"):
            normalized_key = normalized_key[: -len("_prob")]
        scores[normalized_key] = score

    for container_key in ("emotions", "emotion_list", "expression", "expressions", "results"):
        container = obj.get(container_key)
        if isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                label = item.get("label") or item.get("emotion") or item.get("name")
                score = _normalize_score(item.get("score") or item.get("prob") or item.get("confidence"))
                if label and score is not None:
                    scores[str(label).strip().lower()] = score
        elif isinstance(container, dict):
            for label, score_value in container.items():
                score = _normalize_score(score_value)
                if score is not None:
                    scores[str(label).strip().lower()] = score

    nested = obj.get("face") or obj.get("data")
    if isinstance(nested, dict):
        scores.update(_collect_emotion_scores(nested))

    return scores


def _distress_score(emotion_scores: dict[str, float]) -> float | None:
    weighted: list[float] = []
    for label, score in emotion_scores.items():
        if label in DISTRESS_EMOTIONS:
            weighted.append(score)
        elif label in CALM_EMOTIONS:
            weighted.append(max(0.0, 1.0 - score) * 0.35)
    if not weighted:
        return None
    return max(0.0, min(1.0, max(weighted)))


def _labels_from_scores(emotion_scores: dict[str, float]) -> list[str]:
    labels: list[str] = []
    for label, score in sorted(emotion_scores.items(), key=lambda item: item[1], reverse=True):
        if score < 0.35:
            continue
        if label in DISTRESS_EMOTIONS or label in {"low_eye_contact", "eye_closed", "eyes_closed"}:
            mapped = _label_for_emotion(label)
            if mapped not in labels:
                labels.append(mapped)
    return labels[:4]


def _label_for_emotion(label: str) -> str:
    normalized = label.strip().lower()
    return LABEL_ALIASES.get(normalized, normalized)


def _normalize_labels(value: object) -> list[str]:
    if isinstance(value, list):
        return [_label_for_emotion(str(item)) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [_label_for_emotion(part) for part in value.split(",") if part.strip()]
    return []


def _normalize_label(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _first_score(obj: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        score = _normalize_score(obj.get(key))
        if score is not None:
            return score
    return None


def _normalize_score(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))
