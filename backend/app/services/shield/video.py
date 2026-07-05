"""Extract audio and frames from Path B live-check video uploads."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from backend.app.services.shield.paths import ALLOWED_FRAME_EXTENSIONS, resolve_shield_ref


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_audio_wav(video_ref: str, output_path: Path) -> bool:
    """Extract mono 16 kHz WAV from a challenge video. Returns False if ffmpeg is unavailable."""
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
