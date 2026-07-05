#!/usr/bin/env python3
"""Smoke-test VNPT SmartVision Hackathon flow: addFile -> url-file -> detect-face."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.smartvision.parser import parse_smartvision_face_emotion
from backend.app.services.vnpt_client import VnptClient


def _pick_selfie(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"Image not found: {explicit}")
        if path.is_relative_to(ROOT):
            return str(path.relative_to(ROOT))
        return str(path)

    uploads = ROOT / "uploads" / "ekyc"
    if uploads.is_dir():
        for item in sorted(uploads.glob("*")):
            if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                return f"uploads/ekyc/{item.name}"

    raise SystemExit(
        "No selfie found. Upload via POST /api/shield/challenge/upload-ekyc "
        "or pass --selfie /path/to/selfie.jpg"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test VNPT SmartVision detect-face API.")
    parser.add_argument("--selfie", help="Path to selfie JPEG/PNG/WEBP")
    parser.add_argument("--session", default="fides-smartvision-smoke", help="client_session value")
    args = parser.parse_args()

    settings = get_settings()
    client = VnptClient(settings)
    print(f"smartvision_enabled={client.smartvision_enabled} provider_mode={client.mode}")
    if not client.smartvision_enabled:
        print("FAIL: SmartVision real mode is disabled or credentials are incomplete.")
        return 1

    selfie_ref = _pick_selfie(args.selfie)
    response = client.smartvision_detect_face(selfie_ref, args.session)
    print(json.dumps(response, indent=2, ensure_ascii=False)[:3000])

    parsed = parse_smartvision_face_emotion(response)
    print(
        "\nParsed:",
        json.dumps(
            {
                "face_emotion_score": parsed.face_emotion_score,
                "face_emotion_labels": parsed.face_emotion_labels,
                "dominant_emotion": parsed.dominant_emotion,
                "parse_source": parsed.parse_source,
            },
            ensure_ascii=False,
        ),
    )

    http_status = response.get("http_status")
    if http_status == 401:
        print("\nFAIL: SmartVision token lacks permission for addFile/url-file/detect-face.")
        return 1

    if response.get("status") == "error" or (isinstance(http_status, int) and http_status >= 400):
        print("\nFAIL: SmartVision detect-face flow returned an error.")
        return 1

    if parsed.face_emotion_score is None and parsed.parse_source == "empty":
        print("\nWARN: API responded but parser could not derive face_emotion_score.")
        return 2

    print("\nOK: SmartVision detect-face responded and parsed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
