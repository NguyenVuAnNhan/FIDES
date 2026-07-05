from __future__ import annotations

from threading import Lock
from typing import Any

import numpy as np

from backend.app.services.voice_stress.emotion_types import EmotionPrediction
from backend.app.services.voice_stress.prosody import TARGET_SAMPLE_RATE
from backend.app.services.voice_stress.wav2vec_model import (
    DEFAULT_WAV2VEC_MODEL,
    predict_wav2vec_emotion,
)

DEFAULT_EMOTION2VEC_MODEL = "iic/emotion2vec_plus_base"

EMOTION2VEC_DISTRESS_LABELS = frozenset({"angry", "disgusted", "fearful", "sad"})

_model_bundle: dict[str, Any] | None = None
_load_lock = Lock()
_load_error: str | None = None


def predict_emotion2vec(audio_path: str, model_name: str, hub: str = "hf") -> EmotionPrediction | None:
    bundle = _load_model(model_name, hub)
    if bundle is None:
        return None

    model = bundle["model"]
    try:
        results = model.generate(
            input=audio_path,
            granularity="utterance",
            extract_embedding=False,
        )
    except Exception as exc:  # noqa: BLE001
        global _load_error
        _load_error = str(exc)
        return None

    if not results:
        return None

    first = results[0] if isinstance(results, list) else results
    if not isinstance(first, dict):
        return None

    labels = [str(item).lower() for item in first.get("labels", [])]
    scores = [_to_float(item) for item in first.get("scores", [])]
    if not labels or not scores or len(labels) != len(scores):
        return None

    ranked = sorted(zip(labels, scores), key=lambda item: item[1], reverse=True)
    distress_score, arousal, valence, dominance = _map_distress_scores(ranked)
    return EmotionPrediction(
        arousal=arousal,
        valence=valence,
        dominance=dominance,
        distress_score=distress_score,
        top_emotions=ranked[:3],
        backend="emotion2vec",
        model_name=model_name,
    )


def model_load_error() -> str | None:
    return _load_error


def is_emotion2vec_model(model_name: str) -> bool:
    normalized = model_name.lower()
    return "emotion2vec" in normalized or normalized.startswith("iic/")


def predict_emotion(
    *,
    audio_path: str,
    signal: np.ndarray,
    sample_rate: int,
    backend: str,
    model_name: str,
    hub: str = "hf",
) -> EmotionPrediction | None:
    selected_backend = _resolve_backend(backend, model_name)
    if selected_backend == "emotion2vec":
        return predict_emotion2vec(audio_path, model_name, hub=hub)
    if selected_backend == "wav2vec":
        wav2vec = predict_wav2vec_emotion(
            signal,
            sample_rate,
            model_name=model_name or DEFAULT_WAV2VEC_MODEL,
        )
        if wav2vec is None:
            return None
        arousal, dominance, valence = wav2vec
        distress = min(1.0, arousal + max(0.0, 0.45 - valence) * 0.35)
        return EmotionPrediction(
            arousal=arousal,
            valence=valence,
            dominance=dominance,
            distress_score=distress,
            top_emotions=[("arousal", arousal), ("valence", valence)],
            backend="wav2vec",
            model_name=model_name or DEFAULT_WAV2VEC_MODEL,
        )
    return None


def _resolve_backend(backend: str, model_name: str) -> str:
    normalized = backend.strip().lower()
    if normalized == "auto":
        return "emotion2vec" if is_emotion2vec_model(model_name) else "wav2vec"
    if normalized in {"emotion2vec", "wav2vec"}:
        return normalized
    if is_emotion2vec_model(model_name):
        return "emotion2vec"
    return "wav2vec"


def _map_distress_scores(ranked: list[tuple[str, float]]) -> tuple[float, float, float, float]:
    scores = {label: score for label, score in ranked}
    distress = sum(scores.get(label, 0.0) for label in EMOTION2VEC_DISTRESS_LABELS)
    fearful = scores.get("fearful", 0.0)
    angry = scores.get("angry", 0.0)
    sad = scores.get("sad", 0.0)
    happy = scores.get("happy", 0.0)
    surprised = scores.get("surprised", 0.0)
    neutral = scores.get("neutral", 0.0)

    arousal = _clip01(fearful + angry * 0.85 + surprised * 0.45 + sad * 0.35)
    valence = _clip01(0.5 + (happy - sad - fearful * 0.6 - angry * 0.35))
    dominance = _clip01(0.45 + angry * 0.35 - fearful * 0.25 + surprised * 0.15)
    distress_score = _clip01(distress + max(0.0, arousal - neutral) * 0.15)
    return distress_score, arousal, valence, dominance


def _load_model(model_name: str, hub: str) -> dict[str, Any] | None:
    global _model_bundle, _load_error
    cache_key = f"{hub}:{model_name}"
    if _model_bundle is not None and _model_bundle.get("cache_key") == cache_key:
        return _model_bundle

    with _load_lock:
        if _model_bundle is not None and _model_bundle.get("cache_key") == cache_key:
            return _model_bundle
        try:
            from funasr import AutoModel

            resolved_hub = "hf" if hub.lower() in {"hf", "huggingface"} else "ms"
            model = AutoModel(model=model_name, hub=resolved_hub)
            _model_bundle = {"model": model, "cache_key": cache_key, "model_name": model_name}
            _load_error = None
            return _model_bundle
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            _model_bundle = None
            return None


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))
