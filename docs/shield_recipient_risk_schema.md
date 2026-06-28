# FIDES Shield Recipient-Risk Schema

## Purpose

Recipient-risk fields mock the state that would normally come from three sources:

- `vnSocial`: public or social scam reports related to an account or phone number.
- `SIMO`: official or interbank suspicious-account status.
- FIDES graph intelligence: bank-side transaction graph features that suggest a suspected mule account.

For the MVP, these are flat fields inside each Shield payload so the demo can run without a live graph database or official SIMO access.

## Shield Payload Fields

| Field | Type | Source in MVP | Meaning |
| --- | --- | --- | --- |
| `recipient_phone` | string | Dataset/form | Phone number associated with the recipient, when known. |
| `vn_social_report_count` | integer | Mock vnSocial lookup | Number of recent scam reports tied to recipient account or phone. |
| `vn_social_recent_keywords` | string array | Mock vnSocial lookup | Trending report keywords, such as `cong an`, `otp`, or `ho tro tu xa`. |
| `simo_status` | string | Mock SIMO lookup | One of `not_checked`, `not_listed`, `watchlisted`, or `listed`. |
| `simo_last_checked_at` | string or null | Mock SIMO lookup | Timestamp for the last official/interbank lookup. |
| `graph_risk_score` | number or null | Mock graph service output | Mule-account risk score from `0.0` to `1.0`. |
| `graph_pattern` | string or null | Mock graph service output | Dominant pattern, such as `fan_in_fan_out`, `rapid_pass_through`, `fan_in`, or `new_account_high_activity`. |
| `inbound_sender_count_10m` | integer | Mock graph feature | Count of distinct inbound senders in the last 10 minutes. |
| `outbound_account_count_10m` | integer | Mock graph feature | Count of distinct onward recipient accounts in the last 10 minutes. |
| `median_pass_through_minutes` | number or null | Mock graph feature | Median time between receiving funds and sending them onward. |
| `account_age_days` | integer or null | Mock account metadata | Age of the recipient account. |
| `shared_device_cluster_size` | integer | Mock graph feature | Number of accounts linked by shared device or phone signals. |
| `funds_moved_within_minutes` | boolean | Mock graph feature | Whether funds are typically moved onward soon after receipt. |
| `recipient_risk_level` | string | Mock graph service output | One of `unknown`, `low`, `elevated`, or `critical`. |

## Backend Behavior

Shield currently adds explainable risk weight for:

1. vnSocial reports.
2. SIMO `watchlisted` or `listed` status.
3. Graph risk score and graph-pattern features.

The backend wording should describe these as suspected mule-account or recipient-risk signals, not proof of fraud.

## Real-Life Mapping

In production:

- vnSocial fields would come from a report/reputation service.
- SIMO fields would come from an official or bank-consortium integration.
- Graph fields would come from FIDES-owned transaction graph queries or a graph ML service.
- `graph_risk_score` can start as a rule-based score and later be replaced by a GNN or graph anomaly model.
- Decisions should trigger friction, review, or trusted-contact confirmation rather than directly accusing the recipient.

