# VNPT Provider Adapter

## Purpose

Shield Path B challenge calls real VNPT providers and local voice-stress analysis:

- **eKYC** — `VNPT_EKYC_MODE=real` + eKYC tokens (no offline mock path)
- **SmartVoice STT** — `VNPT_SMARTVOICE_MODE=real` + SmartVoice tokens (no offline mock path)
- **Smartbot** — `VNPT_SMARTBOT_MODE=real` + Smartbot tokens + `VNPT_SMARTBOT_BOT_ID` (no offline mock path)
- **SmartVision** — `VNPT_SMARTVISION_MODE=real` + SmartVision tokens on challenge selfie (no heuristic proxy)
- **Voice stress** — local emotion2vec + prosody on uploaded challenge audio

The normalized Shield schema stays the same regardless of provider configuration.

## Environment

Copy `.env.example` to `.env` and fill:

```bash
VNPT_EKYC_MODE=real
VNPT_SMARTVOICE_MODE=real
VNPT_SMARTBOT_MODE=real
VNPT_SMARTVISION_MODE=real
VNPT_BASE_URL=https://api.idg.vnpt.vn
VNPT_SMARTBOT_BASE_URL=https://assistant-stream.vnpt.vn
VNPT_EKYC_ACCESS_TOKEN=...
VNPT_SMARTVOICE_ACCESS_TOKEN=...
VNPT_SMARTBOT_ACCESS_TOKEN=...
VNPT_SMARTVISION_ACCESS_TOKEN=...
VNPT_SMARTBOT_BOT_ID=your-bot-id-from-smartbot-platform
VNPT_SMARTBOT_INPUT_CHANNEL=api
VNPT_MAC_ADDRESS=TEST1
```

Per-product credentials override the global fallback (`VNPT_ACCESS_TOKEN`, `VNPT_TOKEN_ID`, `VNPT_TOKEN_KEY`).

If a product is not configured, the challenge marks that step as failed/skipped with an explanation — there is no fixture fallback.

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

Both `ekyc_image_ref` and `stt_audio_ref` must come from the upload endpoints (or stored refs pointing at real files under `uploads/`).

## Upload endpoints

- `POST /api/shield/challenge/upload-ekyc` — selfie (+ optional CCCD)
- `POST /api/shield/challenge/upload-audio` — challenge voice clip (WAV/MP3/WEBM)

## Smoke tests

```bash
python3 scripts/smoke_vnpt_ekyc.py --selfie /path/to/selfie.jpg
python3 scripts/smoke_vnpt_smartvoice.py --challenge-audio uploads/smartvoice/challenge.wav
python3 scripts/smoke_vnpt_smartbot.py --text "Toi tu xac nhan giao dich"
python3 scripts/smoke_vnpt_smartvision.py --selfie uploads/ekyc/selfie.jpg
python3 scripts/smoke_voice_stress.py --audio uploads/smartvoice/challenge.wav
```

## Called endpoints

| Product | Endpoint |
| --- | --- |
| eKYC | `POST /file-service/v1/addFile`, `/ai/v1/face/liveness`, `/mask`, `/compare` |
| SmartVoice | `POST /stt-service/v1/grpc/standard` |
| Smartbot | `POST https://assistant-stream.vnpt.vn/v1/conversation` |
| SmartVision | `POST /aicommon-service/face-camera/v1/emotion` |
| Voice stress | Local analysis on `uploads/smartvoice/*` |

Smartbot should return JSON in `card_data[].text` when possible:

```json
{"safe": false, "scam_type": "fake_authority", "detected_patterns": ["secrecy_pressure"], "confidence": 0.91}
```

Voice stress uses `VOICE_STRESS_*` settings (emotion2vec + prosody, locale `vi` by default).
