# FIDES Shield Telecom Context Decision

## MVP Decision

For the hackathon MVP, telecom context is represented as explicit request fields and synthetic dataset fields. This lets the demo prove the product logic without depending on native mobile permissions or a live telco integration.

Implemented Shield fields:

- `transaction_amount`: used to trigger extra Shield analysis for high-value transfers.
- `active_call`: whether the user is on a call during the transfer.
- `caller_type`: one of `trusted`, `unknown`, `voip`, or `international`.
- `caller_number`: used for simple country-code and suspicious-prefix checks.
- `recipient_known`: whether the recipient appears in trusted payees, recent invoices, or known supplier history.
- `remote_control_detected`: whether a remote-support or screen-control signal is present.
- `native_telemetry_available`: whether the integrating SDK consumer supplied native telemetry.

The current MVP treats these as explainable risk signals. They are not claims that a browser can directly observe phone-call or installed-app state.

## Easy MVP Features

| Feature | MVP implementation | Why it is easy |
| --- | --- | --- |
| High-value transfer trigger | Backend threshold rule on `transaction_amount` | Bank/payment apps already know transfer amount before approval. |
| Active call flag | Boolean `active_call` in the dataset/request | Good enough for demo flows and mobile SDK simulation. |
| Caller type flag | Enum `caller_type` | Can be mocked now and replaced by telco/mobile metadata later. |
| Phone prefix check | Rule over `caller_number` | Simple deterministic logic, easy to explain. |
| Known-recipient check | Boolean `recipient_known` | Server-side history lookup can support this in production. |
| Remote-control signal | Boolean `remote_control_detected` | Demonstrates the risk model before native detection exists. |
| Risk explanation | Per-signal explanation rows | Critical for trust, judge clarity, and future compliance. |

## Real-Life Capability

### Bank Backend

The bank backend can reliably know:

- Transaction amount.
- Recipient account.
- Whether the recipient is known, new, trusted, or recently added.
- User transaction history and normal transfer patterns.
- Whether this transaction is unusual for this customer.

These are production-feasible without special mobile permissions.

### Android App or SDK

Android can support more context, but it depends on permissions, OS version, and whether FIDES is embedded in the banking app:

- Active-call state may be available through phone-state permissions or telecom APIs, but modern Android restricts call-log and number access.
- Incoming caller number may be available only with sensitive permissions, default-dialer/call-screening roles, or telco cooperation.
- Known remote-control apps can sometimes be detected through package visibility rules if the app declares the relevant package queries.
- Accessibility, overlay, screen-sharing, and remote-control indicators are possible heuristics, but they are OS-limited and privacy-sensitive.

For MVP and pilot language, describe this as `mobile telemetry with explicit consent`, not guaranteed universal device visibility.

In the SDK/API product model, native telemetry collection belongs to the integrating bank or wallet app. FIDES defines the telemetry contract and risk-fusion logic; the SDK consumer supplies derived signals where legally and technically available.

### iOS App

iOS is much more restricted:

- Third-party banking apps generally cannot inspect call state, call numbers, installed apps, or remote-control tools.
- iOS implementation should rely more heavily on bank-side history, user confirmation, telco metadata, and in-app behavioral signals.

### Web App

A normal web app cannot reliably detect:

- Whether the user is on a phone call.
- Caller number or caller type.
- Installed remote-control apps.
- Screen-sharing or device-control tools outside the browser.

For web demos, these fields must remain mocked or supplied by the scenario dataset.

### Telco Integration

A telco or telco-backed API can make the strongest version possible:

- Whether a call is active while the transfer is initiated.
- Whether the caller is international, VoIP-like, hidden, spoofed, or recently suspicious.
- Prefix and reputation signals.
- Cross-user scam reports and velocity signals.

This is the long-term reason FIDES is stronger with telecom-bank collaboration.

## Privacy and Compliance Position

The production design should use explicit consent, data minimization, and purpose limitation:

- Process only the signals needed for transfer-risk decisions.
- Prefer derived features over raw call contents or raw numbers where possible.
- Keep risky actions explainable.
- Do not let the LLM independently block money movement.
- Maintain a clear appeal or continue-flow path for false positives.
