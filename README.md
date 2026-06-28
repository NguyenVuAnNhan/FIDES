# FIDES

FIDES is an AI platform for modern banking, with two MVP modules:

- **FIDES Shield**: a real-time manipulation circuit breaker for risky transfers.
- **FIDES Grow**: an invoice-to-trust-profile flow for small businesses.

This scaffold uses a FastAPI backend and a lightweight static frontend served by the same app.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000.

## API

- `GET /api/health`
- `GET /api/demo/dataset`
- `GET /api/demo/synthetic-dataset`
- `POST /api/shield/analyze`
- `POST /api/grow/analyze-invoice`

## Demo Dataset

Synthetic demo fixtures live in `backend/app/data/demo_dataset.json`.

The current dataset includes:

- Five Shield scenarios: fake police scam, OTP theft, guaranteed-investment scam, remote-control support scam, and a legitimate supplier payment.
- Four Grow invoice cases: strong coffee-shop profile, emerging food-stall profile, late-payment retailer, and high-volume electronics reseller.
- Shared trust profiles for the demo dashboard and future trust-graph work.

For a full explanation of the Shield scam schema and how the field families fit together, see `docs/scam_schema_explained.md`.

The Shield dataset includes MVP telecom-context fields: `active_call`, `caller_type`, `caller_number`, `recipient_known`, and `remote_control_detected`. The implementation decision and real-life capability limits are documented in `docs/telecom_context_mvp_decision.md`.

The Shield dataset also includes the mocked SmartVoice/Smartbot pipeline fields: `consent_granted`, `audio_source`, `stt_transcript`, `stt_confidence`, `detected_patterns`, `llm_scam_type`, and `llm_confidence`. It also includes derived coercion-signal fields: `voice_stress_score`, `face_emotion_score`, `scripted_behavior_score`, `coercion_score`, and their explanation labels/confidence values. The schema is documented in `docs/shield_audio_nlp_schema.md`.

Recipient-risk mock fields cover vnSocial reports, SIMO status, and graph-derived suspected mule-account features. The flat Shield payload schema is documented in `docs/shield_recipient_risk_schema.md`; the backend graph database design is documented in `docs/graph_database_schema.md`.

Native telemetry and eKYC mock fields cover liveness, mask/spoof checks, face comparison, biometric injection risk, SmartUX behavior anomaly, and remote-control-like signals supplied by the SDK consumer. This schema is documented in `docs/shield_native_telemetry_schema.md`.

Post-intervention learning is intentionally separate from the Shield transaction schema. Feedback events, anonymized outcome labels, and offline model/rule updates are documented in `docs/shield_feedback_learning_pipeline.md`.

Behavioral-science intervention is also separate from the Shield input schema. Assistant/TTS cool-down, reflection questions, trusted-contact confirmation, and intervention levels are documented in `docs/shield_intervention_orchestration.md`.

Grow input mocks cover invoice-photo OCR, Vietnamese voice bookkeeping, and normalized ledger entries. The schema and receipt fixture generation flow are documented in `docs/grow_input_schema.md`.

For bulk UI/dashboard testing, generate a deterministic madlib-style synthetic dataset:

```bash
python3 scripts/generate_synthetic_dataset.py --seed 20260628 --count 1000
```

By default this writes `backend/app/data/synthetic_demo_dataset.json` with 500 Shield records and 500 Grow records. The generator uses a few fixed formats per category, then fills in names, amounts, accounts, invoice IDs, and transcript details from seeded lists.

Generate curated fake receipt PNGs:

```bash
python3 scripts/generate_receipt_fixtures.py
```

## Next Build Steps

1. Add VNPT provider adapters behind the Shield and Grow services.
2. Keep keys in `.env`; never place them in frontend code.
3. Add file upload for scam audio and invoice images.
4. Add a shared trust profile/dashboard once both flows are stable.
