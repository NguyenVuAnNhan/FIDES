#!/usr/bin/env python3
"""Smoke-test FIDES Grow pipeline with VNPT SmartReader on receipt fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.models import GrowProcessRequest
from backend.app.services.grow_pipeline_service import GrowOcrError, process_invoice
from backend.app.services.ocr.paths import (
    UPLOADS_ROOT,
    ReceiptPathError,
    ensure_uploads_dir,
    resolve_receipt_path,
)
from backend.app.services.vnpt_client import VnptClient

DATASET_PATH = ROOT / "backend/app/data/demo_dataset.json"
FIXTURES_DIR = ROOT / "frontend/static/fixtures/receipts"

EXPECTED_BANDS = {
    "grow-coffee-strong": "strong",
    "grow-food-stall-emerging": "emerging",
    "grow-retail-late-payment": "thin_file",
    "grow-electronics-strong": "strong",
}


def _minimal_payload(payload: dict) -> dict:
    return {
        "business_id": payload["business_id"],
        "business_name": payload["business_name"],
        "input_mode": payload["input_mode"],
        "input_source": payload.get("input_source"),
        "invoice_id": payload["invoice_id"],
        "customer_name": payload["customer_name"],
        "invoice_total": payload["invoice_total"],
        "paid_on_time": payload["paid_on_time"],
        "items": payload.get("items", []),
    }


def main() -> int:
    settings = get_settings()
    client = VnptClient(settings)
    print(f"smartreader_enabled={client.smartreader_enabled} provider_mode={client.mode}")
    if not client.smartreader_enabled:
        print("FAIL: SmartReader real mode is disabled or credentials are incomplete.")
        print("Set VNPT_SMARTREADER_MODE=real and VNPT token credentials in .env")
        return 1

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    try:
        resolve_receipt_path("/static/fixtures/receipts/../../../etc/passwd")
        failures.append("path traversal was not rejected")
    except ReceiptPathError:
        print("[ok] path traversal rejected")

    try:
        resolve_receipt_path("/static/other/file.png")
        failures.append("non-receipt path was not rejected")
    except ReceiptPathError:
        print("[ok] non-receipt path rejected")

    ensure_uploads_dir()
    upload_sample = UPLOADS_ROOT / "smoke-upload.png"
    fixture_sample = FIXTURES_DIR / "grow-coffee-strong.png"
    if fixture_sample.exists():
        upload_sample.write_bytes(fixture_sample.read_bytes())
        resolved_upload = resolve_receipt_path(f"/static/uploads/receipts/{upload_sample.name}")
        if resolved_upload != upload_sample.resolve():
            failures.append("upload path did not resolve correctly")
        else:
            print("[ok] upload receipt path resolved")
        upload_sample.unlink(missing_ok=True)

    for record in dataset["grow_invoices"]:
        scenario_id = record["id"]
        payload = record["payload"]
        if payload.get("input_mode") != "invoice_photo":
            continue

        try:
            process_response = process_invoice(GrowProcessRequest(**_minimal_payload(payload)))
        except GrowOcrError as exc:
            failures.append(f"{scenario_id}: OCR error: {exc}")
            print(f"[grow] {scenario_id}: OCR error: {exc}")
            continue

        request = process_response.request
        analysis = process_response.analysis
        ocr = request.ocr
        fields = ocr.extracted_fields
        expected_band = EXPECTED_BANDS.get(scenario_id)

        print(
            f"[grow] {scenario_id}: provider={ocr.provider} trust={analysis.trust_score} "
            f"band={analysis.credit_band} total={request.invoice_total}"
        )

        if ocr.provider != "SmartReader":
            failures.append(f"{scenario_id}: provider={ocr.provider!r}")
        if ocr.status != "completed":
            failures.append(f"{scenario_id}: ocr.status={ocr.status}")
        if fields is None:
            failures.append(f"{scenario_id}: missing extracted_fields")
        else:
            if request.invoice_total != fields.total_amount:
                failures.append(
                    f"{scenario_id}: invoice_total {request.invoice_total} "
                    f"!= ocr total {fields.total_amount}"
                )
            if request.business_name != fields.seller_name:
                failures.append(
                    f"{scenario_id}: business_name {request.business_name!r} "
                    f"!= seller {fields.seller_name!r}"
                )

        if expected_band and analysis.credit_band != expected_band:
            failures.append(
                f"{scenario_id}: expected credit_band={expected_band}, got {analysis.credit_band}"
            )

        input_source = payload.get("input_source", "")
        if input_source.startswith("/static/"):
            fixture_path = ROOT / "frontend/static" / input_source.removeprefix("/static/")
            if not fixture_path.exists():
                failures.append(f"{scenario_id}: missing receipt fixture {fixture_path}")

    if not FIXTURES_DIR.exists():
        failures.append(f"missing fixtures directory: {FIXTURES_DIR}")
    elif not any(FIXTURES_DIR.glob("*.png")):
        failures.append(f"no receipt PNG fixtures found in {FIXTURES_DIR}")

    if failures:
        print("\nGrow smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nGrow smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
