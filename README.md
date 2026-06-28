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

- Four Shield scenarios: fake police scam, OTP theft, guaranteed-investment scam, and a legitimate supplier payment.
- Four Grow invoice cases: strong coffee-shop profile, emerging food-stall profile, late-payment retailer, and high-volume electronics reseller.
- Shared trust profiles for the demo dashboard and future trust-graph work.

For bulk UI/dashboard testing, generate a deterministic madlib-style synthetic dataset:

```bash
python3 scripts/generate_synthetic_dataset.py --seed 20260628 --count 1000
```

By default this writes `backend/app/data/synthetic_demo_dataset.json` with 500 Shield records and 500 Grow records. The generator uses a few fixed formats per category, then fills in names, amounts, accounts, invoice IDs, and transcript details from seeded lists.

## Next Build Steps

1. Add VNPT provider adapters behind the Shield and Grow services.
2. Keep keys in `.env`; never place them in frontend code.
3. Add file upload for scam audio and invoice images.
4. Add a shared trust profile/dashboard once both flows are stable.
