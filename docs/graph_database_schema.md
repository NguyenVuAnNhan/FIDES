# FIDES Backend Graph Database Schema

## Purpose

The graph database models bank-side relationships between users, accounts, devices, phones, transactions, reports, and official watchlist state. Its first MVP job is to produce recipient-risk features for Shield, especially suspected mule-account behavior.

Recommended database: Neo4j or another property graph store. The schema below is implementation-oriented but still lightweight enough for the hackathon backend.

## Node Labels

### `User`

Represents an authenticated banking customer.

Properties:

- `user_id`: stable internal ID.
- `customer_segment`: retail, SME, household_business.
- `created_at`: ISO timestamp.
- `risk_segment`: low, elevated, high.

### `Account`

Represents a bank account or wallet account.

Properties:

- `account_id`: stable internal ID.
- `account_number_hash`: salted hash of the account number.
- `bank_code`: issuing bank or wallet code.
- `account_type`: personal, business, wallet, external.
- `created_at`: ISO timestamp.
- `status`: active, frozen, closed.
- `known_good`: boolean trusted-recipient hint.

### `Phone`

Represents a phone number linked to a user, recipient, or report.

Properties:

- `phone_hash`: salted hash of the phone number.
- `country_code`: normalized country code.
- `carrier_type`: mobile, voip, fixed, unknown.
- `first_seen_at`: ISO timestamp.

### `Device`

Represents a mobile device or browser/device fingerprint.

Properties:

- `device_id`: stable internal ID or hash.
- `platform`: android, ios, web, unknown.
- `first_seen_at`: ISO timestamp.
- `risk_tags`: list of derived tags.

### `Transaction`

Represents a transfer attempt or completed transfer.

Properties:

- `transaction_id`: stable internal ID.
- `amount`: integer VND amount.
- `currency`: VND.
- `created_at`: ISO timestamp.
- `status`: initiated, paused, completed, reversed, failed.
- `channel`: mobile, web, branch, api.

### `ScamReport`

Represents a report from vnSocial, customer support, or internal investigation.

Properties:

- `report_id`: stable internal ID.
- `source`: vn_social, customer_support, internal_case, partner_bank.
- `keywords`: list of report keywords.
- `created_at`: ISO timestamp.
- `confidence`: number from 0.0 to 1.0.

### `OfficialWatchStatus`

Represents SIMO/NHNN or partner-bank status at a point in time.

Properties:

- `status_id`: stable internal ID.
- `source`: simo, nhnn, partner_bank.
- `status`: not_listed, watchlisted, listed.
- `checked_at`: ISO timestamp.

## Relationships

| Relationship | From | To | Meaning |
| --- | --- | --- | --- |
| `OWNS` | `User` | `Account` | User owns or controls an account. |
| `USES_DEVICE` | `User` | `Device` | User has used this device. |
| `LINKED_PHONE` | `User` or `Account` | `Phone` | Phone is associated with the user or account. |
| `SENT` | `Account` | `Transaction` | Source account initiated a transaction. |
| `RECEIVED` | `Transaction` | `Account` | Destination account received funds. |
| `USED_DEVICE` | `Transaction` | `Device` | Device used for a transfer. |
| `REPORTED` | `ScamReport` | `Account` or `Phone` | Report references this account or phone. |
| `HAS_WATCH_STATUS` | `Account` | `OfficialWatchStatus` | Official watchlist state for an account. |
| `TRUSTED_PAYEE` | `User` | `Account` | User has an established trusted-recipient history. |

## Indexes And Constraints

Neo4j-style examples:

```cypher
CREATE CONSTRAINT user_id IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT account_id IF NOT EXISTS
FOR (a:Account) REQUIRE a.account_id IS UNIQUE;

CREATE INDEX account_number_hash IF NOT EXISTS
FOR (a:Account) ON (a.account_number_hash);

CREATE CONSTRAINT transaction_id IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE;

CREATE INDEX transaction_created_at IF NOT EXISTS
FOR (t:Transaction) ON (t.created_at);

CREATE INDEX phone_hash IF NOT EXISTS
FOR (p:Phone) ON (p.phone_hash);

CREATE INDEX device_id IF NOT EXISTS
FOR (d:Device) ON (d.device_id);
```

## Derived Features For Shield

The graph service should expose a compact recipient-intelligence response:

```json
{
  "graph_risk_score": 0.88,
  "graph_pattern": "fan_in_fan_out",
  "inbound_sender_count_10m": 14,
  "outbound_account_count_10m": 9,
  "median_pass_through_minutes": 3.0,
  "account_age_days": 4,
  "shared_device_cluster_size": 6,
  "funds_moved_within_minutes": true,
  "recipient_risk_level": "critical"
}
```

MVP rules for suspected mule behavior:

- Fan-in: many unrelated accounts send to one recipient in a short window.
- Fan-out: the recipient quickly sends onward to several other accounts.
- Rapid pass-through: received funds leave within minutes.
- New account with high activity: low account age, sudden high volume.
- Shared device cluster: multiple suspicious accounts share device or phone infrastructure.

## Example Feature Queries

Inbound sender count:

```cypher
MATCH (sender:Account)-[:SENT]->(tx:Transaction)-[:RECEIVED]->(recipient:Account {account_id: $account_id})
WHERE datetime(tx.created_at) >= datetime() - duration({minutes: 10})
RETURN count(DISTINCT sender) AS inbound_sender_count_10m;
```

Outbound account count:

```cypher
MATCH (recipient:Account {account_id: $account_id})-[:SENT]->(tx:Transaction)-[:RECEIVED]->(next:Account)
WHERE datetime(tx.created_at) >= datetime() - duration({minutes: 10})
RETURN count(DISTINCT next) AS outbound_account_count_10m;
```

Shared device cluster:

```cypher
MATCH (target:Account {account_id: $account_id})<-[:OWNS]-(:User)-[:USES_DEVICE]->(device:Device)<-[:USES_DEVICE]-(other:User)-[:OWNS]->(other_account:Account)
RETURN count(DISTINCT other_account) AS shared_device_cluster_size;
```

## Storage And Privacy

- Store hashes for account numbers and phone numbers where direct values are not required.
- Keep raw device and phone identifiers out of analytics views when possible.
- Treat graph-risk output as an assistive signal, not a final fraud verdict.
- Keep all model explanations reviewable for compliance and appeal flows.

