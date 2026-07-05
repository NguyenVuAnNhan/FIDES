from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services import shield_challenge_service as svc


class ShieldEkycHelperTests(unittest.TestCase):
    def test_parse_liveness_from_message(self) -> None:
        passed = svc._parse_liveness_passed({"liveness_msg": "Người thật"}, liveness_failed=False)
        self.assertTrue(passed)

    def test_parse_liveness_rejects_spoof_message(self) -> None:
        passed = svc._parse_liveness_passed({"liveness_msg": "Khuon mat gia"}, liveness_failed=False)
        self.assertFalse(passed)

    def test_injection_risk_from_fake_liveness(self) -> None:
        risk = svc._injection_risk_from_liveness(
            {"fake_liveness": True, "face_swapping": False},
            liveness_failed=False,
            face_is_live=True,
            mask_detected=False,
            face_match_score=0.9,
            compare_failed=False,
            compare_skipped=False,
        )
        self.assertGreaterEqual(risk, 0.85)

    def test_scripted_behavior_does_not_penalize_stt_fail(self) -> None:
        score, labels = svc._scripted_behavior("", True, None)
        self.assertLess(score, 0.3)
        self.assertIn("insufficient_speech", labels)

    def test_scripted_behavior_uses_scam_signals(self) -> None:
        score, labels = svc._scripted_behavior(
            "cong an yeu cau chuyen tien",
            False,
            "fake_authority",
            stt_confidence=0.9,
            llm_confidence=0.95,
        )
        self.assertGreater(score, 0.6)
        self.assertIn("repeats_caller_phrasing", labels)

    def test_coercion_confidence_blends_stt_and_llm(self) -> None:
        class VoiceStub:
            model_used = True
            prosody = type("Prosody", (), {"prosody_stress_score": 0.7})()

        confidence = svc._coercion_confidence(
            VoiceStub(),
            stt_confidence=0.92,
            llm_confidence=0.9,
            stt_transcript="toi tu xac nhan",
        )
        self.assertGreater(confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
