from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.app.services.voice_stress.prosody import TARGET_SAMPLE_RATE


def load_mono_audio(path: Path, target_rate: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    signal, sample_rate = _read_audio(path)
    if sample_rate != target_rate:
        signal = _resample_linear(signal, sample_rate, target_rate)
        sample_rate = target_rate
    if signal.ndim > 1:
        signal = np.mean(signal, axis=1)
    return signal.astype(np.float32), sample_rate


def load_mono_audio_from_array(
    signal: np.ndarray,
    source_rate: int,
    target_rate: int,
) -> tuple[np.ndarray, int]:
    if source_rate == target_rate:
        return np.asarray(signal, dtype=np.float32), target_rate
    return _resample_linear(np.asarray(signal, dtype=np.float32), source_rate, target_rate), target_rate


def _read_audio(path: Path) -> tuple[np.ndarray, int]:
    try:
        return _read_with_soundfile(path)
    except Exception:
        return _read_with_librosa(path)


def _read_with_soundfile(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    signal, sample_rate = sf.read(path, always_2d=False)
    return np.asarray(signal, dtype=np.float32), int(sample_rate)


def _read_with_librosa(path: Path) -> tuple[np.ndarray, int]:
    import librosa

    signal, sample_rate = librosa.load(path, sr=None, mono=True)
    return np.asarray(signal, dtype=np.float32), int(sample_rate)


def _resample_linear(signal: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or signal.size == 0:
        return signal
    duration = signal.size / source_rate
    target_length = max(1, int(round(duration * target_rate)))
    source_times = np.linspace(0.0, duration, num=signal.size, endpoint=False)
    target_times = np.linspace(0.0, duration, num=target_length, endpoint=False)
    return np.interp(target_times, source_times, signal).astype(np.float32)
