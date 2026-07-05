from __future__ import annotations

from pathlib import Path

from backend.app.config import Settings, get_settings
from backend.app.services.smartvoice.paths import PROJECT_ROOT
from backend.app.services.voice_stress.audio_io import load_mono_audio
from backend.app.services.voice_stress.emotion2vec_model import (
    DEFAULT_EMOTION2VEC_MODEL,
    model_load_error as emotion2vec_load_error,
    predict_emotion,
)
from backend.app.services.voice_stress.wav2vec_model import (
    DEFAULT_WAV2VEC_MODEL,
    model_load_error as wav2vec_load_error,
)
from backend.app.services.voice_stress.emotion_types import EmotionPrediction
from backend.app.services.voice_stress.prosody import (
    TARGET_SAMPLE_RATE,
    analyze_prosody,
    empty_prosody,
    prosody_labels,
)
from backend.app.services.voice_stress.types import VoiceStressResult
LOCALE_WEIGHTS = {
    "vi": (0.40, 0.60),
    "en": (0.55, 0.45),
}


def analyze_voice_stress(
    audio_ref: str,
    settings: Settings | None = None,
) -> VoiceStressResult:
    """Analyze challenge audio using multilingual emotion2vec + language-agnostic prosody."""
    active_settings = settings or get_settings()
    if not active_settings.voice_stress_enabled:
        return _disabled_result(audio_ref)

    audio_path = resolve_audio_ref(audio_ref)
    if not audio_path.is_file():
        return _missing_audio_result(audio_ref, audio_path)

    signal, sample_rate = load_mono_audio(audio_path, TARGET_SAMPLE_RATE)
    prosody = analyze_prosody(signal, sample_rate)

    mode = active_settings.voice_stress_mode.strip().lower()
    locale = active_settings.voice_stress_locale.strip().lower() or "vi"
    use_model = mode in {"auto", "model"}
    backend = active_settings.voice_stress_backend
    model_name = active_settings.voice_stress_model_name or _default_model_name(backend, locale)
    hub = active_settings.voice_stress_model_hub

    emotion: EmotionPrediction | None = None
    fallback_attempts: list[dict[str, str | None]] = []
    if use_model:
        emotion = predict_emotion(
            audio_path=str(audio_path),
            signal=signal,
            sample_rate=sample_rate,
            backend=backend,
            model_name=model_name,
            hub=hub,
        )
        if emotion is None:
            fallback_attempts.append(
                {
                    "backend": backend,
                    "model": model_name,
                    "error": emotion2vec_load_error() or wav2vec_load_error(),
                }
            )
            if mode == "auto" and backend.strip().lower() in {"auto", "emotion2vec"}:
                emotion = predict_emotion(
                    audio_path=str(audio_path),
                    signal=signal,
                    sample_rate=sample_rate,
                    backend="wav2vec",
                    model_name=DEFAULT_WAV2VEC_MODEL,
                    hub=hub,
                )
                if emotion is None:
                    fallback_attempts.append(
                        {
                            "backend": "wav2vec",
                            "model": DEFAULT_WAV2VEC_MODEL,
                            "error": wav2vec_load_error(),
                        }
                    )
        if emotion is None and mode == "model":
            error = fallback_attempts[-1]["error"] if fallback_attempts else "unknown model load error"
            return _model_failed_result(audio_ref, prosody, str(error))

    model_used = emotion is not None
    arousal = emotion.arousal if emotion else None
    valence = emotion.valence if emotion else None
    dominance = emotion.dominance if emotion else None
    distress_score = emotion.distress_score if emotion else None
    top_emotions = emotion.top_emotions if emotion else []

    arousal_weight, prosody_weight = _weights_for_locale(
        locale,
        active_settings.voice_stress_arousal_weight,
        active_settings.voice_stress_prosody_weight,
    )
    voice_stress_score = _combine_stress_score(
        prosody.prosody_stress_score,
        emotion,
        arousal_weight,
        prosody_weight,
    )
    labels = prosody_labels(prosody, arousal=arousal, top_emotions=top_emotions)
    detail = _build_detail(
        audio_ref=audio_ref,
        locale=locale,
        prosody=prosody,
        emotion=emotion,
        voice_stress_score=voice_stress_score,
        labels=labels,
    )

    return VoiceStressResult(
        voice_stress_score=voice_stress_score,
        voice_stress_labels=labels,
        prosody=prosody,
        arousal=arousal,
        valence=valence,
        dominance=dominance,
        distress_score=distress_score,
        top_emotions=top_emotions,
        model_used=model_used,
        model_name=emotion.model_name if emotion else model_name,
        model_backend=emotion.backend if emotion else None,
        locale=locale,
        detail=detail,
        raw={
            "audio_ref": audio_ref,
            "resolved_path": str(audio_path),
            "mode": mode,
            "locale": locale,
            "backend": emotion.backend if emotion else backend,
            "model_load_error": emotion2vec_load_error() or wav2vec_load_error(),
            "fallback_attempts": fallback_attempts,
            "top_emotions": top_emotions,
        },
    )


def resolve_audio_ref(ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _default_model_name(backend: str, locale: str) -> str:
    normalized = backend.strip().lower()
    if normalized == "wav2vec" or (normalized == "auto" and locale == "en"):
        return DEFAULT_WAV2VEC_MODEL
    return DEFAULT_EMOTION2VEC_MODEL


def _weights_for_locale(
    locale: str,
    configured_arousal: float,
    configured_prosody: float,
) -> tuple[float, float]:
    if configured_arousal != 0.55 or configured_prosody != 0.45:
        return configured_arousal, configured_prosody
    return LOCALE_WEIGHTS.get(locale, LOCALE_WEIGHTS["vi"])


def _combine_stress_score(
    prosody_stress: float,
    emotion: EmotionPrediction | None,
    model_weight: float,
    prosody_weight: float,
) -> float:
    if emotion is None:
        return round(prosody_stress, 3)

    model_signal = min(1.0, emotion.distress_score * 0.65 + emotion.arousal * 0.35)
    total = max(model_weight + prosody_weight, 0.001)
    mw = model_weight / total
    pw = prosody_weight / total
    score = mw * model_signal + pw * prosody_stress
    return round(max(0.0, min(1.0, score)), 3)


def _build_detail(
    *,
    audio_ref: str,
    locale: str,
    prosody,
    emotion: EmotionPrediction | None,
    voice_stress_score: float,
    labels: list[str],
) -> str:
    parts = [
        f"Voice stress analyzer processed {audio_ref} (locale={locale}).",
        f"score={voice_stress_score:.2f}",
        f"labels={', '.join(labels) if labels else 'none'}",
        (
            f"prosody(f0={prosody.f0_mean_hz:.0f}Hz, pause_ratio={prosody.pause_ratio:.2f}, "
            f"rate={prosody.speech_rate_syms_per_s:.2f}/s)"
        ),
    ]
    if emotion is not None:
        top = ", ".join(f"{name}={score:.2f}" for name, score in emotion.top_emotions[:3])
        parts.append(
            f"model={emotion.model_name} backend={emotion.backend} "
            f"distress={emotion.distress_score:.2f} arousal={emotion.arousal:.2f} "
            f"valence={emotion.valence:.2f} top=[{top}]"
        )
    else:
        err = emotion2vec_load_error() or wav2vec_load_error()
        suffix = f" error={err}" if err else ""
        parts.append(f"model=prosody-only fallback{suffix}")
    return " ".join(parts)


def _disabled_result(audio_ref: str) -> VoiceStressResult:
    return VoiceStressResult(
        voice_stress_score=0.0,
        voice_stress_labels=["not_analyzed"],
        prosody=empty_prosody(),
        detail=f"Voice stress analysis disabled for {audio_ref}.",
        raw={"disabled": True},
    )


def _missing_audio_result(audio_ref: str, path: Path) -> VoiceStressResult:
    return VoiceStressResult(
        voice_stress_score=0.5,
        voice_stress_labels=["audio_missing"],
        prosody=empty_prosody(),
        detail=f"Voice stress analyzer could not find audio for {audio_ref} at {path}.",
        raw={"missing_audio": True, "resolved_path": str(path)},
    )


def _model_failed_result(audio_ref: str, prosody, error: str) -> VoiceStressResult:
    labels = prosody_labels(prosody)
    score = prosody.prosody_stress_score
    return VoiceStressResult(
        voice_stress_score=score,
        voice_stress_labels=labels,
        prosody=prosody,
        detail=(
            f"Voice stress model failed for {audio_ref}; prosody-only fallback. "
            f"score={score:.2f}. error={error}"
        ),
        raw={"model_error": error},
    )
