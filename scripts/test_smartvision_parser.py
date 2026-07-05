#!/usr/bin/env python3
"""Unit tests for VNPT SmartVision face-emotion response parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.smartvision.parser import parse_smartvision_face_emotion


class SmartvisionParserTests(unittest.TestCase):
    def test_emotion_map(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "object": {
                    "fear": 0.82,
                    "sad": 0.61,
                    "happy": 0.04,
                    "neutral": 0.11,
                }
            }
        )
        self.assertGreater(parsed.face_emotion_score or 0, 0.7)
        self.assertIn("fear", parsed.face_emotion_labels)
        self.assertEqual(parsed.parse_source, "emotion_map")

    def test_direct_distress_score(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "object": {
                    "distress_score": 0.76,
                    "dominant_emotion": "fear",
                }
            }
        )
        self.assertEqual(parsed.face_emotion_score, 0.76)
        self.assertEqual(parsed.dominant_emotion, "fear")
        self.assertEqual(parsed.parse_source, "direct_score")

    def test_error_response_is_empty(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "status": "UNAUTHORIZED",
                "http_status": 401,
                "object": {},
            }
        )
        self.assertIsNone(parsed.face_emotion_score)
        self.assertEqual(parsed.parse_source, "empty")

    def test_emotion_list(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "object": {
                    "emotions": [
                        {"label": "fear", "score": 0.71},
                        {"label": "neutral", "score": 0.18},
                    ]
                }
            }
        )
        self.assertAlmostEqual(parsed.face_emotion_score or 0, 0.71, places=2)
        self.assertIn("fear", parsed.face_emotion_labels)


if __name__ == "__main__":
    unittest.main()
