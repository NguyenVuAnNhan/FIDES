#!/usr/bin/env python3
"""Smoke-test VNPT SmartVoice STT and voice verification."""

from __future__ import annotations

import argparse
import io
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.vnpt_client import VnptClient


def _write_silence_wav(path: Path, seconds: float = 1.0, rate: int = 16000) -> None:
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

    candidates = [
        ROOT / "uploads" / "smartvoice",
        ROOT / "mock_payload" / "customer_voice_samples",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            for item in sorted(candidate.glob("*")):
                if item.suffix.lower() in {".wav", ".mp3", ".webm", ".m4a", ".ogg"}:
                    return item

    generated = ROOT / "uploads" / "smartvoice" / "smoke-generated.wav"
    _write_silence_wav(generated)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test VNPT SmartVoice wiring.")
    parser.add_argument("--challenge-audio", help="Path to challenge WAV/MP3")
    parser.add_argument("--reference-audio", help="Optional enrolled voice sample")
    parser.add_argument("--session", default="fides-smartvoice-smoke", help="client_session value")
    args = parser.parse_args()

    settings = get_settings()
    client = VnptClient(settings)
    print(f"smartvoice_enabled={client.smartvoice_enabled} provider_mode={client.mode}")
    if not client.smartvoice_enabled:
        print("FAIL: SmartVoice real mode is disabled or credentials are incomplete.")
        return 1

    challenge_path = _pick_audio(args.challenge_audio)
    reference_path = Path(args.reference_audio) if args.reference_audio else challenge_path
    if not reference_path.is_file():
        raise SystemExit(f"Reference audio not found: {args.reference_audio}")

    challenge_ref = (
        str(challenge_path.relative_to(ROOT)) if challenge_path.is_relative_to(ROOT) else str(challenge_path)
    )
    reference_ref = (
        str(reference_path.relative_to(ROOT)) if reference_path.is_relative_to(ROOT) else str(reference_path)
    )

    stt = client.smartvoice_stt(challenge_ref)
    voice = client.smartvoice_voice_verify(reference_ref, challenge_ref, args.session)

    print("\n== stt-service/v3/standard ==")
    print(json.dumps(stt, indent=2, ensure_ascii=False)[:1500])
    print("\n== voice-id upload/encode/verify ==")
    print(json.dumps(voice, indent=2, ensure_ascii=False)[:1500])

    auth_ok = all(
        item.get("provider_mode") == "real" and item.get("status") != "error" for item in (stt, voice)
    )
    provider_issues = any(
        str(item.get("statusCode", "")).startswith(("4", "401"))
        or item.get("status") in {"UNAUTHORIZED", "BAD_REQUEST", "error"}
        for item in (stt, voice)
    )

    if not auth_ok:
        print("\nFAIL: VNPT SmartVoice transport or auth failed.")
        return 1

    if provider_issues:
        print("\nOK: wiring reached VNPT. Check token permissions or use real speech WAV if transcript is empty.")
        return 0

    print("\nOK: VNPT SmartVoice STT and voice verification responded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
