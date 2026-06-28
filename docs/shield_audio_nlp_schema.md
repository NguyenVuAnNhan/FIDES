# FIDES Shield Audio and Scam-Script Schema

## Purpose

Shield scenarios model this MVP pipeline:

`consent -> audio/visual source -> SmartVoice speech-to-text -> Smartbot scam-pattern classification -> coercion/distress signals -> Shield risk decision`

The dataset does not require real audio for every synthetic record. Instead, it stores stable mock references and the derived outputs needed to demo the product behavior.

## Shield Payload Fields

| Field | Type | Source in MVP | Meaning |
| --- | --- | --- | --- |
| `consent_granted` | boolean | Dataset/form | Whether the user allowed call analysis for this transfer. |
| `audio_source` | string or null | Dataset fixture reference | Path or ID for the call audio. Real audio can be added later for curated cases. |
| `stt_transcript` | string | Mock SmartVoice output | Transcript produced from the call audio. This is preferred over `transcript` when present. |
| `stt_confidence` | number or null | Mock SmartVoice output | Speech-to-text confidence from `0.0` to `1.0`. |
| `detected_patterns` | string array | Mock Smartbot output | Fine-grained scam-script signals found by the language model. |
| `llm_scam_type` | string or null | Mock Smartbot output | Top-level scam class, such as `fake_authority`, `otp_theft`, `investment`, or `remote_support`. |
| `llm_confidence` | number or null | Mock Smartbot output | Language-model confidence from `0.0` to `1.0`. |
| `voice_stress_score` | number or null | Mock SmartVoice/voice-stress output | Derived stress signal from consented audio, from `0.0` to `1.0`. |
| `voice_stress_labels` | string array | Mock voice-stress output | Explainable voice cues such as `elevated_pitch` or `speech_hesitation`. |
| `face_emotion_score` | number or null | Mock SmartVision/vnFace output | Derived visual distress signal, from `0.0` to `1.0`. |
| `face_emotion_labels` | string array | Mock visual-analysis output | Explainable visual cues such as `distress` or `low_eye_contact`. |
| `scripted_behavior_score` | number or null | Mock multimodal behavior output | Likelihood that the user appears to be reading or following a script. |
| `scripted_behavior_labels` | string array | Mock behavior-analysis output | Explainable behavior cues such as `monotone_reading` or `repeats_caller_phrasing`. |
| `coercion_score` | number or null | Mock fusion output | Aggregate coercion/distress score derived from audio, visual, and behavior cues. |
| `coercion_confidence` | number or null | Mock fusion output | Confidence in the aggregate coercion score. |
| `transcript` | string | Manual fallback | Legacy/manual transcript used when `stt_transcript` is unavailable. |

Existing telecom and transaction fields remain part of the same Shield payload:

- `transaction_amount`
- `recipient_name`
- `recipient_account`
- `active_call`
- `caller_type`
- `caller_number`
- `recipient_known`
- `remote_control_detected`

## Pattern Labels

Current MVP pattern labels include:

- `fake_authority`
- `case_involvement`
- `transfer_for_verification`
- `secrecy_pressure`
- `otp_theft`
- `credential_extraction`
- `security_support_impersonation`
- `investment`
- `guaranteed_return`
- `urgency_pressure`
- `remote_support`
- `screen_control`
- `refund_promise`
- `transfer_test`

Only the top-level labels are currently used as `llm_scam_type`. The fine-grained labels are kept for explanations, demos, dashboards, and future model evaluation.

## Backend Behavior

The backend keeps backward compatibility:

1. If `stt_transcript` exists, Shield analyzes it.
2. Otherwise, Shield falls back to `transcript`.
3. If `llm_scam_type` or `detected_patterns` exists and `consent_granted` is true, Shield uses the Smartbot classification as the primary scam-script signal.
4. If no Smartbot output exists and `consent_granted` is true, Shield falls back to keyword pattern matching over the transcript.
5. If `consent_granted` is false, Shield skips audio/transcript analysis and uses transaction plus telecom context only.
6. If `coercion_score` exists, Shield adds an explainable coercion/distress risk signal using the aggregate score and confidence.

## Real-Life Mapping

In production:

- `consent_granted` should come from an explicit consent flow.
- `audio_source` should be short-lived and access-controlled, or replaced by a processing job ID.
- `stt_transcript` and `stt_confidence` would come from SmartVoice.
- `detected_patterns`, `llm_scam_type`, and `llm_confidence` would come from Smartbot or another guarded language-model classifier.
- `voice_stress_score` and `voice_stress_labels` could come from consented audio analysis.
- `face_emotion_score` and `face_emotion_labels` require camera/video consent and should be framed as visual distress or behavioral cues, not definitive emotion or intent detection.
- `scripted_behavior_score` should be treated as an assistive signal, not proof that the user is coerced.
- `coercion_score` should be a derived fusion score. Avoid storing raw face frames, biometric templates, or long-lived audio embeddings unless there is a clear legal basis and retention policy.
- Raw audio and transcript retention should be minimized. Prefer storing derived risk features and explanations instead of full call content where possible.
