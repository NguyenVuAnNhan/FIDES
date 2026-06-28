# FIDES Grow Input Schema

## Purpose

Grow accepts low-friction business input and turns it into structured bookkeeping data.

The MVP supports three input modes:

- `invoice_photo`: a receipt or invoice image processed by SmartReader OCR.
- `voice_entry`: a Vietnamese spoken bookkeeping entry processed by SmartVoice.
- `manual_entry`: direct form input, used as a fallback.

The current trust-score logic still uses the flat fields `invoice_id`, `customer_name`, `invoice_total`, `paid_on_time`, and `items`. The new input schema explains how those fields were obtained.

## Payload Blocks

### Source Fields

```json
{
  "business_id": "biz_an_nhien_coffee",
  "business_name": "An Nhien Coffee",
  "input_mode": "invoice_photo",
  "input_source": "/static/fixtures/receipts/grow-coffee-strong.png"
}
```

`input_source` can be a fixture path, upload ID, object-storage URI, or audio job ID.

### SmartReader OCR

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

For MVP, the OCR block is mocked but shaped like provider output.

### SmartVoice Bookkeeping

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

For `invoice_photo` cases, `voice_entry.status` is usually `not_used`.

### Normalized Ledger Entry

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

This is the stable bookkeeping object Grow should use for cashflow summaries, tax workflows, and alternative credit scoring.

### Derived Compliance Outputs

Grow also accepts mocked post-processing outputs:

- `cashflow_summary`
- `cashflow_forecast`
- `tax_summary`
- `einvoice_status`
- `alternative_credit_profile`

The compliance blocks model automatic bookkeeping, tax draft, and e-invoice workflow state after the normalized ledger entry exists. They are documented in `docs/grow_compliance_schema.md`.

The forecast block models liquidity early warning and suggested borrowing timing. It is documented in `docs/grow_cashflow_forecast_schema.md`.

The alternative credit block models derived trust graph and vnSocial reputation evidence. It is documented in `docs/grow_alternative_credit_schema.md`.

## Receipt Fixtures

Curated receipt images are generated from the Grow dataset by:

```bash
python3 scripts/generate_receipt_fixtures.py
```

The images are written to:

```text
frontend/static/fixtures/receipts/
```

These fixtures are synthetic and deterministic. They are intended for OCR demos and UI preview, not for model training claims.
