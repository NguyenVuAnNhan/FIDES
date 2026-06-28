# FIDES Grow Schema Explained

## Purpose

FIDES Grow is the MVP flow for helping a small business turn low-friction evidence into a trust profile, a credit-readiness score, and partner-capital recommendations.

The Grow schema is intentionally split into layers:

1. Minimal input capture.
2. Source extraction from OCR or voice.
3. Normalized ledger record.
4. Bookkeeping and compliance outputs.
5. Cashflow forecast and early warning.
6. Alternative credit profile.
7. Explainable credit model metadata.
8. Partner-bank and insurance matching.
9. Final Grow analysis response.

This separation matters. It lets the demo show a coherent journey from "take a photo of a receipt" or "speak a Vietnamese bookkeeping entry" to "explainable capital recommendation" without pretending every output is raw user input or a production banking decision.

## High-Level Flow

```text
invoice photo / voice entry / manual entry
  -> SmartReader OCR or SmartVoice parsing
  -> normalized_ledger_entry
  -> cashflow_summary
  -> cashflow_forecast
  -> tax_summary and einvoice_status
  -> alternative_credit_profile
  -> explainability
  -> capital_connection
  -> Grow score, credit band, recommendations, explanations
```

For the MVP, most derived fields are mocked deterministically. They are shaped like real service outputs so the frontend, backend, and demo dataset can evolve into real integrations later.

## Top-Level Request

The main request model is `GrowAnalyzeRequest`.

```json
{
  "business_id": "biz_an_nhien_coffee",
  "business_name": "An Nhien Coffee",
  "input_mode": "invoice_photo",
  "input_source": "/static/fixtures/receipts/grow-coffee-strong.png",
  "invoice_id": "INV-2026-001",
  "customer_name": "Office Pantry Co.",
  "invoice_total": 32000000,
  "paid_on_time": true,
  "items": [],
  "ocr": {},
  "voice_entry": {},
  "normalized_ledger_entry": {},
  "cashflow_summary": {},
  "cashflow_forecast": {},
  "tax_summary": {},
  "einvoice_status": {},
  "alternative_credit_profile": {},
  "capital_connection": {}
}
```

The flat fields `invoice_id`, `customer_name`, `invoice_total`, `paid_on_time`, and `items` are still the simplest score inputs. The richer nested objects explain where those values came from and what Grow can derive from them.

## Source Identity

```json
{
  "business_id": "biz_an_nhien_coffee",
  "business_name": "An Nhien Coffee",
  "input_mode": "invoice_photo",
  "input_source": "/static/fixtures/receipts/grow-coffee-strong.png"
}
```

`business_id` identifies the merchant or household business.

`business_name` is the display name.

`input_mode` tells Grow how the record was captured:

- `invoice_photo`: a receipt or invoice image processed by SmartReader OCR.
- `voice_entry`: a Vietnamese spoken bookkeeping entry processed by SmartVoice.
- `manual_entry`: direct form input, used as fallback.

`input_source` points to the source artifact. In the MVP it can be a local fixture path, mock URI, or audio ID. In production it would likely be an upload ID or object-storage URI.

## Invoice Items

```json
{
  "description": "Monthly coffee bean supply",
  "quantity": 1,
  "unit_price": 18000000,
  "amount": 18000000
}
```

`items` are line items from the invoice or receipt.

The Grow scorer currently gives a small boost when there are at least two line items, because structured detail makes revenue easier to validate and categorize. In real life, these items would also feed product category, tax category, margin estimate, seasonality, inventory exposure, and anomaly checks.

## SmartReader OCR

```json
{
  "ocr": {
    "provider": "SmartReader",
    "status": "completed",
    "confidence": 0.93,
    "extracted_fields": {
      "invoice_id": "INV-2026-001",
      "seller_name": "An Nhien Coffee",
      "buyer_name": "Office Pantry Co.",
      "issue_date": "2026-06-21",
      "due_date": "2026-06-28",
      "total_amount": 32000000,
      "tax_amount": 2909091,
      "currency": "VND",
      "line_items": []
    }
  }
}
```

The OCR block represents SmartReader output.

Important fields:

- `provider`: fixed to `SmartReader` in the MVP.
- `status`: `completed`, `not_used`, or a later failure/review state.
- `confidence`: extraction confidence from `0` to `1`.
- `extracted_fields`: structured invoice fields recovered from the image.

For MVP, OCR data is mocked and deterministic. The fake receipt PNGs under `frontend/static/fixtures/receipts/` support UI preview and demo flow, not model-training claims.

Real-life capability would require image upload, OCR job tracking, document-quality checks, invoice-layout handling, duplicate detection, tax-code extraction, and human review for low-confidence fields.

## SmartVoice Bookkeeping

```json
{
  "voice_entry": {
    "provider": "SmartVoice",
    "status": "completed",
    "audio_source": "mock://audio/grow-voice-001.wav",
    "transcript": "Hom nay ghi nhan doanh thu 2000000 dong...",
    "confidence": 0.91,
    "parsed_fields": {
      "transaction_type": "sale",
      "amount": 2000000,
      "description": "40 cups of coffee",
      "transaction_date": "2026-06-28",
      "category": "beverage_sales"
    }
  }
}
```

The voice block represents Vietnamese speech-to-text and parsing.

The MVP uses this to show minimal bookkeeping input: a merchant can speak a transaction instead of typing structured fields.

Real-life capability would require audio consent, recording/upload, Vietnamese STT, number normalization, transaction intent parsing, merchant-specific category mapping, and confirmation before the record becomes part of the ledger.

## Normalized Ledger Entry

```json
{
  "normalized_ledger_entry": {
    "entry_id": "ledger_inv_2026_001",
    "source_type": "invoice_photo",
    "transaction_type": "sale",
    "counterparty_name": "Office Pantry Co.",
    "amount": 32000000,
    "currency": "VND",
    "transaction_date": "2026-06-21",
    "category": "sales_revenue",
    "confidence": 0.93
  }
}
```

This is the stable bookkeeping object.

Everything downstream should be able to rely on this record more than on raw OCR or raw voice text. It says what happened in accounting terms: who paid whom, how much, when, in what category, and with what confidence.

In production, a ledger entry would need source links, edit history, reconciliation state, duplicate detection, and audit metadata.

## Cashflow Summary

```json
{
  "cashflow_summary": {
    "period": "2026-06",
    "total_inflow": 128000000,
    "total_outflow": 74240000,
    "net_cashflow": 53760000,
    "largest_customer": "Office Pantry Co.",
    "revenue_confidence": 0.93
  }
}
```

This block summarizes recent business cashflow.

In the MVP:

- `total_inflow` is roughly invoice total times four.
- `total_outflow` is a fixed mock expense ratio.
- `net_cashflow` is inflow minus outflow.
- `largest_customer` comes from the current invoice.
- `revenue_confidence` mirrors OCR or voice confidence.

This block is meant to support business understanding and credit-readiness context. It is not a bank-statement reconciliation engine yet.

## Cashflow Forecast

```json
{
  "cashflow_forecast": {
    "forecast_period_days": 30,
    "projected_inflow": 41250000,
    "projected_outflow": 36250000,
    "projected_net_cashflow": 5000000,
    "minimum_cash_buffer": 9375000,
    "liquidity_risk_level": "medium",
    "shortfall_amount": 4375000,
    "shortfall_expected_date": "2026-07-18",
    "recommended_borrowing_window": "2026-07-10_to_2026-07-17",
    "recommended_credit_amount": 6000000,
    "drivers": [
      "thin_recent_revenue",
      "starter_cash_buffer_gap",
      "limited_payment_history"
    ],
    "confidence": 0.64
  }
}
```

The forecast is forward-looking. It answers: will this business likely face a liquidity gap, and if so, when might working capital be useful?

Important fields:

- `forecast_period_days`: MVP uses a 30-day horizon.
- `projected_inflow` and `projected_outflow`: expected cash movement.
- `projected_net_cashflow`: can be negative.
- `minimum_cash_buffer`: mock safety buffer for operations.
- `liquidity_risk_level`: `low`, `medium`, `high`, or `unknown`.
- `shortfall_amount`: projected buffer gap.
- `recommended_borrowing_window`: timing suggestion, or `not_required`.
- `recommended_credit_amount`: mock amount to cover the gap.
- `drivers`: plain-language reasons.
- `confidence`: reliability of the forecast.

In production, this is financial-advice-adjacent. It would need transaction history, invoice due dates, actual settlement dates, recurring expenses, seasonality, affordability checks, and clear disclaimers.

## Tax Summary

```json
{
  "tax_summary": {
    "period": "2026-06",
    "vat_estimate": 11636364,
    "taxable_revenue": 128000000,
    "deductible_expenses": 40832000,
    "estimated_tax_due": 4358400,
    "filing_status": "draft_ready"
  }
}
```

This block supports automatic bookkeeping and compliance after the 2026 transition away from flat household-business tax assumptions.

For MVP, the formulas are simple:

- VAT is estimated from revenue.
- Deductible expenses use a mock ratio.
- Estimated tax due uses a mock percentage.
- `filing_status` is `draft_ready` or `needs_review`.

Production tax workflows would need up-to-date rules, business registration status, product/service tax categories, official filing periods, accountant review, and audit trails. Grow should produce draft reports, not silently file taxes.

## E-Invoice Status

```json
{
  "einvoice_status": {
    "provider": "mock_einvoice",
    "status": "draft_ready",
    "invoice_id": "INV-2026-001",
    "validation_errors": [],
    "compliance_notes": [
      "Required buyer and seller fields present",
      "VAT estimate generated",
      "Ledger entry linked to source document"
    ]
  }
}
```

This block shows where e-invoice workflow state would live.

For MVP:

- `provider` is `mock_einvoice`.
- clean records are `draft_ready`.
- late or incomplete records may be `needs_review`.
- `validation_errors` and `compliance_notes` are human-readable demo messages.

Production would require certified e-invoice provider integration, digital signing, invoice-number sequencing, tax-code validation, submission status, cancellation/adjustment workflows, and immutable audit logs.

## Alternative Credit Profile

```json
{
  "alternative_credit_profile": {
    "trust_graph_score": 0.88,
    "repeat_counterparty_count": 16,
    "verified_counterparty_count": 12,
    "network_centrality_score": 0.74,
    "cashflow_stability_score": 0.86,
    "vn_social_reputation_score": 0.81,
    "vn_social_mentions_30d": 54,
    "vn_social_sentiment": "positive",
    "vn_social_complaint_count_30d": 0,
    "alternative_credit_score": 88,
    "confidence": 0.82,
    "signals": [
      "repeat_buyer_relationships",
      "verified_supplier_network",
      "positive_social_reputation"
    ],
    "explainability": {}
  }
}
```

This is the main thin-file credit-intelligence block.

It combines:

- transaction graph evidence,
- repeat counterparties,
- verified counterparties,
- cashflow stability,
- vnSocial reputation,
- recent complaints,
- a combined alternative credit score.

The MVP scorer uses this profile as a small supporting signal:

- score at least `80` and at most one complaint: add `10`,
- score at least `65`: add `6`,
- score below `45` or at least four complaints: subtract `8`.

Invoice evidence still dominates the MVP score. The alternative profile should improve context, not override a bad payment record or missing revenue signal.

Real-life capability would require consent, entity resolution, transaction graph ingestion, social-data governance, bias monitoring, explainability, and review workflows before adverse decisions.

## Explainable Credit Model

```json
{
  "explainability": {
    "model_type": "gradient_boosted_trees",
    "model_version": "grow_alt_credit_mock_v1",
    "baseline_score": 55,
    "final_score": 88,
    "reason_codes": [
      "trust_graph_score",
      "repeat_counterparty_count",
      "paid_on_time"
    ],
    "feature_contributions": [
      {
        "feature": "trust_graph_score",
        "value": 0.88,
        "shap_value": 8.4,
        "direction": "positive",
        "reason": "A stronger transaction graph improves confidence in real business activity."
      }
    ]
  }
}
```

This block sits inside `alternative_credit_profile`.

It is the transparency layer for the alternative credit score. It lets the demo say: this score came from a gradient-boosted-tree-style model, and these features pushed the score up or down.

Important fields:

- `model_type`: fixed to `gradient_boosted_trees` in the MVP.
- `model_version`: audit/version identifier.
- `baseline_score`: starting score before contributions.
- `final_score`: score being explained.
- `reason_codes`: short top-factor labels.
- `feature_contributions`: SHAP-style feature contribution list.

For MVP, SHAP values are deterministic mock values. They are not produced by a trained model yet.

Production would require a real training pipeline, model registry, feature store, SHAP or equivalent explanation generation, monitoring, drift checks, and regulator-ready documentation.

## Capital Connection

```json
{
  "capital_connection": {
    "status": "matched",
    "recommended_offer_id": "mock_wc_6000000_6mo",
    "partner_offers": [],
    "smartbot_advice": {
      "provider": "Smartbot",
      "message": "A modest working-capital offer may help cover the projected cash-buffer gap.",
      "confidence": 0.66,
      "disclaimer": "Demo advisory output, not a binding credit decision."
    },
    "data_sharing_scope": [
      "business_profile",
      "cashflow_forecast",
      "recent_invoices"
    ],
    "consent_required": true
  }
}
```

This block turns Grow intelligence into mocked product recommendations.

It contains:

- partner-bank working-capital offers,
- insurance offers,
- product fit scores,
- eligibility labels,
- required documents,
- Smartbot advice,
- data-sharing scope,
- consent requirement.

For MVP, the catalog is static:

- `Mock Partner Bank A`: working-capital loan.
- `Mock Insurance Partner B`: inventory insurance.

Ranking is simple:

- strong, low-risk profiles can be `prequalified`,
- emerging profiles can be `eligible`,
- late-payment profiles become `needs_review`,
- forecast shortfalls raise working-capital fit,
- inventory or seasonal drivers raise insurance fit.

Production would need partner APIs, pricing engines, affordability checks, KYC/KYB handoff, quote expiry, consent, audit logs, adverse-action handling, and human escalation.

## Grow Analysis Response

```json
{
  "trust_score": 93,
  "credit_band": "strong",
  "monthly_revenue_estimate": 128000000,
  "loan_readiness": "ready_for_small_working_capital_offer",
  "recommended_action": "Prepare a small working-capital loan offer with invoice-backed limits.",
  "explanations": []
}
```

The response is what the UI displays after posting to `/api/grow/analyze-invoice`.

`trust_score` is capped from `0` to `100`.

`credit_band` is:

- `strong` for score at least `75`,
- `emerging` for score at least `55`,
- `thin_file` below that.

`monthly_revenue_estimate` is currently invoice total times four.

`loan_readiness` and `recommended_action` are simple labels based on the final score.

`explanations` are the user-facing reason list. They include both scoring reasons and zero-weight derived-output summaries, such as cashflow forecast, e-invoice status, explainable credit model, and partner capital connection.

## Current MVP Score Logic

The current score starts at `45`.

Positive rules:

- invoice total at least `20,000,000` VND: add `18`,
- paid on time: add `22`,
- at least two line items: add `8`,
- strong alternative credit profile: add up to `10`.

Negative rules:

- late payment: subtract `12`,
- weak alternative credit profile: subtract `8`.

The richer derived blocks are mostly explanatory today. That is intentional. The MVP should prove the workflow and data contract before pretending to run a production credit-risk model.

## Dataset Shape

The curated dataset has four Grow examples:

- strong coffee-shop profile,
- emerging food-stall profile,
- late-payment retailer,
- high-volume electronics reseller.

The synthetic dataset generator creates 500 Grow records by default when run with:

```bash
python3 scripts/generate_synthetic_dataset.py --seed 20260628 --count 1000
```

The generator uses a small set of category templates:

- `strong_business`,
- `emerging_thin_file`,
- `late_payment`,
- `seasonal_cashflow`,
- `high_volume`.

Each template fills in business names, invoice IDs, amounts, receipt/audio sources, cashflow forecasts, alternative credit profiles, explainability, and partner offers.

## What Is Mocked

For the hackathon MVP, these are mocked:

- OCR extraction,
- voice transcription and parsing,
- ledger normalization,
- cashflow summary,
- tax draft,
- e-invoice status,
- cashflow forecast,
- trust graph score,
- vnSocial reputation,
- gradient-boosting/SHAP outputs,
- partner-bank and insurance offers,
- Smartbot capital advice.

They are mocked in a consistent schema so the demo feels end-to-end and the code can later swap mock generators for real service adapters.

## What Needs Real Integrations Later

To move beyond MVP, Grow would need:

- SmartReader OCR adapter,
- SmartVoice STT and parsing adapter,
- persistent ledger database,
- bank transaction ingestion,
- e-invoice provider integration,
- tax-rule engine or accountant-reviewed workflow,
- graph database and graph feature service,
- vnSocial/reputation data integration,
- trained alternative-credit model,
- SHAP or equivalent explanation pipeline,
- partner-bank and insurer product APIs,
- consent and data-sharing controls,
- audit logs and model governance,
- human review for lending and adverse outcomes.

## Design Principle

The Grow schema should keep raw evidence, normalized facts, derived intelligence, and advisory outputs separate.

Raw input answers: what did the merchant provide?

Normalized ledger answers: what business event did we record?

Derived outputs answer: what can FIDES infer?

Advisory outputs answer: what should the merchant consider next?

Keeping those layers separate makes the MVP easier to explain, easier to demo, and much safer to evolve into a real financial product.
