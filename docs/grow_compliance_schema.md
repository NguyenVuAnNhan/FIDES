# FIDES Grow Compliance Schema

## Decision

Automatic bookkeeping, cashflow summaries, tax drafts, and e-invoice state should be represented in the Grow schema.

This is a schema update because these outputs have their own lifecycle after the minimal input step. OCR or voice input creates a normalized ledger entry; bookkeeping and compliance automation then derives cashflow, tax, and e-invoice artifacts from that ledger data.

For the 5-day MVP, these fields are mocked and deterministic. They are useful for a demo and for UI wiring, but they are not legal tax advice or a production e-invoice integration.

## Added Payload Blocks

### Cashflow Summary

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

This is the business-facing bookkeeping view. It answers whether the merchant has enough recent inflow and margin signal to support a Grow recommendation.

MVP implementation:

- `total_inflow` is approximated as the demo invoice total times four.
- `total_outflow` is a fixed mock expense ratio.
- `net_cashflow` is calculated from those values.
- `revenue_confidence` mirrors OCR or voice parsing confidence.

Real-life capability:

- Derive cashflow from invoices, receipts, bank transactions, payment confirmations, refunds, and manual ledger adjustments.
- Reconcile invoice issue dates, due dates, actual payment dates, and bank settlement events.
- Preserve source links and confidence per entry so a user or reviewer can trace every number back to evidence.

### Tax Summary

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

This block supports the demo claim that Grow can reduce bookkeeping and compliance burden after the 2026 transition away from flat household-business tax assumptions.

MVP implementation:

- VAT, deductible expenses, and estimated tax due use simple deterministic formulas.
- `filing_status` is `draft_ready` for clean examples and `needs_review` when the mock data has an issue such as late payment.

Real-life capability:

- Needs up-to-date tax rules, business type, registration status, product/service tax categories, deductible-expense rules, and official filing periods.
- Should produce a draft report with explainable calculations, not silently file taxes.
- Should include accountant review, user confirmation, audit logs, and jurisdiction-specific validation before any production submission.

### E-Invoice Status

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

This block makes e-invoice automation visible in the demo without pretending that the backend is connected to a live tax-authority system.

MVP implementation:

- The provider is `mock_einvoice`.
- Clean invoices become `draft_ready`.
- Late or incomplete cases can become `needs_review` with validation errors.

Real-life capability:

- Requires integration with certified e-invoice providers or official tax infrastructure.
- Needs digital signing, invoice-number sequencing, buyer/seller validation, tax-code validation, submission status, cancellation/adjustment handling, and immutable audit trails.
- Should store provider request IDs and response statuses separately from the Grow scoring result.

## What This Does Not Change

The current Grow trust score still relies on the existing flat fields:

- `invoice_total`
- `paid_on_time`
- `items`

The new compliance blocks are explanatory demo outputs. Later, they can feed richer scoring once there is real transaction history and validation evidence.
