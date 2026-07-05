from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import ShieldAnalyzeRequest
from backend.app.services.shield_service import analyze_shield_risk, ekyc_identity_blocks_transfer


class ShieldEkycIdentityGateTests(unittest.TestCase):
    def _challenge_request(self, **overrides: object) -> ShieldAnalyzeRequest:
        payload = {
            "transaction_amount": 65_000_000,
            "recipient_name": "Tran Van B",
            "recipient_account": "9704 2222 8800",
            "active_call": True,
            "caller_type": "unknown",
            "recipient_known": False,
            "consent_granted": True,
            "consent_transfer_check": True,
            "shield_path": "transfer_monitoring",
            "ekyc_verification_status": "review",
            "ekyc_liveness_passed": True,
            "ekyc_mask_detected": False,
            "ekyc_face_match_score": 0.6696,
            "ekyc_injection_risk_score": 0.28,
            "audio_source": "uploads/shield/live-check.webm",
            "stt_transcript": "Toi tu xac nhan giao dich nay khong co ai huong dan.",
            "stt_confidence": 0.18,
            "voice_stress_score": 0.74,
            "face_emotion_score": 0.62,
            "coercion_score": 0.58,
            "coercion_confidence": 0.65,
        }
        payload.update(overrides)
        return ShieldAnalyzeRequest(**payload)

    def test_identity_blocks_transfer_for_review_and_low_match(self) -> None:
        request = self._challenge_request()
        self.assertTrue(ekyc_identity_blocks_transfer(request))

    def test_nomatch_review_case_withholds_instead_of_allow(self) -> None:
        request = self._challenge_request(ekyc_verification_status="failed")
        response = analyze_shield_risk(request)
        self.assertEqual(response.action, "withhold_24h_notify_trusted_authority")
        self.assertIn("cannot verify your identity", response.intervention_message.lower())
        self.assertGreaterEqual(response.stage_two_score or 0, 25)

    def test_identity_not_blocked_when_liveness_false_but_match_high(self) -> None:
        request = self._challenge_request(
            ekyc_verification_status="passed",
            ekyc_liveness_passed=False,
            ekyc_face_match_score=0.95,
        )
        self.assertFalse(ekyc_identity_blocks_transfer(request))

    def test_passed_identity_allows_after_challenge_without_scam(self) -> None:
        request = self._challenge_request(
            ekyc_verification_status="passed",
            ekyc_face_match_score=0.96,
            stt_transcript="Toi tu xac nhan giao dich nay khong co ai huong dan.",
            voice_stress_score=0.1,
            face_emotion_score=0.1,
            coercion_score=0.1,
            coercion_confidence=0.1,
        )
        response = analyze_shield_risk(request)
        self.assertEqual(response.action, "allow_after_challenge")


if __name__ == "__main__":
    unittest.main()
