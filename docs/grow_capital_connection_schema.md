# FIDES Grow Capital Connection Schema

## Decision

Grow should include a mocked capital-connection block that matches partner-bank loan offers, insurance offers, and Smartbot financial guidance.

This is a Grow derived-output schema update. It is not invoice input, not a tax workflow, and not a binding credit decision. It sits after cashflow forecast and alternative credit scoring, then turns those signals into partner-product recommendations.

For the 5-day MVP, the partner catalog is static and the ranking rules are deterministic. This gives the demo a clear path from business data to capital access without requiring live bank or insurer integrations.

## Payload Block

```json
{
  "capital_connection": {
    "status": "matched",
    "recommended_offer_id": "mock_wc_6000000_6mo",
    "partner_offers": [
      {
        "offer_id": "mock_wc_6000000_6mo",
        "partner_name": "Mock Partner Bank A",
        "product_type": "working_capital_loan",
        "max_amount": 6000000,
        "term_months": 6,
        "monthly_payment_estimate": 1060000,
        "premium_estimate": null,
        "eligibility_status": "eligible",
        "fit_score": 0.68,
        "required_documents": [
          "recent_invoices",
          "bank_statement_snapshot"
        ],
        "reason": "Small working-capital line can cover the projected starter cash-buffer gap.",
        "next_step": "request_partner_review"
      }
    ],
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

## Field Meaning

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | string | Match status such as `matched`, `needs_more_data`, or `not_matched`. |
| `recommended_offer_id` | string | Best offer ID selected by the mock ranking rule. |
| `partner_offers` | object array | Candidate loan or insurance offers from mock partners. |
| `smartbot_advice` | object | Smartbot message that explains the recommendation. |
| `data_sharing_scope` | string array | Data categories that would be shared with a partner after user consent. |
| `consent_required` | boolean | Whether partner sharing requires explicit consent. MVP sets this to `true`. |

Each `partner_offers` item contains:

- `offer_id`
- `partner_name`
- `product_type`: for MVP, `working_capital_loan` or `inventory_insurance`.
- `max_amount`
- `term_months`
- `monthly_payment_estimate`
- `premium_estimate`
- `eligibility_status`: `prequalified`, `eligible`, `needs_review`, or `ineligible`.
- `fit_score`
- `required_documents`
- `reason`
- `next_step`

## MVP Mock Rules

The synthetic generator uses a tiny static catalog:

- `Mock Partner Bank A`: working-capital loan.
- `Mock Insurance Partner B`: inventory insurance.

Ranking is simple:

- Low-risk, high-score Grow profiles can be `prequalified`.
- Emerging businesses can be `eligible` with partner review.
- Late-payment cases become `needs_review`.
- Forecasted shortfall or seasonal inventory drivers increase working-capital fit.
- Inventory or seasonal drivers increase insurance fit.

Smartbot turns the selected offer into a concise advisory message and repeats that the output is not a binding credit decision.

## Real-Life Capability

A production version would need:

- partner-bank and insurer product catalog APIs,
- pricing, eligibility, and affordability engines,
- customer consent before data sharing,
- KYC/KYB handoff and document collection,
- binding offer status from partner systems,
- quote expiry and versioning,
- adverse-action and fair-lending review where applicable,
- audit logs for recommendation inputs and Smartbot wording,
- financial-advice disclaimers and human escalation paths.

For the MVP, this block should be framed as a matched demo recommendation layer, not an approval or final quote.
