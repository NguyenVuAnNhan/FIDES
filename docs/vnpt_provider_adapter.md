# VNPT Provider Adapter

## Purpose

Shield Path B challenge calls real VNPT providers and local voice-stress analysis:

- **eKYC** — `VNPT_EKYC_MODE=real` + eKYC tokens (no offline mock path)
- **SmartVoice STT** — `VNPT_SMARTVOICE_MODE=real` + SmartVoice tokens (no offline mock path)
- **Smartbot** — `VNPT_SMARTBOT_MODE=real` + Smartbot tokens + `VNPT_SMARTBOT_BOT_ID` (no offline mock path)
- **SmartVision** — `VNPT_SMARTVISION_MODE=real` + SmartVision tokens; Hackathon flow `addFile` → `url-file` → `detect-face` on **multiple sampled live-check frames**
- **Voice stress** — local emotion2vec + prosody on challenge audio extracted from the live clip

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
  "ekyc_image_ref": "uploads/shield/frame-1-abc123.jpg",
  "ekyc_document_ref": "uploads/ekyc/document-def456.jpg",
  "stt_audio_ref": "uploads/smartvoice/live-audio-abc123.wav",
  "challenge_video_ref": "uploads/shield/live-check-abc123.webm",
  "challenge_frame_refs": [
    "uploads/shield/frame-0-abc123.jpg",
    "uploads/shield/frame-1-abc123.jpg",
    "uploads/shield/frame-2-abc123.jpg"
  ],
  "client_session": "shield-demo-browser-session"
}
```

`ekyc_image_ref` is the primary selfie frame (middle sample). SmartVision runs on all unique frame refs and aggregates the max visual distress score.

## Upload endpoints

### Preferred — live camera check

`POST /api/shield/challenge/upload-live-check` (multipart):

| Field | Required | Notes |
| --- | --- | --- |
| `challenge_video` | yes | WEBM/MP4/MOV from browser `MediaRecorder` (camera + mic) |
| `challenge_audio` | recommended | Audio-only WEBM from a parallel browser `MediaRecorder` (best STT quality) |
| `frame_0` … `frame_4` | recommended | JPEG samples from client-side canvas (3 typical) |
| `document` | no | CCCD portrait for face compare |

The server stores video under `uploads/shield/`, extracts an audio-only WEBM (or WAV fallback) for STT when `challenge_audio` is missing, and uses client frames or server `ffmpeg` frame extraction as fallback.

### Legacy fallback

- `POST /api/shield/challenge/upload-ekyc` — selfie + **required** CCCD portrait
- `POST /api/shield/challenge/upload-audio` — challenge voice clip (WAV/MP3/WEBM)

Live check uploads require a CCCD portrait for VNPT `/ai/v1/face/compare` (no skip-to-MATCH path).

## Smoke tests

```bash
python3 scripts/smoke_vnpt_ekyc.py --selfie /path/to/selfie.jpg
python3 scripts/smoke_vnpt_smartvoice.py --challenge-audio uploads/smartvoice/challenge.wav
python3 scripts/smoke_vnpt_smartbot.py --text "Toi tu xac nhan giao dich"
python3 scripts/smoke_vnpt_smartvision.py --selfie uploads/ekyc/selfie.jpg
python3 scripts/smoke_voice_stress.py --audio uploads/smartvoice/challenge.wav
python3 scripts/test_smartvision_parser.py
```

## Called endpoints

| Product | Endpoint |
| --- | --- |
| eKYC | `POST /file-service/v1/addFile`, `/ai/v1/face/liveness`, `/mask`, `/compare` |
| SmartVoice | `POST /stt-service/v1/grpc/standard` |
| Smartbot | `POST https://assistant-stream.vnpt.vn/v1/conversation` |
| SmartVision | `POST /file-service/v1/addFile`, `GET /proxy-service/url-file`, `POST /data-service/v1/smartvision/detect-face` (per frame) |
| Voice stress | Local analysis on extracted `uploads/smartvoice/*` |

Smartbot should return JSON in `card_data[].text` when possible:

```json
{"safe": false, "scam_type": "fake_authority", "detected_patterns": ["secrecy_pressure"], "confidence": 0.91}
```

SmartVision Hackathon flow for each sampled frame:

1. `POST /file-service/v1/addFile` (SmartVision token)
2. `GET /proxy-service/url-file?hash=...`
3. `POST /data-service/v1/smartvision/detect-face` with `{"data": "<signed-url>", "max_object": 1}`

Multi-frame results are fused with `aggregate_smartvision_frames()` (max distress score, merged labels). Shield maps `face_scores`, bbox count, and landmarks into `face_emotion_score` / `face_emotion_labels` (Hackathon doc has no separate emotion endpoint).

Voice stress uses `VOICE_STRESS_*` settings (emotion2vec + prosody, locale `vi` by default).

## Browser flow (Path B step 2)

1. User enables front camera + microphone.
2. App records ~10 seconds via `MediaRecorder`.
3. Browser samples 3 JPEG frames from the clip.
4. Upload hits `/api/shield/challenge/upload-live-check`.
5. `/api/shield/challenge` runs eKYC, SmartVision (multi-frame), SmartVoice STT, Smartbot, and local voice stress.
