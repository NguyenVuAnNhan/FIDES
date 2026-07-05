# FIDES Shield Feedback Learning Pipeline

## Decision

Post-intervention learning should not be added to the Shield transaction payload.

The Shield payload represents the state available at decision time:

- transaction context
- telecom context
- SmartVoice/Smartbot outputs
- coercion/distress signals
- recipient-risk intelligence
- native telemetry/eKYC signals

Feedback learning happens after an intervention. It should use a separate event schema so the active transfer decision remains fast, auditable, and stable.

## MVP Pipeline

```text
Shield decision
-> intervention shown
-> user/bank outcome captured
-> anonymized feedback event stored
-> pattern registry or model candidates updated offline
-> validation
-> new rules/model version deployed
```

For the MVP, this can be mocked as an append-only feedback log and a versioned pattern registry.

## Feedback Event Schema

```json
{
  "event_id": "evt_001",
  "intervention_id": "int_001",
  "timestamp": "2026-06-28T10:12:00Z",
  "anonymized_user_id": "user_hash_abc",
  "anonymized_recipient_id": "acct_hash_xyz",
  "scam_type": "fake_authority",
  "detected_patterns": [
    "fake_authority",
    "transfer_for_verification",
    "secrecy_pressure"
  ],
  "risk_score": 100,
  "action_taken": "withhold_24h_notify_trusted_authority",
  "user_outcome": "cancelled_transfer",
  "confirmed_label": "fraud_prevented",
  "new_keywords": [
    "tai khoan lien quan vu an"
  ],
  "model_version": "shield_rules_v1"
}
```

## Outcome Values

Suggested `user_outcome` values:

- `continued_transfer`
- `cancelled_transfer`
- `called_trusted_contact`
- `reported_scam`
- `appealed_warning`
- `unknown`

Suggested `confirmed_label` values:

- `fraud_prevented`
- `confirmed_fraud`
- `false_positive`
- `benign_transfer`
- `needs_review`
- `unknown`

## Model Update Policy

Do not update the live model synchronously inside the transfer flow.

Instead:

1. Store feedback as an anonymized event.
2. Review or auto-label outcomes.
3. Update a candidate pattern registry, ruleset, or model offline.
4. Validate against regression cases and false-positive thresholds.
5. Promote a new version through a model registry.
6. Keep rollback available.

## MVP Implementation Path

Near-term implementation:

- Add `POST /api/feedback/intervention`.
- Store events in a local JSONL file or database table.
- Add `model_version` to Shield responses later if needed.
- Move hardcoded scam patterns from Python into a versioned JSON registry.
- Build a tiny admin view showing new keywords and outcome counts.

This is enough to demonstrate "cang dung cang thong minh" without making unsafe live model updates.

## Privacy Position

Feedback events should avoid raw sensitive data:

- Hash user/account/phone identifiers.
- Avoid storing raw audio, face frames, biometric templates, or full call transcripts.
- Prefer derived labels, pattern names, risk scores, and short candidate keywords.
- Keep immutable audit logs for model-update decisions.
