from __future__ import annotations

import numpy as np

from backend.app.services.voice_stress.types import ProsodyFeatures

TARGET_SAMPLE_RATE = 16_000
MIN_AUDIO_SECONDS = 0.5


def analyze_prosody(signal: np.ndarray, sample_rate: int) -> ProsodyFeatures:
    """Extract explainable prosody cues from mono audio."""
    if signal.size == 0:
        return _empty_prosody()

    if sample_rate != TARGET_SAMPLE_RATE:
        signal = _resample(signal, sample_rate, TARGET_SAMPLE_RATE)
        sample_rate = TARGET_SAMPLE_RATE

    signal = signal.astype(np.float64, copy=False)
    duration_s = float(signal.size) / sample_rate
    if duration_s < MIN_AUDIO_SECONDS:
        padded = np.zeros(int(MIN_AUDIO_SECONDS * sample_rate), dtype=np.float64)
        padded[: signal.size] = signal
        signal = padded
        duration_s = float(signal.size) / sample_rate

    f0_mean, f0_std = _pitch_stats(signal, sample_rate)
    pause_ratio, long_pause_count = _pause_stats(signal, sample_rate)
    speech_rate = _speech_rate(signal, sample_rate, duration_s)
    energy_std = float(np.std(_frame_rms(signal, sample_rate)))
    zcr = _zero_crossing_rate(signal)

    stress_parts = [
        _bounded01((f0_mean - 145.0) / 95.0),
        _bounded01(f0_std / 45.0),
        _bounded01(pause_ratio / 0.35),
        _bounded01(long_pause_count / 4.0),
        _bounded01((0.55 - speech_rate) / 0.35) if speech_rate < 0.55 else _bounded01((speech_rate - 3.8) / 2.2),
        _bounded01(energy_std / 0.08),
        _bounded01(zcr / 0.12),
    ]
    prosody_stress_score = round(float(np.mean(stress_parts)), 3)

    return ProsodyFeatures(
        f0_mean_hz=round(f0_mean, 2),
        f0_std_hz=round(f0_std, 2),
        pause_ratio=round(pause_ratio, 3),
        long_pause_count=long_pause_count,
        speech_rate_syms_per_s=round(speech_rate, 3),
        energy_std=round(energy_std, 4),
        zero_crossing_rate=round(zcr, 4),
        duration_s=round(duration_s, 3),
        prosody_stress_score=prosody_stress_score,
    )


def _normalize_emotion_label(label: str) -> str:
    text = str(label).strip().lower()
    if "/" in text:
        english = text.rsplit("/", 1)[-1].strip()
        if english:
            text = english
    return text


def prosody_labels(
    prosody: ProsodyFeatures,
    arousal: float | None = None,
    top_emotions: list[tuple[str, float]] | None = None,
) -> list[str]:
    labels: list[str] = []
    if prosody.f0_mean_hz >= 185.0 or prosody.f0_std_hz >= 28.0:
        labels.append("elevated_pitch")
    if prosody.pause_ratio >= 0.12 or prosody.long_pause_count >= 2:
        labels.append("speech_hesitation")
    if prosody.zero_crossing_rate >= 0.08 and prosody.energy_std >= 0.045:
        labels.append("fast_breathing")
    if arousal is not None and arousal >= 0.62:
        labels.append("high_arousal")
    if top_emotions:
        top_label = _normalize_emotion_label(top_emotions[0][0])
        if top_label in {"fearful", "sad", "angry", "disgusted"} and top_emotions[0][1] >= 0.35:
            labels.append(f"emotion_{top_label}")
    if not labels and prosody.prosody_stress_score <= 0.28:
        labels.append("steady_voice")
    return labels


def empty_prosody() -> ProsodyFeatures:
    return _empty_prosody()


def _empty_prosody() -> ProsodyFeatures:
    return ProsodyFeatures(
        f0_mean_hz=0.0,
        f0_std_hz=0.0,
        pause_ratio=0.0,
        long_pause_count=0,
        speech_rate_syms_per_s=0.0,
        energy_std=0.0,
        zero_crossing_rate=0.0,
        duration_s=0.0,
        prosody_stress_score=0.0,
    )


def _resample(signal: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    import librosa

    return librosa.resample(signal, orig_sr=source_rate, target_sr=target_rate)


def _pitch_stats(signal: np.ndarray, sample_rate: int) -> tuple[float, float]:
    import librosa

    f0 = librosa.yin(
        signal,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sample_rate,
    )
    voiced = f0[f0 > 0]
    if voiced.size == 0:
        return 0.0, 0.0
    return float(np.mean(voiced)), float(np.std(voiced))


def _pause_stats(signal: np.ndarray, sample_rate: int) -> tuple[float, int]:
    import librosa

    frame_length = max(256, int(0.025 * sample_rate))
    hop_length = max(128, int(0.010 * sample_rate))
    rms = librosa.feature.rms(y=signal, frame_length=frame_length, hop_length=hop_length)[0]
    if rms.size == 0:
        return 0.0, 0
    threshold = max(float(np.percentile(rms, 20)), 0.01)
    silent = rms < threshold
    pause_ratio = float(np.mean(silent))
    long_pause_count = _count_long_runs(silent, min_frames=max(3, int(0.35 * sample_rate / hop_length)))
    return pause_ratio, long_pause_count


def _speech_rate(signal: np.ndarray, sample_rate: int, duration_s: float) -> float:
    import librosa

    if duration_s <= 0:
        return 0.0
    onsets = librosa.onset.onset_detect(y=signal, sr=sample_rate, units="time")
    if onsets.size == 0:
        return 0.0
    return float(onsets.size / duration_s)


def _frame_rms(signal: np.ndarray, sample_rate: int) -> np.ndarray:
    import librosa

    frame_length = max(256, int(0.025 * sample_rate))
    hop_length = max(128, int(0.010 * sample_rate))
    return librosa.feature.rms(y=signal, frame_length=frame_length, hop_length=hop_length)[0]


def _zero_crossing_rate(signal: np.ndarray) -> float:
    if signal.size < 2:
        return 0.0
    crossings = np.sum(signal[:-1] * signal[1:] < 0)
    return float(crossings / (signal.size - 1))


def _count_long_runs(mask: np.ndarray, min_frames: int) -> int:
    count = 0
    run = 0
    for value in mask:
        if value:
            run += 1
        elif run >= min_frames:
            count += 1
            run = 0
        else:
            run = 0
    if run >= min_frames:
        count += 1
    return count


def _bounded01(value: float) -> float:
    return max(0.0, min(1.0, value))
