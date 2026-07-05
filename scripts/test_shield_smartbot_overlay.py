from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models import Explanation, ShieldAnalyzeRequest, ShieldAnalyzeResponse
from backend.app.services.shield_service import apply_smartbot_response_overlay


class ShieldSmartbotOverlayTests(unittest.TestCase):
    def test_overlay_message_and_withhold_action(self) -> None:
        request = ShieldAnalyzeRequest(
            transaction_amount=65000000,
            recipient_name="Tran Van B",
            recipient_account="9704 2222 8800",
            llm_scam_type="fake_authority",
            detected_patterns=["fake_authority"],
            smartbot_intervention_message="Giao dich co dau hieu lua dao. Hay tam dung.",
            smartbot_recommended_action="trigger_circuit_breaker",
            smartbot_risk_level="high",
        )
        base = ShieldAnalyzeResponse(
            risk_score=70,
            risk_level="elevated",
            action="allow_after_challenge",
            stage_one_score=50,
            stage_two_score=30,
            scam_type="fake_authority",
            explanations=[Explanation(label="test", detail="detail", weight=0)],
            intervention_message="English fallback message.",
        )
        result = apply_smartbot_response_overlay(request, base)
        self.assertEqual(result.intervention_message, "Giao dich co dau hieu lua dao. Hay tam dung.")
        self.assertEqual(result.action, "withhold_24h_notify_trusted_authority")
        self.assertEqual(result.risk_level, "critical")
        self.assertTrue(result.trusted_authority_notification)

    def test_overlay_message_without_forcing_withhold_when_safe(self) -> None:
        request = ShieldAnalyzeRequest(
            transaction_amount=65000000,
            recipient_name="Tran Van B",
            recipient_account="9704 2222 8800",
            smartbot_intervention_message="Bot message that should still display.",
            smartbot_recommended_action="trigger_circuit_breaker",
        )
        base = ShieldAnalyzeResponse(
            risk_score=20,
            risk_level="low",
            action="allow_after_challenge",
            stage_one_score=50,
            stage_two_score=10,
            scam_type=None,
            explanations=[],
            intervention_message="English fallback message.",
        )
        result = apply_smartbot_response_overlay(request, base)
        self.assertEqual(result.intervention_message, "Bot message that should still display.")
        self.assertEqual(result.action, "allow_after_challenge")


if __name__ == "__main__":
    unittest.main()
