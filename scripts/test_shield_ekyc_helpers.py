from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services import shield_challenge_service as svc


class ShieldEkycHelperTests(unittest.TestCase):
    def test_face_compare_nomatch_checks_msg_and_result(self) -> None:
        self.assertTrue(svc._face_compare_nomatch({"msg": "NOMATCH", "result": "MATCH"}))
        self.assertTrue(svc._face_compare_nomatch({"msg": "MATCH", "result": "NOMATCH"}))
        self.assertFalse(svc._face_compare_nomatch({"msg": "MATCH", "result": "MATCH"}))

    def test_resolve_verification_status_nomatch_in_msg(self) -> None:
        status = svc.resolve_ekyc_verification_status(
            mask_failed=False,
            compare_failed=False,
            compare_skipped=False,
            mask_detected=False,
            face_compare_nomatch=True,
            face_match_score=0.6696,
        )
        self.assertEqual(status, "failed")

    def test_resolve_verification_status_low_score_without_nomatch(self) -> None:
        status = svc.resolve_ekyc_verification_status(
            mask_failed=False,
            compare_failed=False,
            compare_skipped=False,
            mask_detected=False,
            face_compare_nomatch=False,
            face_match_score=0.6696,
        )
        self.assertEqual(status, "review")

    def test_resolve_verification_status_high_match_passes(self) -> None:
        status = svc.resolve_ekyc_verification_status(
            mask_failed=False,
            compare_failed=False,
            compare_skipped=False,
            mask_detected=False,
            face_compare_nomatch=False,
            face_match_score=0.95,
        )
        self.assertEqual(status, "passed")

    def test_injection_risk_from_low_face_match(self) -> None:
        risk = svc._injection_risk_from_ekyc(
            mask_detected=False,
            face_match_score=0.4,
            compare_failed=False,
            compare_skipped=False,
        )
        self.assertGreaterEqual(risk, 0.55)

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
