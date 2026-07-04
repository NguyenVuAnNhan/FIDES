# FIDES SDK Scaffolds

This folder contains two MVP SDK scaffolds:

- `web`: browser/JavaScript SDK for web banking flows.
- `mobile`: native mobile SDK shape for Android and iOS banking apps.

The SDKs are intentionally thin. They collect or accept derived telemetry, build normalized FIDES payloads, and call the backend APIs:

- `POST /api/shield/analyze`
- `POST /api/shield/challenge`
- `POST /api/grow/analyze-invoice`

`/api/shield/challenge` takes the original Shield transaction payload plus mock artifact references. In the MVP, `mock_payload/ekyc_img_1` passes eKYC, `mock_payload/ekyc_img_2` fails eKYC, `mock_payload/stt_audio_1` passes the spoken challenge, and `mock_payload/stt_audio_2` fails it.

They do not contain VNPT credentials, partner-bank credentials, or raw model logic. Provider calls and secrets stay server-side.
