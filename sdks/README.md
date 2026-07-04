# FIDES SDK Scaffolds

This folder contains two MVP SDK scaffolds:

- `web`: browser/JavaScript SDK for web banking flows.
- `mobile`: native mobile SDK shape for Android and iOS banking apps.

The SDKs are intentionally thin. They collect or accept derived telemetry, build normalized FIDES payloads, and call the backend APIs:

- `POST /api/shield/analyze`
- `POST /api/shield/challenge`
- `POST /api/grow/analyze-invoice`

`/api/shield/challenge` takes the original Shield transaction payload plus a demo `challenge_profile` such as `clear_user`, `coerced_authority`, `deepfake_injection`, or `scripted_remote_support`.

They do not contain VNPT credentials, partner-bank credentials, or raw model logic. Provider calls and secrets stay server-side.
