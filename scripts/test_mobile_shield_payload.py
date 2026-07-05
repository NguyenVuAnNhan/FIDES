#!/usr/bin/env python3
"""Smoke-check that mobile Shield payload defaults match backend Path B expectations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID_BUILDER = ROOT / "sdks/mobile/android/src/main/kotlin/ai/fides/sdk/ShieldPayloadBuilder.kt"
ANDROID_TYPES = ROOT / "sdks/mobile/android/src/main/kotlin/ai/fides/sdk/FidesTypes.kt"

REQUIRED_PATH_B_KEYS = {
    "shield_path",
    "transaction_amount",
    "recipient_name",
    "recipient_account",
    "active_call",
    "caller_type",
    "caller_number",
    "recipient_known",
    "ekyc_verification_status",
    "consent_granted",
    "consent_call_monitoring",
    "consent_transfer_check",
    "stt_transcript",
    "llm_scam_type",
    "native_telemetry_available",
}

PHASE2_FILES = {
    "call_monitor": ROOT / "sdks/mobile/android/src/main/kotlin/ai/fides/sdk/call/AndroidCallStateMonitor.kt",
    "live_capture": ROOT / "sdks/mobile/android/src/main/kotlin/ai/fides/sdk/capture/LiveCheckCapture.kt",
}

SAMPLE_APP_FILES = {
    "activity": ROOT / "sdks/mobile/sample-banking-app/src/main/kotlin/ai/fides/sample/ShieldTransferActivity.kt",
    "layout": ROOT / "sdks/mobile/sample-banking-app/src/main/res/layout/activity_shield_transfer.xml",
    "settings": ROOT / "sdks/mobile/settings.gradle.kts",
}

STAGE_TWO_CLEARED = {
    "ekyc_verification_status": "not_checked",
    "consent_granted": False,
    "stt_transcript": "",
    "llm_scam_type": None,
    "audio_source": None,
}


def main() -> int:
    if not ANDROID_BUILDER.exists():
        print(f"Missing {ANDROID_BUILDER}")
        return 1

    source = ANDROID_BUILDER.read_text(encoding="utf-8") + ANDROID_TYPES.read_text(encoding="utf-8")
    missing = [key for key in REQUIRED_PATH_B_KEYS if key not in source]
    if missing:
        print("ShieldPayloadBuilder missing keys:", ", ".join(sorted(missing)))
        return 1

    for key, expected in STAGE_TWO_CLEARED.items():
        if key not in source:
            print(f"Stage-2 clear key missing from builder: {key}")
            return 1

    missing_phase2 = [name for name, path in PHASE2_FILES.items() if not path.exists()]
    if missing_phase2:
        print("Missing Phase 2 files:", ", ".join(sorted(missing_phase2)))
        return 1

    missing_sample = [name for name, path in SAMPLE_APP_FILES.items() if not path.exists()]
    if missing_sample:
        print("Missing sample app files:", ", ".join(sorted(missing_sample)))
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "checked_file": str(ANDROID_BUILDER.relative_to(ROOT)),
                "required_keys": sorted(REQUIRED_PATH_B_KEYS),
                "phase2_files": sorted(PHASE2_FILES.keys()),
                "sample_app_files": sorted(SAMPLE_APP_FILES.keys()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
