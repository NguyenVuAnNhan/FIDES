"""Extract audio and frames from Path B live-check video uploads."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from backend.app.services.shield.paths import ALLOWED_FRAME_EXTENSIONS, resolve_shield_ref


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_audio_webm(video_ref: str, output_path: Path) -> bool:
    """Extract audio-only Opus WEBM for VNPT STT (video tracks break gRPC STT)."""
    if not ffmpeg_available():
        return False

    video_path = resolve_shield_ref(video_ref)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-c:a",
                "libopus",
                "-b:a",
                "128k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return output_path.is_file() and output_path.stat().st_size > 0


def extract_audio_wav(video_ref: str, output_path: Path) -> bool:
    """Extract mono 16 kHz WAV for local voice-stress analysis."""
    if not ffmpeg_available():
        return False

    video_path = resolve_shield_ref(video_ref)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                str(video_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return output_path.is_file() and output_path.stat().st_size > 0


def resolve_stt_audio_ref(video_ref: str, smartvoice_dir: Path) -> tuple[str, str]:
    """Return (audio_ref, format_label) preferring audio-only WEBM for VNPT STT."""
    batch = uuid.uuid4().hex
    webm_path = smartvoice_dir / f"live-audio-{batch}.webm"
    if extract_audio_webm(video_ref, webm_path):
        return f"uploads/smartvoice/{webm_path.name}", "audio-only-webm"

    wav_path = smartvoice_dir / f"live-audio-{batch}.wav"
    if extract_audio_wav(video_ref, wav_path):
        return f"uploads/smartvoice/{wav_path.name}", "wav"

    return video_ref, "video-webm-fallback"


def extract_video_frames(video_ref: str, output_dir: Path, count: int = 3) -> list[Path]:
    """Sample JPEG frames evenly across the video duration."""
    if count < 1 or not ffmpeg_available():
        return []

    video_path = resolve_shield_ref(video_ref)
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame-%02d.jpg"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"fps=1/{max(1, count)}",
                "-frames:v",
                str(count),
                str(pattern),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return []

    frames = sorted(output_dir.glob("frame-*.jpg"))
    return [path for path in frames if path.suffix.lower() in ALLOWED_FRAME_EXTENSIONS]
