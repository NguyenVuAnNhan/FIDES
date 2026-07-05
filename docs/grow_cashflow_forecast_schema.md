# FIDES Grow Cashflow Forecast Schema

## Decision

Grow should include a mocked cashflow forecast block for liquidity early warning and suggested borrowing timing.

This is a Grow derived-output schema update. It is not raw invoice input and it is not tax/e-invoice compliance. It sits after normalized ledger and cashflow summary data, then projects whether the business may face a cash-buffer gap soon.

For the 5-day MVP, this is deterministic mock data. It lets the demo show a useful advisory workflow without claiming that FIDES has a production forecasting model or regulated lending-advice engine.

## Payload Block

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

## Field Meaning

| Field | Type | Meaning |
| --- | --- | --- |
| `forecast_period_days` | integer | Forecast horizon. MVP uses 30 days. |
| `projected_inflow` | integer VND | Expected incoming cash during the horizon. |
| `projected_outflow` | integer VND | Expected outgoing cash during the horizon. |
| `projected_net_cashflow` | integer VND | `projected_inflow - projected_outflow`. Can be negative. |
| `minimum_cash_buffer` | integer VND | Mock safety buffer needed for normal operations. |
| `liquidity_risk_level` | string | `low`, `medium`, `high`, or `unknown`. |
| `shortfall_amount` | integer VND | Gap between projected net cashflow and the required buffer. |
| `shortfall_expected_date` | string or null | Mock date when the gap is expected. |
| `recommended_borrowing_window` | string | Suggested timing window, or `not_required`. |
| `recommended_credit_amount` | integer VND | Mock working-capital amount to cover the shortfall plus buffer. |
| `drivers` | string array | Explanation labels for the forecast. |
| `confidence` | number from 0 to 1 | Confidence in the forecast. |

## MVP Mock Rules

The synthetic generator uses category-based patterns:

- `strong_business`: low risk, stable inflow, no borrowing required.
- `emerging_thin_file`: medium risk, thin buffer, small working-capital suggestion.
- `late_payment`: high risk, delayed receivable, larger shortfall warning.
- `seasonal_cashflow`: medium or high risk from inventory timing gaps.
- `high_volume`: low risk but working-capital ready.

The frontend builds the same style of mock forecast from the invoice total and payment status.

## Real-Life Capability

A production forecast would need:

- historical bank transactions and invoices,
- invoice due dates and actual settlement dates,
- recurring rent, payroll, supplier, inventory, and tax obligations,
- seasonality and event-calendar effects,
- delayed-payment probabilities by counterparty,
- loan affordability checks and repayment stress tests,
- explainability and audit logs for forecast drivers,
- clear consent and disclaimers because borrowing recommendations are financial-advice-adjacent.

For the MVP, this block should be presented as an early-warning assistant, not as an automated lending decision.
