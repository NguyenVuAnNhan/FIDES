# VNPT Provider Adapter

## Purpose

Shield Path B challenge calls VNPT for eKYC (face) and SmartVoice STT.

- **eKYC** always uses the real VNPT API when `VNPT_EKYC_MODE=real` and credentials are configured. There is no offline eKYC mock path.
- **SmartVoice STT** uses the real VNPT API when `VNPT_SMARTVOICE_MODE=real` and credentials are configured. Mock fixtures in `backend/app/data/vnpt_mocks/smartvoice/` are used only when SmartVoice mode is `mock`.

The normalized Shield schema stays the same regardless of provider mode.

## Environment

Copy `.env.example` to `.env` and fill:

```bash
VNPT_EKYC_MODE=real
VNPT_SMARTVOICE_MODE=real
VNPT_BASE_URL=https://api.idg.vnpt.vn
VNPT_EKYC_ACCESS_TOKEN=...
VNPT_EKYC_TOKEN_ID=...
VNPT_EKYC_TOKEN_KEY=...
# Optional body token; falls back to VNPT_EKYC_TOKEN_ID when empty
VNPT_EKYC_TOKEN=
VNPT_MAC_ADDRESS=TEST1
```

Per-product credentials override the global fallback (`VNPT_ACCESS_TOKEN`, `VNPT_TOKEN_ID`, `VNPT_TOKEN_KEY`).

Set `VNPT_SMARTVOICE_MODE=mock` to fall back to offline SmartVoice fixtures.

## Shield Challenge Request

`POST /api/shield/challenge` accepts:

```json
{
  "transaction": { "...": "ShieldAnalyzeRequest" },
  "ekyc_image_ref": "uploads/ekyc/selfie-abc123.jpg",
  "ekyc_document_ref": "uploads/ekyc/document-def456.jpg",
  "stt_audio_ref": "uploads/smartvoice/challenge-abc123.wav",
  "client_session": "shield-demo-browser-session"
}
```

Field meaning:

| Field | Meaning |
| --- | --- |
| `transaction` | Original Stage 1 Shield transaction context. |
| `ekyc_image_ref` | **Required.** Live selfie path returned from upload or stored customer file ref. |
| `ekyc_document_ref` | Optional CCCD/portrait image for face compare. |
| `stt_audio_ref` | **Required.** Challenge audio path from upload or stored file ref. |
| `client_session` | Correlation ID passed to VNPT eKYC and SmartVoice STT endpoints. |

When a reference resolves to a local file, the backend uploads images via `POST /file-service/v1/addFile` and passes the returned `object.hash` to face APIs (not base64).

## Upload eKYC Images

`POST /api/shield/challenge/upload-ekyc` accepts multipart form data:

| Field | Required | Notes |
| --- | --- | --- |
| `selfie` | yes | Live face image (PNG/JPG/WEBP, max 8MB). |
| `document` | no | CCCD/portrait image for face compare. |

Saved files are stored under `uploads/ekyc/` and returned as refs such as `uploads/ekyc/selfie-<uuid>.jpg`.

## Upload SmartVoice Audio

`POST /api/shield/challenge/upload-audio` accepts multipart form data:

| Field | Required | Notes |
| --- | --- | --- |
| `challenge_audio` | yes | Short spoken confirmation (WAV/MP3/WEBM, max 16MB). |

Saved files are stored under `uploads/smartvoice/` and returned as refs such as `uploads/smartvoice/challenge-<uuid>.wav`.

The Shield demo UI uploads selfie and challenge audio in step 2 before calling `/api/shield/challenge`.

Smoke-test credentials and endpoints:

```bash
python3 scripts/smoke_vnpt_ekyc.py --selfie /path/to/selfie.jpg --document /path/to/cmnd.jpg
python3 scripts/smoke_vnpt_smartvoice.py --challenge-audio /path/to/challenge.wav
```

## Called VNPT Endpoints

Real mode targets the contracts in `docs/api_references/vnpt/endpoint_contracts.md`:

| Product | Endpoint | Request |
| --- | --- | --- |
| eKYC | `POST /file-service/v1/addFile` | Multipart `file`, `title`, `description`; response `object.hash` feeds face APIs. |
| eKYC | `POST /ai/v1/face/liveness` | JSON `img` (hash), `client_session`, `token`. |
| eKYC | `POST /ai/v1/face/mask` | JSON `img` (hash), `client_session`, `token`. |
| eKYC | `POST /ai/v1/face/compare` | JSON `img_front`, `img_face` (hashes), `client_session`, `token`. |
| SmartVoice | `POST /stt-service/v1/grpc/standard` | Multipart `audioFile`, `clientSession`, optional STT tuning fields. |

Challenge audio is also analyzed locally for voice stress (`voice_stress_score`, `voice_stress_labels`) using **emotion2vec+** (multilingual, suitable for Vietnamese) plus language-agnostic prosody rules. Configure via `VOICE_STRESS_*` in `.env`. Default locale is `vi` with higher prosody weight; set `VOICE_STRESS_BACKEND=wav2vec` only for English-centric experiments.

The adapter normalizes provider JSON into Shield fields including `ekyc_verification_status`, `ekyc_liveness_passed`, `ekyc_mask_detected`, `ekyc_face_match_score`, `ekyc_injection_risk_score`, `stt_transcript`, `stt_confidence`, `voice_stress_score`, and `voice_stress_labels`.

VNPT face liveness is treated as boolean. `object.liveness=false` fails the challenge.

VNPT eKYC error payloads (`statusCode` 400/408, `messageFields`, empty `object`) map to `ekyc_verification_status=failed` with provider notes in the Shield explanation list.
