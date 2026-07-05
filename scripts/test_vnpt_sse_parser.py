from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.services.vnpt_client import VnptClient


class VnptSseParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = VnptClient(get_settings())

    def test_parse_sse_data_line(self) -> None:
        payload = {
            "message": "IDG-00000000",
            "object": {
                "sb": {
                    "card_data": [
                        {
                            "text": (
                                '{"safe": false, "scam_type": "suspected_scam", '
                                '"detected_patterns": ["scam_pattern_detected"], "confidence": 0.9}'
                            ),
                            "type": "text",
                        }
                    ]
                }
            },
        }
        body = f"data:{json.dumps(payload, ensure_ascii=False)}".encode("utf-8")
        parsed = self.client._parse_json(body)
        self.assertEqual(parsed["object"]["sb"]["card_data"][0]["type"], "text")

    def test_parse_plain_json(self) -> None:
        payload = {"object": {"sb": {"intent_name": "safe_confirmation"}}}
        parsed = self.client._parse_json(json.dumps(payload).encode("utf-8"))
        self.assertEqual(parsed["object"]["sb"]["intent_name"], "safe_confirmation")


if __name__ == "__main__":
    unittest.main()
