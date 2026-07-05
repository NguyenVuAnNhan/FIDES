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

    def test_parse_suspected_scam_from_detected_patterns(self) -> None:
        response = {
            "object": {
                "sb": {
                    "card_data": [
                        {
                            "text": (
                                '{"safe": false, "scam_type": "suspected_scam", '
                                '"detected_patterns": ["fake_authority"], "confidence": 0.95}'
                            ),
                            "type": "text",
                        }
                    ],
                    "intent_name": "fake_authority",
                }
            }
        }
        result = parse_smartbot_response(
            response,
            "Cong an dang dieu tra vu an, yeu cau chuyen tien xac minh",
        )
        self.assertEqual(result.llm_scam_type, "fake_authority")
        self.assertEqual(result.detected_patterns, ["fake_authority"])
        self.assertEqual(result.parse_source, "json")

    def test_parse_suspected_scam_investment_pattern(self) -> None:
        response = {
            "object": {
                "sb": {
                    "card_data": [
                        {
                            "text": (
                                '{"safe": false, "scam_type": "suspected_scam", '
                                '"detected_patterns": ["investment_scam"], "confidence": 0.9}'
                            ),
                            "type": "text",
                        }
                    ],
                    "intent_name": "investment_scam",
                }
            }
        }
        result = parse_smartbot_response(response, "cam ket loi nhuan cao")
        self.assertEqual(result.llm_scam_type, "investment")
        self.assertEqual(result.detected_patterns, ["investment_scam"])

    def test_parse_suspected_scam_with_transcript_keywords(self) -> None:
        response = {
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
            }
        }
        result = parse_smartbot_response(
            response,
            "Cong an dang dieu tra vu an, yeu cau chuyen tien xac minh",
        )
        self.assertEqual(result.llm_scam_type, "fake_authority")
        self.assertEqual(result.parse_source, "json")

    def test_parse_suspected_scam_safe_confirmation(self) -> None:
        response = {
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
            }
        }
        result = parse_smartbot_response(
            response,
            "Toi dang tu minh xac nhan giao dich nay. Khong co ai huong dan toi qua dien thoai.",
        )
        self.assertIsNone(result.llm_scam_type)
        self.assertEqual(result.parse_source, "json")


if __name__ == "__main__":
    unittest.main()
