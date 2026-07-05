from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SMARTVOICE_UPLOAD_DIR = PROJECT_ROOT / "uploads" / "smartvoice"
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".mpeg", ".webm", ".m4a", ".ogg", ".aac"}


def ensure_smartvoice_upload_dir() -> Path:
    SMARTVOICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return SMARTVOICE_UPLOAD_DIR
