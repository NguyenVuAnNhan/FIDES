"""VNPT SmartReader provider: receipt image path -> GrowOcrInput."""

from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.config import get_settings
from backend.app.models import GrowOcrInput, OcrExtractedFields
from backend.app.services.ocr.receipt_parser import ParseResult
from backend.app.services.ocr.smartreader_parser import (
    parse_scan_response,
    parse_vat_invoice_response,
    vnpt_call_failed,
)
from backend.app.services.vnpt_client import VnptClient

PROVIDER_NAME = "SmartReader"


class SmartReaderOcrProvider:
    """Extract structured receipt fields via VNPT SmartReader OCR/KIE."""

    def __init__(self, client: VnptClient | None = None):
        self._client = client or VnptClient(get_settings())

    @property
    def enabled(self) -> bool:
        return self._client.smartreader_enabled

    def extract(self, image_path: Path | str) -> GrowOcrInput:
        path = Path(image_path)
        if not path.is_file():
            return _failed()
        if not self.enabled:
            return _failed()

        image_ref = str(path.resolve())
        session = f"fides-grow-ocr-{uuid.uuid4().hex[:12]}"

        scan_response = self._client.smartreader_ocr_scan(image_ref, session)
        if not vnpt_call_failed(scan_response):
            parsed = parse_scan_response(scan_response)
            if not parsed.missing_required:
                return _completed(parsed)
            scan_partial = parsed

        vat_response = self._client.smartreader_vat_invoice(image_ref, session)
        if not vnpt_call_failed(vat_response):
            parsed = parse_vat_invoice_response(vat_response)
            if not parsed.missing_required:
                return _completed(parsed)

        if "scan_partial" in locals() and scan_partial.fields:
            return GrowOcrInput(
                provider=PROVIDER_NAME,
                status="failed",
                confidence=scan_partial.confidence,
                extracted_fields=scan_partial.fields,
            )

        return _failed()


def get_smartreader_provider() -> SmartReaderOcrProvider:
    return SmartReaderOcrProvider()


def get_ocr_provider() -> SmartReaderOcrProvider:
    """Return the active Grow OCR provider (VNPT SmartReader)."""
    return get_smartreader_provider()


def _completed(parsed: ParseResult) -> GrowOcrInput:
    return GrowOcrInput(
        provider=PROVIDER_NAME,
        status="completed",
        confidence=parsed.confidence,
        extracted_fields=parsed.fields,
    )


def _failed() -> GrowOcrInput:
    return GrowOcrInput(
        provider=PROVIDER_NAME,
        status="failed",
        confidence=0.0,
        extracted_fields=OcrExtractedFields(),
    )
