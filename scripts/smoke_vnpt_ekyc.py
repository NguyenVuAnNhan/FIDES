#!/usr/bin/env python3
"""Smoke-test VNPT eKYC credentials and face endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.vnpt_client import VnptClient


def _pick_image(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise SystemExit(f"Image not found: {explicit}")
        return path

    candidates = [
        ROOT / "mock_payload" / "ekyc_test_selfie.jpg",
        ROOT / "mock_payload" / "uploads" / "ekyc",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            for item in sorted(candidate.glob("*")):
                if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    return item

    raise SystemExit(
        "No eKYC image found. Upload via POST /api/shield/challenge/upload-ekyc "
        "or pass --selfie /path/to/face.jpg"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test VNPT eKYC API wiring.")
    parser.add_argument("--selfie", help="Path to selfie JPEG/PNG")
    parser.add_argument("--document", help="Optional CMND/portrait image for face compare")
    parser.add_argument("--session", default="fides-ekyc-smoke", help="client_session value")
    args = parser.parse_args()

    settings = get_settings()
    client = VnptClient(settings)
    print(f"ekyc_enabled={client.ekyc_enabled} provider_mode={client.mode}")
    if not client.ekyc_enabled:
        print("FAIL: eKYC real mode is disabled or credentials are incomplete.")
        return 1

    selfie_path = _pick_image(args.selfie)
    document_path = Path(args.document) if args.document else selfie_path
    if not document_path.is_file():
        raise SystemExit(f"Document image not found: {args.document}")

    selfie_ref = str(selfie_path.relative_to(ROOT)) if selfie_path.is_relative_to(ROOT) else str(selfie_path)
    document_ref = (
        str(document_path.relative_to(ROOT)) if document_path.is_relative_to(ROOT) else str(document_path)
    )

    liveness = client.face_liveness(selfie_ref, args.session)
    mask = client.face_mask(selfie_ref, args.session)
    compare = client.face_compare(document_ref, selfie_ref, args.session)

    print("\n== face/liveness ==")
    print(json.dumps(liveness, indent=2, ensure_ascii=False)[:1200])
    print("\n== face/mask ==")
    print(json.dumps(mask, indent=2, ensure_ascii=False)[:800])
    print("\n== face/compare ==")
    print(json.dumps(compare, indent=2, ensure_ascii=False)[:800])

    auth_ok = all(item.get("provider_mode") == "real" and item.get("status") != "error" for item in (liveness, mask, compare))
    face_issues = any(
        item.get("messageFields") or str(item.get("statusCode", "")).startswith(("4", "408"))
        for item in (liveness, mask, compare)
    )

    if not auth_ok:
        print("\nFAIL: VNPT rejected auth or transport. Check token headers and body token.")
        return 1

    if face_issues:
        print("\nOK: VNPT auth works. Image quality/face detection failed — use real selfie + CMND photos.")
        return 0

    print("\nOK: VNPT eKYC auth and face checks responded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
