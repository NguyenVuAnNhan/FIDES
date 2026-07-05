# FIDES

FIDES is an AI platform for modern banking, with two MVP modules:

- **FIDES Shield**: a real-time manipulation circuit breaker for risky transfers.
- **FIDES Grow**: an invoice-to-trust-profile flow for small businesses.

This scaffold uses a FastAPI backend and a lightweight static frontend served by the same app.

## Run Locally

One-command setup and run (recommended):

```bash
./scripts/bootstrap.sh
```

Setup only (no server):

```bash
./scripts/bootstrap.sh --no-run
```

Manual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_receipt_fixtures.py
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000 (redirects to Grow).

### Grow OCR (PaddleOCR)

Grow receipt OCR uses **PaddleOCR** on the synthetic PNGs under `frontend/static/fixtures/receipts/`.

Use the project virtualenv (recommended; avoids system NumPy conflicts):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Parser unit tests (no Paddle model download)
python scripts/test_receipt_parser.py

# PaddleOcrProvider on all receipt fixtures (first run may download models)
python scripts/smoke_paddle_ocr.py
```


If `paddlepaddle` fails to install on your platform, check the [PaddlePaddle install guide](https://www.paddlepaddle.org.cn/install/quick) for the correct wheel, then `pip install paddleocr`.

## API

- `GET /api/health`
- `GET /api/demo/dataset`
- `GET /api/demo/synthetic-dataset`
- `POST /api/shield/analyze`
- `POST /api/shield/challenge`
- `POST /api/shield/challenge/upload-live-check` — live camera clip + sampled frames (Path B)
- `POST /api/shield/challenge/upload-ekyc` — legacy selfie upload
- `POST /api/shield/challenge/upload-audio` — legacy audio upload
- `POST /api/grow/upload-receipt` — upload PNG/JPG/WEBP receipt; returns `input_source`
- `POST /api/grow/process-invoice` — minimal input; runs PaddleOCR on receipt PNG then credit pipeline
- `POST /api/grow/analyze-invoice` — full payload scoring (compat)

## SDK Scaffolds

- Web SDK scaffold: `sdks/web`
- Mobile SDK scaffold: `sdks/mobile`

The SDK design and platform boundaries are documented in `docs/sdk_scaffold.md`.

## Demo Dataset

Synthetic demo fixtures live in `backend/app/data/demo_dataset.json`.

The current dataset includes:

- Six Shield scenarios: fake police scam, stage-one challenge required, OTP theft, guaranteed-investment scam, remote-control support scam, and a legitimate supplier payment.
- Four Grow invoice cases: strong coffee-shop profile, emerging food-stall profile, late-payment retailer, and high-volume electronics reseller.
- Shared trust profiles for the demo dashboard and future trust-graph work.

The full mock data and future database inventory is tracked in `docs/mock_data_inventory.md`. VNPT API contract alignment and recommended schema updates are documented in `docs/vnpt_schema_integration_plan.md`.

Shield Path B challenge uses real VNPT eKYC, SmartVoice STT, Smartbot, and SmartVision APIs (when configured in `.env`), plus local voice-stress analysis on challenge audio. Step 2 records a **live camera + microphone clip** (~4s); the browser samples JPEG frames and the backend runs eKYC/SmartVision on those frames and STT on extracted audio. Upload via `POST /api/shield/challenge/upload-live-check` (preferred) or legacy selfie/audio upload endpoints. See `docs/vnpt_provider_adapter.md`.

There is no offline mock fallback for eKYC, STT, or Smartbot. If credentials are missing, the challenge marks that step as failed/skipped with an explanation. See `docs/vnpt_provider_adapter.md` for the operator checklist.

For a full explanation of the Shield scam schema and two-stage circuit-breaker flow, see `docs/scam_schema_explained.md`.

The Shield dataset includes MVP telecom-context fields: `active_call`, `caller_type`, `caller_number`, `recipient_known`, and `remote_control_detected`. The implementation decision and real-life capability limits are documented in `docs/telecom_context_mvp_decision.md`.

The Shield dataset also includes the SmartVoice/Smartbot pipeline fields: `consent_granted`, `audio_source`, `stt_transcript`, `stt_confidence`, `detected_patterns`, `llm_scam_type`, and `llm_confidence`. It also includes derived coercion-signal fields: `voice_stress_score`, `face_emotion_score`, `scripted_behavior_score`, `coercion_score`, and their explanation labels/confidence values. The schema is documented in `docs/shield_audio_nlp_schema.md`.

Recipient-risk mock fields cover vnSocial reports, SIMO status, and graph-derived suspected mule-account features. The flat Shield payload schema is documented in `docs/shield_recipient_risk_schema.md`; the backend graph database design is documented in `docs/graph_database_schema.md`.

Native telemetry and eKYC mock fields cover liveness, mask/spoof checks, face comparison, biometric injection risk, SmartUX behavior anomaly, and remote-control-like signals supplied by the SDK consumer. This schema is documented in `docs/shield_native_telemetry_schema.md`.

Post-intervention learning is intentionally separate from the Shield transaction schema. Feedback events, anonymized outcome labels, and offline model/rule updates are documented in `docs/shield_feedback_learning_pipeline.md`.

Behavioral-science intervention is also separate from the Shield input schema. Assistant/TTS cool-down, reflection questions, trusted-contact confirmation, and intervention levels are documented in `docs/shield_intervention_orchestration.md`.

For a full explanation of the Grow schema and how input, bookkeeping, forecast, alternative-credit, and capital-connection blocks fit together, see `docs/grow_schema_explained.md`.

Grow input mocks cover invoice-photo OCR, Vietnamese voice bookkeeping, and normalized ledger entries. The schema and receipt fixture generation flow are documented in `docs/grow_input_schema.md`.

Grow compliance mocks cover derived cashflow, tax-draft, and e-invoice workflow state. The MVP decision, mock formulas, and real-life integration limits are documented in `docs/grow_compliance_schema.md`.

Grow cashflow forecast mocks cover liquidity early warning, projected shortfalls, and suggested borrowing windows. The schema and real-life capability boundaries are documented in `docs/grow_cashflow_forecast_schema.md`.

Grow alternative-credit mocks combine trust graph evidence and vnSocial reputation into a derived profile, including gradient-boosted-tree and SHAP-style explainability metadata. The schema, mock rules, and real-life capability boundaries are documented in `docs/grow_alternative_credit_schema.md`.

Grow capital-connection mocks match partner-bank loan offers, insurance offers, and Smartbot advisory text. The schema and real-life integration boundaries are documented in `docs/grow_capital_connection_schema.md`.

For bulk UI/dashboard testing, generate a deterministic madlib-style synthetic dataset:

```bash
python3 scripts/generate_synthetic_dataset.py --seed 20260628 --count 1000
```

By default this writes `backend/app/data/synthetic_demo_dataset.json` with 500 Shield records and 500 Grow records. The generator uses a few fixed formats per category, then fills in names, amounts, accounts, invoice IDs, and transcript details from seeded lists.

Generate curated fake receipt PNGs:

```bash
python3 scripts/generate_receipt_fixtures.py
```

Files are written to `frontend/static/fixtures/receipts/` for upload/OCR testing.

## Grow OCR flow

`POST /api/grow/process-invoice` no longer loads curated demo JSON for scoring inputs.

1. Resolve `input_source` under allowed receipt paths (path-safe).
2. Run **PaddleOCR** on the PNG.
3. Parse fields (`seller`, `buyer`, `invoice_id`, `total`, line items).
4. Normalize a ledger entry from OCR output.
5. Score with **LightGBM** and return `{ request, analysis }` for the Grow wizard.

Form fields `business_id` and `paid_on_time` still come from the UI; invoice identity and amounts come from OCR.

## Grow ML credit scoring

Grow uses a **LightGBM** model trained on synthetic invoice features with rule-based labels.

Features (7):

- `paid_on_time`, `invoice_total`, `log_invoice_total`, `item_count`, `avg_line_amount`, `tax_ratio`, `ocr_confidence`

Train or retrain:

```bash
source .venv/bin/activate
python scripts/train_grow_credit_model.py
python scripts/smoke_grow_ml.py
```

Model artifacts: `backend/app/data/models/grow_credit_lgb.txt` and `grow_credit_model_meta.json`.

The live Grow pipeline: **PaddleOCR → ledger → Neo4j trust graph → LightGBM + SHAP**. Mock vnSocial, cashflow, tax, e-invoice, and partner capital blocks were removed from the pipeline and wizard.

Trust graph design: [`docs/grow_trust_graph_neo4j_plan.md`](docs/grow_trust_graph_neo4j_plan.md).

### Neo4j (trust graph)

```bash
docker compose up neo4j -d
# Browser: http://localhost:7474 (neo4j / fides-dev-password)

# Enable in .env:
# NEO4J_ENABLED=true

python scripts/init_neo4j_schema.py
python scripts/seed_grow_graph.py
python scripts/train_grow_credit_model.py   # v2 model with 11 features
python scripts/smoke_grow_graph.py
```

Demo business IDs (seeded graph history): `biz_an_nhien_coffee`, `biz_bep_nha_linh`, `biz_thanh_tam_mini_mart`, `biz_nam_phuong_devices`.

## Next Build Steps

1. Expand the VNPT adapter pattern to Grow SmartReader OCR and SmartVoice bookkeeping.
2. Keep keys in `.env`; never place them in frontend code.
3. Add file upload for scam audio and invoice images.
4. Add a shared trust profile/dashboard once both flows are stable.
