# VNPT Provider Adapter

## Purpose

The Shield camera/voice challenge can run in two modes:

- `mock`: fully offline, using `backend/app/data/vnpt_mocks/`.
- `real`: calls VNPT endpoints using credentials from `.env`.

The normalized Shield schema stays the same in both modes. This lets us rehearse the demo with mocks now, then record real files and tune thresholds once VNPT access is available.

## Environment

Copy `.env.example` to `.env` and fill:

```bash
VNPT_PROVIDER_MODE=real
VNPT_BASE_URL=https://api.idg.vnpt.vn
VNPT_ACCESS_TOKEN=...
VNPT_TOKEN_ID=...
VNPT_TOKEN_KEY=...
VNPT_EKYC_TOKEN=...
VNPT_MAC_ADDRESS=TEST1
VNPT_STT_SAMPLE_RATE=16000
VNPT_STT_CONTENT_TYPE=audio/wav
VNPT_VOICE_BASE_URL=https://api.idg.vnpt.vn/voice-service
VNPT_VOICE_VERIFY_EMAIL=demo-customer@fides.local
VNPT_VOICE_VERIFY_NAME=FIDES Demo Customer
```

If `VNPT_PROVIDER_MODE` is not `real`, or if the token headers are missing, the backend stays in mock mode.

## Shield Challenge Request

`POST /api/shield/challenge` accepts:

```json
{
  "transaction": { "...": "ShieldAnalyzeRequest" },
  "ekyc_image_ref": "mock_payload/ekyc_img_1",
  "ekyc_document_ref": "mock_payload/customer_document_faces/doc_face_1",
  "stt_audio_ref": "mock_payload/stt_audio_1",
  "voice_reference_ref": "mock_payload/customer_voice_samples/voice_ref_1",
  "client_session": "shield-demo-browser-session"
}
```

Field meaning:

| Field | Meaning |
| --- | --- |
| `transaction` | Original Stage 1 Shield transaction context. |
| `ekyc_image_ref` | Live face/selfie image reference for liveness and mask checks. |
| `ekyc_document_ref` | Optional document/front-ID image reference for face compare. Mock assets live in `mock_payload/customer_document_faces/`. |
| `stt_audio_ref` | Audio file reference for SmartVoice STT. |
| `voice_reference_ref` | Stored customer voice sample for SmartVoice voice verification. Mock assets live in `mock_payload/customer_voice_samples/`. |
| `client_session` | Correlation ID passed to VNPT eKYC endpoints. |

When a reference resolves to a local file, the backend sends images as base64 strings, sends STT audio as a binary body, and uploads voice verification samples through the SmartVoice voice-service flow. When the reference does not resolve to a file, image refs are sent as-is so hosted file hashes/URLs can be tested later.

## Called VNPT Endpoints

Real mode currently targets the contracts in `docs/api_references/vnpt/endpoint_contracts.md`:

| Product | Endpoint | Request |
| --- | --- | --- |
| eKYC | `POST /ai/v1/face/liveness` | JSON `img`, `client_session`, optional `token`. |
| eKYC | `POST /ai/v1/face/mask` | JSON `img`, `client_session`. |
| eKYC | `POST /ai/v1/face/compare` | JSON `img_front`, `img_face`, `client_session`, optional `token`. |
| SmartVoice | `POST /stt-service/v3/standard` | Binary audio body with STT headers. |
| SmartVoice Voice Verification | `POST /v1/voice-id/audio/upload` | Upload customer reference and challenge audio. |
| SmartVoice Voice Verification | `POST /v1/voice-id/audio/encode` | Encode uploaded audio URLs into voice IDs. |
| SmartVoice Voice Verification | `GET /voiceid/api/v1/audio/verify` | Compare two encoded voice IDs. |

The adapter normalizes provider JSON into:

- `ekyc_verification_status`
- `ekyc_liveness_passed`
- `ekyc_mask_detected`
- `ekyc_face_match_score`
- `ekyc_injection_risk_score`
- `stt_transcript`
- `stt_confidence`
- `voice_reference_source`
- `voice_verification_status`
- `voice_match_score`
- `voice_match_threshold`

The API response also includes `provider_mode` and `provider_raw_responses`. For backward compatibility, the same payload is also mirrored into the legacy `mock_provider_raw_responses` field.

## Tuning Plan

1. Keep `VNPT_PROVIDER_MODE=mock` for the judged offline demo.
2. Record real challenge images/audio into `mock_payload/` or another local folder.
3. Switch `.env` to `VNPT_PROVIDER_MODE=real`.
4. Run `POST /api/shield/challenge` and inspect `provider_raw_responses`.
5. Tune face-compare, STT, and voice-verification thresholds against actual provider score distributions.

VNPT face liveness is treated as boolean. `object.liveness=false` fails the challenge and triggers the Stage 2 alarm. `object.liveness=true` adds no liveness risk by itself. The legacy `ekyc_liveness_score` field remains only for older synthetic/manual payloads.

SmartVoice voice verification is treated as a score. A match score below `0.55` fails Stage 2, a score below the current `0.75` threshold enters review, and a score at or above threshold adds no voice-identity risk.

The current production gap is upload UX, not backend integration. The route already accepts file refs; a later frontend can replace the dropdowns with file upload controls.
