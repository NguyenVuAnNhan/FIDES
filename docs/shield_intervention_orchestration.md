# FIDES Shield Intervention Orchestration

## Decision

Behavioral-science intervention should not be added to the Shield scam-signal input schema.

The Shield request payload represents what FIDES knows before making a decision. Intervention orchestration represents what FIDES does after risk scoring.

Therefore, this belongs in the Shield response or an intervention service, not in the incoming scam dataset.

## MVP Flow

```text
Shield request
-> Stage 1 outer context circuit
-> camera and voice challenge if Stage 1 trips
-> Stage 2 invasive check result
-> release, request challenge, or 24h hold
-> assistant message / TTS
-> bank fraud desk or trusted escalation if needed
-> feedback event after outcome
```

The current MVP already returns:

- `risk_score`
- `risk_level`
- `action`
- `circuit_breaker_stage`
- `circuit_breaker_triggered`
- `invasive_check_required`
- `stage_one_score`
- `stage_two_score`
- `explanations`
- `intervention_message`
- `trusted_authority_notification`
- `transaction_hold_hours`

That is enough for the first demo. A later response can add a richer structured `intervention_plan`.

## Circuit-Breaker Actions

| Stage | Action | Meaning |
| --- | --- | --- |
| Stage 1 clear | `allow_with_notice` | Outer context did not trip; transfer proceeds with a normal reminder. |
| Stage 1 tripped, Stage 2 missing | `require_camera_voice_check` | Ask the user to open the camera and speak into the app with consent, then call `POST /api/shield/challenge` with a mock challenge profile. |
| Stage 1 tripped, Stage 2 cleared | `allow_after_challenge` | The transfer proceeds after the invasive check does not find enough evidence to hold. |
| Stage 1 tripped, Stage 2 failed | `withhold_24h_notify_trusted_authority` | Hold the transfer for 24 hours and notify the bank fraud desk or trusted escalation path. |

## Future Intervention Plan Schema

```json
{
  "intervention_plan": {
    "style": "cool_down",
    "assistant_channel": "chatbot_tts",
    "reflection_questions": [
      "Did this caller ask you to keep the transfer secret?",
      "Have you independently called the official organization?",
      "Would you be comfortable if your trusted contact reviewed this transfer?"
    ],
    "warning_explanation": [
      "Caller claimed to be police or an authority figure",
      "Recipient resembles a suspected mule account",
      "Transfer was initiated during an active call"
    ],
    "trusted_contact_required": true,
    "trusted_contact_channel": "vnface_ott",
    "trusted_contact_status": "pending",
    "cool_down_seconds": 60,
    "allow_user_override": false
  }
}
```

## Intervention Levels

Suggested mapping:

| Risk level | Action | Intervention |
| --- | --- | --- |
| `low` | `allow_with_notice` | Small inline reminder. |
| `low` | `allow_after_challenge` | Transfer proceeds after a cleared camera/voice challenge. |
| `elevated` | `require_camera_voice_check` | Reflection prompt plus camera and voice check. |
| `critical` | `withhold_24h_notify_trusted_authority` | 24-hour hold, TTS/chatbot warning, bank fraud desk notification, and optional trusted-contact review. |

## Behavioral-Science Principles

The intervention should:

- slow the user down without shaming them
- ask reflective questions instead of only issuing commands
- explain concrete risk signals
- encourage independent verification through official channels
- use a trusted contact only for high-risk cases
- avoid making the user feel accused or foolish

## Trusted Contact Boundary

Trusted-contact or trusted-authority confirmation should be a separate workflow:

- The user pre-consents to trusted-contact use.
- The bank fraud desk or trusted contact receives minimal transaction context.
- The trusted contact confirms concern, cannot directly control the user's money.
- The user and bank retain the final decision flow.

## Relation To Feedback Learning

Intervention outcome should feed the separate post-intervention feedback pipeline:

- user cancelled transfer
- user continued transfer
- trusted contact confirmed concern
- fraud later confirmed
- false-positive appeal

That feedback pipeline is documented in `docs/shield_feedback_learning_pipeline.md`.
