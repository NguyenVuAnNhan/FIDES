from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.smartbot.parser import parse_smartbot_response


class SmartbotParserTests(unittest.TestCase):
    def test_parse_json_card_data(self) -> None:
        response = {
            "object": {
                "sb": {
                    "card_data": [
                        {
                            "text": (
                                '{"safe": false, "scam_type": "fake_authority", '
                                '"detected_patterns": ["secrecy_pressure"], "confidence": 0.9}'
                            ),
                            "type": "text",
                        }
                    ],
                    "intent_name": "fake_authority",
                }
            }
        }
        result = parse_smartbot_response(response, "co quan dang dieu tra")
        self.assertEqual(result.llm_scam_type, "fake_authority")
        self.assertIn("secrecy_pressure", result.detected_patterns)
        self.assertEqual(result.parse_source, "json")

    def test_parse_safe_intent(self) -> None:
        response = {
            "object": {
                "sb": {
                    "card_data": [{"text": "Ban xac nhan tu minh.", "type": "text"}],
                    "intent_name": "safe_confirmation",
                }
            }
        }
        result = parse_smartbot_response(response, "toi tu xac nhan")
        self.assertIsNone(result.llm_scam_type)


if __name__ == "__main__":
    unittest.main()
