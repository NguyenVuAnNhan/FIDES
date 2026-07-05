#!/usr/bin/env python3
"""Smoke-test VNPT Smartbot conversation API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.smartbot.parser import parse_smartbot_response
from backend.app.services.vnpt_client import VnptClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test VNPT Smartbot /v1/conversation.")
    parser.add_argument(
        "--text",
        default="Toi dang tu minh xac nhan giao dich nay. Khong co ai huong dan toi qua dien thoai.",
        help="Transcript or user message to send to Smartbot",
    )
    parser.add_argument("--session", default="fides-smartbot-smoke", help="session_id value")
    args = parser.parse_args()

    settings = get_settings()
    client = VnptClient(settings)
    print(
        f"smartbot_enabled={client.smartbot_enabled} bot_id={settings.vnpt_smartbot_bot_id} "
        f"base_url={settings.vnpt_smartbot_base_url}"
    )
    if not client.smartbot_enabled:
        print("FAIL: Smartbot real mode is disabled, credentials are incomplete, or bot_id is missing.")
        return 1

    response = client.smartbot_conversation(args.text, args.session)
    print("\n== assistant-stream/v1/conversation ==")
    print(json.dumps(response, indent=2, ensure_ascii=False)[:2500])

    classification = parse_smartbot_response(response, args.text)
    print("\n== parsed classification ==")
    print(
        json.dumps(
            {
                "llm_scam_type": classification.llm_scam_type,
                "detected_patterns": classification.detected_patterns,
                "llm_confidence": classification.llm_confidence,
                "intent_name": classification.intent_name,
                "parse_source": classification.parse_source,
                "reply_text": classification.reply_text[:300],
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    has_sb_payload = isinstance(response.get("object"), dict) and bool(response["object"])
    if response.get("http_status") == 200 and response.get("status") != "error" and has_sb_payload:
        if classification.parse_source == "none":
            print("\nFAIL: Smartbot returned HTTP 200 but card_data JSON was not parsed.")
            return 1
        print("\nOK: VNPT Smartbot conversation endpoint accepted the request.")
        return 0

    if response.get("http_status") == 200 and response.get("status") != "error":
        print("\nFAIL: Smartbot HTTP 200 but response object is empty (check SSE parsing).")
        return 1

    print("\nFAIL: VNPT Smartbot transport or auth failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
