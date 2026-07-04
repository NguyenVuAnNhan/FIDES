# FIDES Shield Scam Schema Explained

## What This Schema Is For

The FIDES Shield scam schema is the request payload sent to `POST /api/shield/analyze`.

Its job is to describe the state of a transfer at decision time:

- What transaction is being attempted.
- Whether the user appears to be under manipulation.
- What the call/transcript/LLM pipeline detected.
- Whether the recipient looks risky.
- Whether native telemetry or eKYC suggests device/session compromise.
- Which derived model outputs should be fused into a risk decision.

The schema is intentionally broad because APP fraud is not detected by one signal. In these scams, the real user often authenticates successfully and personally approves the transfer. The schema therefore captures the surrounding context: phone call, scam script, stress/coercion, recipient behavior, and device/session anomalies.

## Core Design Principle

The schema stores decision-time signals, not post-decision workflow state.

Included:

- transaction details
- telecom context
- consented audio/transcript outputs
- Smartbot scam classification
- coercion/distress scores
- recipient intelligence
- eKYC/native telemetry signals

Not included:

- intervention plan
- trusted-contact workflow state
- user outcome after the warning
- model feedback events
- offline retraining state

Those belong to separate response, intervention, and feedback schemas.

## Top-Level Dataset Shape

The demo dataset stores Shield cases like this:

```json
{
  "id": "shield-fake-police-critical",
  "title": "Fake police verification",
  "persona": "Retail banking customer",
  "demo_goal": "Show the circuit breaker pausing a transfer while the user is being coached on a call.",
  "payload": {
    "...": "ShieldAnalyzeRequest fields"
  }
}
```

Only `payload` is sent to the Shield API. The surrounding fields are for demo selection, storytelling, and test organization.

The synthetic dataset follows the same shape but generates 500 Shield records from a few fixed madlib-style templates.

## Field Family 1: Transaction Context

These fields describe the transfer itself.

```json
{
  "transaction_amount": 75000000,
  "recipient_name": "Nguyen Van A",
  "recipient_account": "9704 0000 1234",
  "recipient_known": false
}
```

Meaning:

- `transaction_amount`: amount being transferred. High-value transfers trigger stronger friction.
- `recipient_name`: display name used for explanations and intervention messages.
- `recipient_account`: destination account.
- `recipient_known`: whether this recipient is already trusted, known from invoices, or common in user history.

Production source:

- Bank/wallet backend.
- Transaction orchestration service.
- User payee history.

MVP behavior:

- High amount adds risk.
- Unknown recipient adds risk.

## Field Family 2: Telecom Context

These fields model the phone-call environment around the transfer.

```json
{
  "active_call": true,
  "caller_type": "unknown",
  "caller_number": "+882 13 456 789"
}
```

Meaning:

- `active_call`: user is on a call while initiating the transfer.
- `caller_type`: `trusted`, `unknown`, `voip`, or `international`.
- `caller_number`: caller number or normalized caller identifier.

Production source:

- Native mobile app telemetry where legally/technically available.
- Telco integration.
- SDK consumer-provided signal.

Important boundary:

- A normal web app cannot know this reliably.
- The FIDES backend does not magically inspect the device.
- In the SDK/API architecture, the bank or wallet app supplies these derived signals.

MVP behavior:

- Active call adds risk.
- VoIP, international, or unknown caller type adds risk.
- International or suspicious prefixes add risk.

## Field Family 3: Recipient Intelligence

Recipient intelligence models whether the destination account or phone resembles a suspicious recipient or suspected mule account.

```json
{
  "recipient_phone": "+84 903 777 888",
  "vn_social_report_count": 27,
  "vn_social_recent_keywords": ["cong an", "xac minh tai khoan", "chuyen tien"],
  "simo_status": "not_listed",
  "simo_last_checked_at": "2026-06-28T10:00:00Z",
  "graph_risk_score": 0.88,
  "graph_pattern": "fan_in_fan_out",
  "inbound_sender_count_10m": 14,
  "outbound_account_count_10m": 9,
  "median_pass_through_minutes": 3.0,
  "account_age_days": 4,
  "shared_device_cluster_size": 6,
  "funds_moved_within_minutes": true,
  "recipient_risk_level": "critical"
}
```

Meaning:

- `vn_social_report_count`: number of recent reports tied to the recipient account or phone.
- `vn_social_recent_keywords`: keywords seen in those reports.
- `simo_status`: official/interbank suspicious-account status. Example values: `not_checked`, `not_listed`, `watchlisted`, `listed`.
- `graph_risk_score`: graph-derived suspected mule score.
- `graph_pattern`: dominant graph pattern, such as `fan_in_fan_out`, `rapid_pass_through`, or `new_account_high_activity`.
- `inbound_sender_count_10m`: distinct senders into the account in the last 10 minutes.
- `outbound_account_count_10m`: distinct outgoing recipients from the account in the last 10 minutes.
- `median_pass_through_minutes`: how quickly money tends to move onward.
- `account_age_days`: age of the recipient account.
- `shared_device_cluster_size`: number of related accounts sharing device/phone infrastructure.
- `funds_moved_within_minutes`: whether the recipient tends to pass funds onward quickly.
- `recipient_risk_level`: simplified recipient-risk band.

Production source:

- vnSocial/report reputation service.
- SIMO/NHNN or partner-bank lookup.
- FIDES-owned transaction graph service.

MVP behavior:

- vnSocial reports add risk.
- SIMO `watchlisted` or `listed` status adds risk.
- High graph risk score adds risk and explanation.

Important wording:

- Use "suspected mule-account signal".
- Avoid saying the recipient is definitively a mule without human/official confirmation.

## Field Family 4: Native Telemetry And eKYC

These fields model device/session risk and identity-confirmation risk.

```json
{
  "remote_control_detected": false,
  "native_telemetry_available": true,
  "native_telemetry_source": "mock_android_sdk",
  "installed_remote_access_app_detected": false,
  "accessibility_service_risk": false,
  "screen_sharing_detected": false,
  "ekyc_verification_status": "passed",
  "ekyc_liveness_score": 0.91,
  "ekyc_mask_detected": false,
  "ekyc_face_match_score": 0.88,
  "ekyc_injection_risk_score": 0.12,
  "smartux_behavior_anomaly_score": 0.58,
  "smartux_remote_control_score": 0.31,
  "smartux_signals": ["unusual_navigation_sequence", "paste_into_amount_field"]
}
```

Meaning:

- `remote_control_detected`: coarse demo flag for remote-control-like behavior.
- `native_telemetry_available`: whether the SDK consumer supplied native telemetry.
- `native_telemetry_source`: source label, such as `mock_android_sdk`.
- `installed_remote_access_app_detected`: SDK consumer detected known remote-access indicators.
- `accessibility_service_risk`: risky accessibility or overlay behavior was observed.
- `screen_sharing_detected`: screen sharing or screen-control-like behavior was observed.
- `ekyc_verification_status`: `not_checked`, `passed`, `review`, or `failed`.
- `ekyc_liveness_score`: liveness result.
- `ekyc_mask_detected`: mask/spoof signal.
- `ekyc_face_match_score`: face comparison confidence.
- `ekyc_injection_risk_score`: biometric injection risk.
- `smartux_behavior_anomaly_score`: unusual in-app behavior score.
- `smartux_remote_control_score`: remote-control-like behavior score.
- `smartux_signals`: explainable UX signals.

Production source:

- eKYC SDK/API.
- SmartUX or bank app telemetry.
- Native Android/iOS/web integration where available.

Important boundary:

- The SDK consumer collects native telemetry.
- FIDES consumes derived claims/scores.
- We should say "remote-control-like behavior" rather than "always detects remote-control apps."

MVP behavior:

- eKYC review/failure, weak liveness, weak face match, mask, or high injection risk adds risk.
- SmartUX anomaly and remote-control scores add risk.
- Native signals produce explanations but do not require raw biometric data.

## Field Family 5: Consent, Audio, STT, And LLM Scam Patterning

These fields model the SmartVoice and Smartbot pipeline.

```json
{
  "consent_granted": true,
  "audio_source": "fixtures/audio/fake-police-001.wav",
  "stt_transcript": "Toi la cong an...",
  "stt_confidence": 0.94,
  "detected_patterns": [
    "fake_authority",
    "case_involvement",
    "transfer_for_verification",
    "secrecy_pressure"
  ],
  "llm_scam_type": "fake_authority",
  "llm_confidence": 0.91,
  "transcript": "Toi la cong an..."
}
```

Meaning:

- `consent_granted`: whether user consent allows call analysis.
- `audio_source`: fixture path or future processing job reference.
- `stt_transcript`: SmartVoice speech-to-text output.
- `stt_confidence`: speech-to-text confidence.
- `detected_patterns`: fine-grained Smartbot scam signals.
- `llm_scam_type`: top-level scam type.
- `llm_confidence`: scam classification confidence.
- `transcript`: manual fallback transcript for MVP/debugging.

Production source:

- User consent flow.
- SmartVoice or STT provider.
- Smartbot or guarded LLM classifier.

MVP behavior:

- If `stt_transcript` exists, Shield uses it.
- Otherwise, Shield falls back to `transcript`.
- If `llm_scam_type` or `detected_patterns` exists, Shield uses the Smartbot classification.
- Otherwise, it falls back to keyword matching.
- If consent is false, audio/transcript analysis is skipped.

## Field Family 6: Coercion And Distress Signals

These fields model derived signs that the user may be afraid, pressured, or reading from a script.

```json
{
  "voice_stress_score": 0.82,
  "voice_stress_labels": ["elevated_pitch", "speech_hesitation", "fast_breathing"],
  "face_emotion_score": 0.76,
  "face_emotion_labels": ["fear", "distress", "low_eye_contact"],
  "scripted_behavior_score": 0.71,
  "scripted_behavior_labels": [
    "monotone_reading",
    "long_pauses_before_answers",
    "repeats_caller_phrasing"
  ],
  "coercion_score": 0.79,
  "coercion_confidence": 0.84
}
```

Meaning:

- `voice_stress_score`: derived stress signal from consented audio.
- `voice_stress_labels`: voice cues behind the score.
- `face_emotion_score`: visual distress signal.
- `face_emotion_labels`: visual cues behind the score.
- `scripted_behavior_score`: likelihood user is reading/following a script.
- `scripted_behavior_labels`: behavioral cues behind the score.
- `coercion_score`: fused coercion/distress score.
- `coercion_confidence`: confidence in that fusion.

Production source:

- Consented audio analysis.
- Consented camera/video analysis if available.
- SmartVision/vnFace or equivalent provider.
- Multimodal fusion service.

Important boundary:

- These are assistive risk signals, not proof of emotion or coercion.
- Prefer "visual distress / behavioral cues" over strong claims like definitive micro-expression truth.
- Avoid storing raw face frames, voiceprints, or biometric templates.

MVP behavior:

- High coercion score and confidence add risk and produce a `Coercion and distress signals` explanation.

## How The Backend Fuses The Schema

The current scorer is intentionally transparent and rule-based. It does not claim to be a trained fraud model.

Shield now uses a two-stage circuit-breaker flow.

### Stage 1: Outer Context Circuit

Stage 1 uses cheap, low-friction signals that can be checked before interrupting the user:

- high-value transfer
- unknown recipient
- active call
- suspicious caller context
- international or high-risk caller prefix
- vnSocial reports
- SIMO status
- graph-derived recipient risk
- remote-control signal
- SmartUX/native telemetry risk

The outer breaker score starts at `10`. If the score reaches `45`, the circuit breaker trips.

If the breaker does not trip, Shield returns:

```text
circuit_breaker_stage = outer_context_clear
action = allow_with_notice
```

If the breaker trips and no camera/voice challenge evidence is present yet, Shield returns:

```text
circuit_breaker_stage = invasive_check_required
action = require_camera_voice_check
```

This means the app should ask the user, with consent, to open the camera and speak into the app.
In the MVP frontend, the challenge panel calls `POST /api/shield/challenge` with:

```json
{
  "transaction": { "...": "original ShieldAnalyzeRequest" },
  "challenge_profile": "clear_user",
  "spoken_response": "User's challenge phrase or demo transcript"
}
```

The backend does not automatically pass the challenge. It calls mocked provider APIs and re-runs Shield analysis from their outputs:

- mock eKYC API: liveness, mask/spoof, face match, injection risk
- mock SmartVoice API: speech-to-text transcript and confidence
- mock Smartbot API: scam-script classification and confidence
- mock coercion API: voice stress, visual distress, scripted behavior, aggregate coercion

Available demo profiles are `clear_user`, `coerced_authority`, `deepfake_injection`, and `scripted_remote_support`.

### Stage 2: Invasive Camera And Voice Challenge

Stage 2 runs only after Stage 1 trips. It uses higher-friction checks:

- eKYC status
- liveness score
- mask/spoof signal
- face-match score
- biometric injection risk
- SmartVoice transcript
- Smartbot scam classification
- transcript keyword fallback
- voice stress
- visual distress
- scripted-behavior signal
- aggregate coercion score

The Stage 2 fail threshold is `25`. If Stage 2 fails, Shield returns:

```text
circuit_breaker_stage = withhold_and_notify
action = withhold_24h_notify_trusted_authority
transaction_hold_hours = 24
trusted_authority_notification = true
```

For the MVP, "trusted authority" means the bank fraud desk or equivalent trusted escalation path. In a production bank deployment, this could also fan out to a pre-consented trusted contact, but that should be governed by a separate consent workflow.

If Stage 2 does not fail, the transfer is released:

```text
circuit_breaker_stage = invasive_check_cleared
action = allow_after_challenge
```

The response still includes the familiar top-level fields:

- `risk_score`
- `risk_level`
- `action`
- `scam_type`
- `explanations`
- `intervention_message`

It also includes staged fields:

- `circuit_breaker_stage`
- `circuit_breaker_triggered`
- `invasive_check_required`
- `stage_one_score`
- `stage_two_score`
- `stage_one_flags`
- `stage_two_flags`
- `trusted_authority_notification`
- `trusted_authority_message`
- `transaction_hold_hours`
- `challenge_profile`
- `mock_provider_calls`

This is a good MVP design because judges can inspect why the low-friction circuit tripped separately from why the invasive challenge passed or failed.

## What The Schema Does Not Do

### It Does Not Define Intervention Policy

Reflection questions, chatbot/TTS cool-down, trusted-contact confirmation, and override rules belong to the response/intervention layer.

See `docs/shield_intervention_orchestration.md`.

### It Does Not Define Feedback Learning

User outcomes and fraud labels are recorded after the intervention.

Those events should be stored separately and used for offline model/rule updates.

See `docs/shield_feedback_learning_pipeline.md`.

### It Does Not Define The Graph Database

The Shield payload receives graph-derived features.

The actual graph database nodes, relationships, and feature queries are defined separately.

See `docs/graph_database_schema.md`.

## Why The Schema Is Good For The MVP

This schema lets us demo the full FIDES thesis without needing every production integration live:

- It shows how telecom context helps detect APP fraud.
- It shows how SmartVoice/Smartbot detects scam scripts.
- It shows how recipient intelligence catches suspected mule behavior.
- It shows how native telemetry and eKYC add device/session protection.
- It keeps sensitive raw data out of the payload.
- It produces clear explanations for every intervention.
- It can be populated by synthetic records, real API outputs, or future SDK integrations.

In short, the schema is a risk-fusion contract. It tells FIDES what the bank app, AI services, graph service, eKYC provider, and SDK consumer have observed, then lets Shield produce one explainable decision.
