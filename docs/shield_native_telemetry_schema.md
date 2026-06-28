# FIDES Shield Native Telemetry And eKYC Schema

## Purpose

This schema models deepfake/liveness and remote-control-like behavior signals for Shield.

Important boundary: FIDES backend does not directly inspect the user's device. The integrating bank app, wallet app, or SDK consumer is responsible for collecting native telemetry with the correct platform permissions, consent, and legal basis. FIDES receives derived signals and fuses them into a risk decision.

## Shield Payload Fields

| Field | Type | Source in MVP | Meaning |
| --- | --- | --- | --- |
| `native_telemetry_available` | boolean | Dataset/form | Whether the SDK consumer supplied native telemetry for this transfer. |
| `native_telemetry_source` | string or null | Dataset/form | Source label, such as `mock_android_sdk`, `bank_android_app`, or `wallet_ios_app`. |
| `installed_remote_access_app_detected` | boolean | SDK consumer claim | Whether the app detected known remote-access app indicators. |
| `accessibility_service_risk` | boolean | SDK consumer claim | Whether risky accessibility/overlay behavior was observed. |
| `screen_sharing_detected` | boolean | SDK consumer claim | Whether screen sharing or screen-control-like telemetry was observed. |
| `ekyc_verification_status` | string | eKYC provider or mock | One of `not_checked`, `passed`, `review`, or `failed`. |
| `ekyc_liveness_score` | number or null | eKYC provider output | Liveness score from `0.0` to `1.0`. |
| `ekyc_mask_detected` | boolean | eKYC provider output | Whether a mask/spoof indicator was detected. |
| `ekyc_face_match_score` | number or null | eKYC provider output | Face comparison score from `0.0` to `1.0`. |
| `ekyc_injection_risk_score` | number or null | eKYC provider output | Biometric injection risk from `0.0` to `1.0`. |
| `smartux_behavior_anomaly_score` | number or null | SmartUX or app telemetry | In-app behavior anomaly score from `0.0` to `1.0`. |
| `smartux_remote_control_score` | number or null | SmartUX or app telemetry | Remote-control-like behavior score from `0.0` to `1.0`. |
| `smartux_signals` | string array | SmartUX or app telemetry | Explainable UX signals such as `rapid_pointer_jumps`, `paste_into_amount_field`, or `unusual_navigation_sequence`. |

## Backend Behavior

Shield adds explainable risk weight for:

- failed/review eKYC status
- low liveness score
- weak face match
- mask/spoof signal
- high biometric injection risk
- remote-access app signal
- risky accessibility or screen-sharing signal
- high SmartUX behavior anomaly score
- high SmartUX remote-control score

These signals complement the existing `remote_control_detected` field. `remote_control_detected` is a coarse demo flag; the SmartUX/native telemetry fields explain why that flag may be true.

## Real-Life Capability

eKYC/liveness:

- Feasible through an eKYC SDK/API.
- Should not be hand-rolled for production.
- Biometric injection detection should come from a serious identity provider or hardened SDK.

SmartUX behavior anomaly:

- Feasible inside the banking app or web app for in-app events.
- Examples: paste into amount/OTP fields, rapid pointer jumps, unusual navigation sequence, repeated corrections, focus changes, and abnormal typing cadence.

Remote-control detection:

- Android: possible through limited heuristics if permissions, package visibility rules, and OS version allow it.
- iOS: very limited for third-party banking apps.
- Web: limited to behavioral inference inside the page.
- Telco or device-management partnerships may improve coverage, but FIDES should not claim universal remote-control detection.

## Product Wording

Use:

> SmartUX detects remote-control-like behavior and behavioral anomaly signals supplied by the integrating app SDK.

Avoid:

> FIDES always detects remote-control apps.

## Privacy Position

- Store derived scores and labels, not raw biometric templates.
- Avoid storing raw face frames or long-lived device identifiers unless legally required and explicitly consented.
- Keep eKYC and native telemetry explanations reviewable.
- Treat all outputs as risk signals, not final fraud verdicts.

