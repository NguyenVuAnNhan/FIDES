from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
EKYC_UPLOAD_DIR = PROJECT_ROOT / "uploads" / "ekyc"
ALLOWED_EKYC_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_ekyc_upload_dir() -> Path:
    EKYC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return EKYC_UPLOAD_DIR


def resolve_ekyc_ref(ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        candidate = path
    else:
        candidate = PROJECT_ROOT / path

    if not candidate.is_file():
        raise FileNotFoundError(f"eKYC image not found: {ref}")
    if candidate.suffix.lower() not in ALLOWED_EKYC_EXTENSIONS:
        raise ValueError(f"Unsupported eKYC image type: {candidate.suffix}")
    return candidate
