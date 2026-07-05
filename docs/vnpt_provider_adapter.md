# VNPT Provider Adapter

## Purpose

Shield Path B challenge calls VNPT for eKYC (face) and optionally SmartVoice (STT/voice verify).

- **eKYC** always uses the real VNPT API when `VNPT_EKYC_MODE=real` and credentials are configured. There is no offline eKYC mock path.
- **SmartVoice** can stay on mock fixtures in `backend/app/data/vnpt_mocks/smartvoice/` until credentials are ready.

The normalized Shield schema stays the same regardless of provider mode.

## Environment

Copy `.env.example` to `.env` and fill:

```bash
VNPT_EKYC_MODE=real
VNPT_SMARTVOICE_MODE=mock
VNPT_BASE_URL=https://api.idg.vnpt.vn
VNPT_EKYC_ACCESS_TOKEN=...
VNPT_EKYC_TOKEN_ID=...
VNPT_EKYC_TOKEN_KEY=...
# Optional body token; falls back to VNPT_EKYC_TOKEN_ID when empty
VNPT_EKYC_TOKEN=
VNPT_MAC_ADDRESS=TEST1
```

Per-product credentials override the global fallback (`VNPT_ACCESS_TOKEN`, `VNPT_TOKEN_ID`, `VNPT_TOKEN_KEY`).

Set `VNPT_SMARTVOICE_MODE=real` when SmartVoice credentials are available.

## Shield Challenge Request

`POST /api/shield/challenge` accepts:

```json
{
  "transaction": { "...": "ShieldAnalyzeRequest" },
  "ekyc_image_ref": "uploads/ekyc/selfie-abc123.jpg",
  "ekyc_document_ref": "uploads/ekyc/document-def456.jpg",
  "stt_audio_ref": "mock_payload/stt_audio_1",
  "voice_reference_ref": "mock_payload/customer_voice_samples/voice_ref_1",
  "client_session": "shield-demo-browser-session"
}
```

Field meaning:

| Field | Meaning |
| --- | --- |
| `transaction` | Original Stage 1 Shield transaction context. |
| `ekyc_image_ref` | **Required.** Live selfie path returned from upload or stored customer file ref. |
| `ekyc_document_ref` | Optional CCCD/portrait image for face compare. |
| `stt_audio_ref` | Audio file reference for SmartVoice STT (mock or real). |
| `voice_reference_ref` | Stored customer voice sample for SmartVoice voice verification. |
| `client_session` | Correlation ID passed to VNPT eKYC endpoints. |

When a reference resolves to a local file, the backend uploads it via `POST /file-service/v1/addFile` and passes the returned `object.hash` to face APIs (not base64).

## Upload eKYC Images

`POST /api/shield/challenge/upload-ekyc` accepts multipart form data:

| Field | Required | Notes |
| --- | --- | --- |
| `selfie` | yes | Live face image (PNG/JPG/WEBP, max 8MB). |
| `document` | no | CCCD/portrait image for face compare. |

Saved files are stored under `uploads/ekyc/` and returned as refs such as `uploads/ekyc/selfie-<uuid>.jpg`.

The Shield demo UI always uploads a selfie in step 2 before calling `/api/shield/challenge`.

Smoke-test credentials and endpoints:

```bash
python3 scripts/smoke_vnpt_ekyc.py --selfie /path/to/selfie.jpg --document /path/to/cmnd.jpg
```

## Called VNPT Endpoints

Real mode targets the contracts in `docs/api_references/vnpt/endpoint_contracts.md`:

| Product | Endpoint | Request |
| --- | --- | --- |
| eKYC | `POST /file-service/v1/addFile` | Multipart `file`, `title`, `description`; response `object.hash` feeds face APIs. |
| eKYC | `POST /ai/v1/face/liveness` | JSON `img` (hash), `client_session`, `token`. |
| eKYC | `POST /ai/v1/face/mask` | JSON `img` (hash), `client_session`, `token`. |
| eKYC | `POST /ai/v1/face/compare` | JSON `img_front`, `img_face` (hashes), `client_session`, `token`. |
| SmartVoice | `POST /stt-service/v3/standard` | Binary audio body with STT headers. |
| SmartVoice Voice Verification | `POST /v1/voice-id/audio/upload` | Upload customer reference and challenge audio. |
| SmartVoice Voice Verification | `POST /v1/voice-id/audio/encode` | Encode uploaded audio URLs into voice IDs. |
| SmartVoice Voice Verification | `GET /voiceid/api/v1/audio/verify` | Compare two encoded voice IDs. |

The adapter normalizes provider JSON into Shield fields including `ekyc_verification_status`, `ekyc_liveness_passed`, `ekyc_mask_detected`, `ekyc_face_match_score`, and `ekyc_injection_risk_score`.

VNPT face liveness is treated as boolean. `object.liveness=false` fails the challenge.

SmartVoice voice verification is treated as a score. A match score below `0.55` fails Stage 2; below `0.75` enters review.

VNPT eKYC error payloads (`statusCode` 400/408, `messageFields`, empty `object`) map to `ekyc_verification_status=failed` with provider notes in the Shield explanation list.
