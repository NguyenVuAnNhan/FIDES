#!/usr/bin/env python3
"""Unit tests for VNPT SmartVision detect-face response parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.smartvision.parser import parse_smartvision_face_emotion


class SmartvisionParserTests(unittest.TestCase):
    def test_detect_face_hackathon_payload(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "object": {
                    "message": {
                        "id": 1783240880283,
                        "info": {
                            "face_bboxs": [[115, 126, 363, 483]],
                            "face_scores": [0.45550790429115295],
                            "face_landmarks": [
                                [
                                    [184.68, 263.93],
                                    [295.76, 260.42],
                                    [240.71, 329.28],
                                    [197.85, 399.61],
                                    [288.21, 396.99],
                                ]
                            ],
                        },
                    }
                }
            }
        )
        self.assertEqual(parsed.parse_source, "detect_face")
        self.assertIsNotNone(parsed.face_emotion_score)
        self.assertTrue(parsed.face_emotion_labels)

    def test_detect_face_multiple_faces(self) -> None:
        parsed = parse_smartvision_face_emotion(
            {
                "object": {
                    "info": {
                        "face_bboxs": [[0, 0, 1, 1], [2, 2, 3, 3]],
                        "face_scores": [[0.91], [0.88]],
                    }
                }
            }
        )
        self.assertEqual(parsed.dominant_emotion, "multiple_faces")
        self.assertIn("multiple_faces", parsed.face_emotion_labels)
        self.assertGreaterEqual(parsed.face_emotion_score or 0, 0.58)

    def test_detect_face_no_face(self) -> None:
        parsed = parse_smartvision_face_emotion({"object": {"info": {"face_bboxs": [], "face_scores": []}}})
        self.assertEqual(parsed.parse_source, "detect_face")
        self.assertEqual(parsed.face_emotion_labels, ["no_face_detected"])

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

    def test_aggregate_multi_frame_max_score(self) -> None:
        from backend.app.services.smartvision.parser import SmartvisionFaceEmotion, aggregate_smartvision_frames

        calm = SmartvisionFaceEmotion(
            face_emotion_score=0.22,
            face_emotion_labels=["calm"],
            dominant_emotion="calm",
            parse_source="detect_face",
        )
        distress = SmartvisionFaceEmotion(
            face_emotion_score=0.61,
            face_emotion_labels=["low_eye_contact"],
            dominant_emotion="low_eye_contact",
            parse_source="detect_face",
        )
        aggregated = aggregate_smartvision_frames([calm, distress])
        self.assertEqual(aggregated.parse_source, "multi_frame_aggregate")
        self.assertEqual(aggregated.face_emotion_score, 0.61)
        self.assertIn("calm", aggregated.face_emotion_labels)
        self.assertIn("low_eye_contact", aggregated.face_emotion_labels)


if __name__ == "__main__":
    unittest.main()
