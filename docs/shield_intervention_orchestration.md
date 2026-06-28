# FIDES Shield Intervention Orchestration

## Decision

Behavioral-science intervention should not be added to the Shield scam-signal input schema.

The Shield request payload represents what FIDES knows before making a decision. Intervention orchestration represents what FIDES does after risk scoring.

Therefore, this belongs in the Shield response or an intervention service, not in the incoming scam dataset.

## MVP Flow

```text
Shield request
-> risk score and explanations
-> intervention policy
-> assistant message / TTS
-> trusted-contact confirmation if needed
-> feedback event after outcome
```

The current MVP already returns:

- `risk_score`
- `risk_level`
- `action`
- `explanations`
- `intervention_message`

That is enough for the first demo. A later response can add a structured `intervention_plan`.

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
| `elevated` | `step_up_verification` | Reflection questions and recipient verification prompt. |
| `critical` | `pause_transfer` | Cool-down, TTS/chatbot warning, trusted-contact confirmation, and optional human review. |

## Behavioral-Science Principles

The intervention should:

- slow the user down without shaming them
- ask reflective questions instead of only issuing commands
- explain concrete risk signals
- encourage independent verification through official channels
- use a trusted contact only for high-risk cases
- avoid making the user feel accused or foolish

## Trusted Contact Boundary

Trusted-contact confirmation should be a separate workflow:

- The user pre-consents to trusted-contact use.
- The trusted contact receives minimal transaction context.
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

