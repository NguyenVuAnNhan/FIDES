"""Safe resolution of Grow receipt image paths."""

from __future__ import annotations

from pathlib import Path

# backend/app/services/ocr/paths.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
STATIC_ROOT = (REPO_ROOT / "frontend" / "static").resolve()
RECEIPTS_ROOT = (STATIC_ROOT / "fixtures" / "receipts").resolve()
UPLOADS_ROOT = (STATIC_ROOT / "uploads" / "receipts").resolve()

_ALLOWED_PREFIXES = (
    ("/static/fixtures/receipts/", RECEIPTS_ROOT),
    ("/static/uploads/receipts/", UPLOADS_ROOT),
    ("fixtures/receipts/", RECEIPTS_ROOT),
    ("uploads/receipts/", UPLOADS_ROOT),
)


class ReceiptPathError(ValueError):
    """Raised when input_source is missing, unsafe, or not found."""


def resolve_receipt_path(input_source: str | None) -> Path:
    """Map a public /static receipt URL to a file under fixtures or uploads."""
    if not input_source or not str(input_source).strip():
        raise ReceiptPathError("input_source is required for invoice_photo mode.")

    source = str(input_source).strip()
    root: Path | None = None
    relative = ""

    for prefix, allowed_root in _ALLOWED_PREFIXES:
        if source.startswith(prefix):
            root = allowed_root
            relative = source[len(prefix) :]
            break

    if root is None:
        raise ReceiptPathError(
            "input_source must point to a receipt under "
            "/static/fixtures/receipts/ or /static/uploads/receipts/."
        )

    relative = relative.lstrip("/")
    if not relative or ".." in Path(relative).parts:
        raise ReceiptPathError("Invalid receipt path.")

    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReceiptPathError("Invalid receipt path.") from exc

    if not path.is_file():
        raise ReceiptPathError(f"Receipt image not found: {relative}")

    return path


def ensure_uploads_dir() -> Path:
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOADS_ROOT
