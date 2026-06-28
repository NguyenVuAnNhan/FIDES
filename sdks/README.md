# FIDES SDK Scaffolds

This folder contains two MVP SDK scaffolds:

- `web`: browser/JavaScript SDK for web banking flows.
- `mobile`: native mobile SDK shape for Android and iOS banking apps.

The SDKs are intentionally thin. They collect or accept derived telemetry, build normalized FIDES payloads, and call the backend APIs:

- `POST /api/shield/analyze`
- `POST /api/grow/analyze-invoice`

They do not contain VNPT credentials, partner-bank credentials, or raw model logic. Provider calls and secrets stay server-side.

