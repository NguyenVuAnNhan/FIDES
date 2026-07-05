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
    "multiple_faces": "multiple_faces",
    "no_face_detected": "no_face_detected",
    "visual_artifact": "visual_artifact",
}

METADATA_KEYS = {
    "http_status",
    "statuscode",
    "status",
    "message",
    "error",
    "provider_mode",
    "messageobjects",
    "messagefields",
    "id",
    "time",
    "smartvision_client_session",
    "smartvision_image_url",
}


@dataclass(frozen=True)
class SmartvisionFaceEmotion:
    face_emotion_score: float | None
    face_emotion_labels: list[str]
    dominant_emotion: str | None
    parse_source: str


def parse_smartvision_face_emotion(response: dict[str, Any]) -> SmartvisionFaceEmotion:
    obj = response.get("object")
    if not isinstance(obj, dict) or not obj:
        return _empty_result("empty")

    info = _extract_detect_face_info(obj)
    if isinstance(info, dict):
        return _parse_detect_face_info(info)

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
        return _empty_result("empty")

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


def _extract_detect_face_info(obj: dict[str, Any]) -> dict[str, Any] | None:
    info = obj.get("info")
    if isinstance(info, dict) and any(key in info for key in ("face_bboxs", "face_scores", "face_landmarks")):
        return info

    message = obj.get("message")
    if isinstance(message, dict):
        nested_info = message.get("info")
        if isinstance(nested_info, dict):
            return nested_info
    return None


def _parse_detect_face_info(info: dict[str, Any]) -> SmartvisionFaceEmotion:
    bboxes = info.get("face_bboxs") or []
    scores = _flatten_nested_scores(info.get("face_scores"))
    landmarks = info.get("face_landmarks") or []
    face_count = len(bboxes) if isinstance(bboxes, list) and bboxes else len(scores)

    if face_count == 0:
        return SmartvisionFaceEmotion(
            face_emotion_score=0.72,
            face_emotion_labels=["no_face_detected"],
            dominant_emotion="no_face_detected",
            parse_source="detect_face",
        )

    labels: list[str] = []
    distress = 0.22
    top_score = max(scores) if scores else 0.0

    if face_count > 1:
        labels.append("multiple_faces")
        distress = max(distress, 0.58)

    if top_score < 0.45:
        labels.append("visual_artifact")
        distress = max(distress, 0.62)

    if isinstance(landmarks, list) and landmarks:
        first_landmarks = landmarks[0]
        if _landmarks_suggest_low_eye_contact(first_landmarks, bboxes[0] if bboxes else None):
            labels.append("low_eye_contact")
            distress = max(distress, 0.55)

    if not labels:
        labels = ["calm"]
        distress = min(distress, 0.24)

    dominant = "calm"
    if face_count > 1:
        dominant = "multiple_faces"
    elif top_score < 0.45:
        dominant = "visual_artifact"
    elif "low_eye_contact" in labels:
        dominant = "low_eye_contact"

    return SmartvisionFaceEmotion(
        face_emotion_score=round(distress, 3),
        face_emotion_labels=labels,
        dominant_emotion=dominant,
        parse_source="detect_face",
    )


def _flatten_nested_scores(value: object) -> list[float]:
    scores: list[float] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, list):
                for nested in item:
                    normalized = _normalize_score(nested)
                    if normalized is not None:
                        scores.append(normalized)
            else:
                normalized = _normalize_score(item)
                if normalized is not None:
                    scores.append(normalized)
    else:
        normalized = _normalize_score(value)
        if normalized is not None:
            scores.append(normalized)
    return scores


def _landmarks_suggest_low_eye_contact(landmarks: object, bbox: object) -> bool:
    if not isinstance(landmarks, list) or len(landmarks) < 2:
        return False

    points: list[tuple[float, float]] = []
    for item in landmarks:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                points.append((float(item[0]), float(item[1])))
            except (TypeError, ValueError):
                continue
    if len(points) < 2:
        return False

    eye_delta_y = abs(points[0][1] - points[1][1])
    face_height = 1.0
    if isinstance(bbox, list) and len(bbox) >= 4:
        try:
            face_height = max(float(bbox[3]) - float(bbox[1]), 1.0)
        except (TypeError, ValueError):
            pass
    return (eye_delta_y / face_height) >= 0.08


def _empty_result(parse_source: str) -> SmartvisionFaceEmotion:
    return SmartvisionFaceEmotion(
        face_emotion_score=None,
        face_emotion_labels=[],
        dominant_emotion=None,
        parse_source=parse_source,
    )


def aggregate_smartvision_frames(emotions: list[SmartvisionFaceEmotion]) -> SmartvisionFaceEmotion:
    """Fuse multi-frame detect-face results into one Shield visual distress signal."""
    usable = [item for item in emotions if item.face_emotion_score is not None]
    if not usable:
        if emotions:
            labels: list[str] = []
            for item in emotions:
                for label in item.face_emotion_labels:
                    if label not in labels:
                        labels.append(label)
            return SmartvisionFaceEmotion(
                face_emotion_score=None,
                face_emotion_labels=labels[:6],
                dominant_emotion=emotions[0].dominant_emotion,
                parse_source="multi_frame_aggregate",
            )
        return _empty_result("aggregate_empty")

    max_item = max(usable, key=lambda item: item.face_emotion_score or 0.0)
    max_score = max(item.face_emotion_score or 0.0 for item in usable)
    labels: list[str] = []
    for item in usable:
        for label in item.face_emotion_labels:
            if label not in labels:
                labels.append(label)

    return SmartvisionFaceEmotion(
        face_emotion_score=round(max_score, 3),
        face_emotion_labels=labels[:6],
        dominant_emotion=max_item.dominant_emotion,
        parse_source="multi_frame_aggregate",
    )


def _collect_emotion_scores(obj: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}

    for key, value in obj.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in METADATA_KEYS:
            continue
        if normalized_key in {"labels", "face_emotion_labels", "dominant_emotion", "emotion", "info"}:
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
