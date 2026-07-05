"""PaddleOCR provider: receipt image path -> GrowOcrInput."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from backend.app.models import GrowOcrInput, OcrExtractedFields
from backend.app.services.ocr.receipt_parser import parse_receipt_lines

PROVIDER_NAME = "PaddleOCR"

_engine = None
_engine_lock = Lock()


class PaddleOcrProvider:
    """Extract structured receipt fields from a PNG using PaddleOCR."""

    def extract(self, image_path: Path | str) -> GrowOcrInput:
        path = Path(image_path)
        if not path.is_file():
            return _failed()

        try:
            lines = _read_text_lines(path)
        except ImportError:
            return _failed()
        except Exception:
            return _failed()

        if not lines:
            return _failed()

        parsed = parse_receipt_lines(lines)
        if parsed.missing_required:
            return GrowOcrInput(
                provider=PROVIDER_NAME,
                status="failed",
                confidence=parsed.confidence,
                extracted_fields=parsed.fields,
            )

        return GrowOcrInput(
            provider=PROVIDER_NAME,
            status="completed",
            confidence=parsed.confidence,
            extracted_fields=parsed.fields,
        )


def get_paddle_provider() -> PaddleOcrProvider:
    """Return a provider instance (Paddle engine loads lazily on first extract)."""
    return PaddleOcrProvider()


_ALLOCATOR_RETRY_ATTEMPTS = 3


def _read_text_lines(image_path: Path) -> list[str]:
    engine = _get_engine()
    last_error: Exception | None = None
    for _ in range(_ALLOCATOR_RETRY_ATTEMPTS):
        try:
            result = engine.ocr(str(image_path), cls=True)
            return _lines_from_paddle_result(result)
        except Exception as exc:  
            last_error = exc
    raise last_error


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine
        from paddleocr import PaddleOCR

        # First call may download English detection/recognition models.
        _engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return _engine


def _lines_from_paddle_result(result: object) -> list[str]:
    lines: list[str] = []
    if not result:
        return lines

    for block in result:
        if not block:
            continue
        for item in block:
            # Typical item shape: [box, (text, confidence)]
            if not item or len(item) < 2 or not item[1]:
                continue
            text = item[1][0]
            if text is None:
                continue
            line = str(text).strip()
            if line:
                lines.append(line)
    return lines


def _failed() -> GrowOcrInput:
    return GrowOcrInput(
        provider=PROVIDER_NAME,
        status="failed",
        confidence=0.0,
        extracted_fields=OcrExtractedFields(),
    )
