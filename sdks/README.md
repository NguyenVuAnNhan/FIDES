# FIDES SDK Scaffolds

This folder contains two MVP SDK scaffolds:

- `web`: browser/JavaScript SDK for web banking flows.
- `mobile`: native mobile SDK for Android and iOS banking apps.

The SDKs are intentionally thin. They collect or accept derived telemetry, build normalized FIDES payloads, and call the backend APIs:

- `POST /api/shield/analyze`
- `POST /api/shield/challenge/upload-live-check` (multipart — preferred for Path B)
- `POST /api/shield/challenge`

Path B flow:

1. `analyzeShield()` — stage 1 transfer context scoring.
2. `uploadLiveCheck()` + `challengeShield()` — or `runIdentityCheck()` for both steps.

They do not contain VNPT credentials, partner-bank credentials, or raw model logic. Provider calls and secrets stay server-side.

## Android Phase 1 (implemented)

- `ShieldPayloadBuilder` — Path B defaults aligned with web demo
- Typed `ShieldAnalyzeResponse`
- Multipart live-check upload
- `OkHttpFidesTransport` reference client

## Android Phase 2 (implemented)

- `AndroidCallStateMonitor` + `analyzeShieldWithCall()`
- `LiveCheckCapture` (CameraX, 10s, JPEG frame sampling)
- `LiveCheckCaptureResult.toUploadInput()`

See `mobile/README.md` for the full Android integration flow.
