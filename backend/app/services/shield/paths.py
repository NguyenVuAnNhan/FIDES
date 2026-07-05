from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SHIELD_UPLOAD_DIR = PROJECT_ROOT / "uploads" / "shield"
ALLOWED_VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov"}
ALLOWED_FRAME_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_shield_upload_dir() -> Path:
    SHIELD_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return SHIELD_UPLOAD_DIR


def resolve_shield_ref(ref: str) -> Path:
    path = Path(ref)
    candidate = path if path.is_absolute() else PROJECT_ROOT / path
    if not candidate.is_file():
        raise FileNotFoundError(f"Shield media not found: {ref}")
    return candidate
