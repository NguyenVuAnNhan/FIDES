#!/usr/bin/env python3
"""Smoke-test local voice stress analysis (prosody + optional wav2vec arousal)."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.voice_stress import analyze_voice_stress


def _write_silence_wav(path: Path, seconds: float = 2.0, rate: int = 16000) -> None:
    sample_count = int(rate * seconds)
    data = b"\x00\x00" * sample_count
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"RIFF")
        handle.write(struct.pack("<I", 36 + len(data)))
        handle.write(b"WAVEfmt ")
        handle.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        handle.write(b"data")
        handle.write(struct.pack("<I", len(data)))
        handle.write(data)


def _pick_audio(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"Audio not found: {explicit}")
        return path

    upload_dir = ROOT / "uploads" / "smartvoice"
    if upload_dir.is_dir():
        for item in sorted(upload_dir.glob("*")):
            if item.suffix.lower() in {".wav", ".mp3", ".webm", ".m4a", ".ogg"}:
                return item

    generated = upload_dir / "voice-stress-smoke.wav"
    _write_silence_wav(generated)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test voice stress analyzer.")
    parser.add_argument("--audio", help="Path to challenge WAV/MP3")
    args = parser.parse_args()

    settings = get_settings()
    audio_path = _pick_audio(args.audio)
    audio_ref = str(audio_path.relative_to(ROOT)) if audio_path.is_relative_to(ROOT) else str(audio_path)

    print(
        f"voice_stress_enabled={settings.voice_stress_enabled} "
        f"locale={settings.voice_stress_locale} backend={settings.voice_stress_backend} "
        f"mode={settings.voice_stress_mode} model={settings.voice_stress_model_name}"
    )
    result = analyze_voice_stress(audio_ref, settings)
    payload = {
        "voice_stress_score": result.voice_stress_score,
        "voice_stress_labels": result.voice_stress_labels,
        "distress_score": result.distress_score,
        "arousal": result.arousal,
        "valence": result.valence,
        "dominance": result.dominance,
        "top_emotions": result.top_emotions,
        "model_used": result.model_used,
        "model_backend": result.model_backend,
        "model_name": result.model_name,
        "locale": result.locale,
        "prosody_stress_score": result.prosody.prosody_stress_score,
        "detail": result.detail,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
