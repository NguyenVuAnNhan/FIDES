"""Safe resolution of Grow receipt image paths."""

from __future__ import annotations

from pathlib import Path

# backend/app/services/ocr/paths.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
RECEIPTS_ROOT = (REPO_ROOT / "frontend" / "static" / "fixtures" / "receipts").resolve()


class ReceiptPathError(ValueError):
    """Raised when input_source is missing, unsafe, or not found."""


def resolve_receipt_path(input_source: str | None) -> Path:
    """Map a public /static receipt URL to a file under fixtures/receipts."""
    if not input_source or not str(input_source).strip():
        raise ReceiptPathError("input_source is required for invoice_photo mode.")

    source = str(input_source).strip()
    prefix = "/static/fixtures/receipts/"
    if source.startswith(prefix):
        relative = source[len(prefix) :]
    elif source.startswith("fixtures/receipts/"):
        relative = source.removeprefix("fixtures/receipts/")
    else:
        raise ReceiptPathError(
            "input_source must point to a receipt under /static/fixtures/receipts/."
        )

    relative = relative.lstrip("/")
    if not relative or ".." in Path(relative).parts:
        raise ReceiptPathError("Invalid receipt path.")

    path = (RECEIPTS_ROOT / relative).resolve()
    try:
        path.relative_to(RECEIPTS_ROOT)
    except ValueError as exc:
        raise ReceiptPathError("Invalid receipt path.") from exc

    if not path.is_file():
        raise ReceiptPathError(f"Receipt image not found: {relative}")

    return path
