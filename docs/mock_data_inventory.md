# FIDES Mock Data And Database Inventory

## Purpose

This document lists the data, service outputs, and database state that FIDES needs to mock for the MVP.

The guiding rule for the 5-day build: mock service outputs and database state as stable JSON first. Do not build a real graph database, ledger database, partner marketplace, or model registry unless the demo specifically needs live querying.

## Current Files

| File or folder | Purpose |
|------------------------------------|------------------------------------|
| `backend/app/data/demo_dataset.json` | Curated Shield and Grow demo scenarios. |
| `backend/app/data/synthetic_demo_dataset.json` | Generated 1,000-record dataset for volume/UI testing. |
| `scripts/generate_synthetic_dataset.py` | Seeded madlib generator for Shield and Grow records. |
| `frontend/static/fixtures/receipts/` | Fake receipt PNGs for Grow OCR demos. |
| `scripts/generate_receipt_fixtures.py` | Receipt fixture generator. |
| `uploads/ekyc/` | Uploaded selfie and CCCD images for real VNPT eKYC. |
| `uploads/smartvoice/` | Uploaded challenge audio for real VNPT SmartVoice STT and local voice-stress analysis. |
| `docs/graph_database_schema.md` | Future graph database design. |
| `sdks/web/` | Web SDK scaffold for in-page telemetry and Shield/Grow calls. |
| `sdks/mobile/` | Android/iOS SDK scaffold for host-app telemetry and Shield/Grow calls. |

## Must Mock For MVP

These are required for a convincing end-to-end demo.

| Area | Mock data/database | Current MVP representation | Real replacement later |
|------------------|------------------|------------------|------------------|
| Demo scenario catalog | Curated Shield and Grow records | `demo_dataset.json` | Seeded demo database or admin-managed scenario library |
| Bulk demo records | 500 Shield + 500 Grow synthetic records | `synthetic_demo_dataset.json` | Test fixtures generated from staging-like data |
| Shield transaction context | Amount, recipient, account, known-recipient flag | Flat Shield payload | Bank transaction API |
| Telecom context | Active call, caller type, caller number, suspicious prefix | Flat Shield payload | Mobile SDK, OS permissions, telco metadata where available |
| Scam transcript | STT transcript and scam-script patterns | Flat Shield payload | SmartVoice STT + Smartbot classifier |
| Recipient reputation | vnSocial report count and keywords | Flat Shield payload | vnSocial or bank/customer-support report service |
| Official/interbank watchlist | SIMO/NHNN status and last checked time | Flat Shield payload | Official or consortium lookup API |
| Recipient graph risk | Mule score, graph pattern, fan-in/fan-out features | Flat Shield payload | FIDES graph database + graph feature service |
| Native telemetry | Remote-control, screen-sharing, accessibility risk, SmartUX signals | Flat Shield payload | SDK consumer telemetry |
| eKYC/deepfake signals | Liveness, mask/spoof, face match, injection risk | Flat Shield payload | eKYC SDK/API |
| Coercion signals | Voice stress, face emotion, scripted behavior | Flat Shield payload | SmartVoice/SmartVision/vnFace style services |
| Circuit-breaker response | Stage 1/Stage 2 decision, hold state, notification flag, behavioral-science message | Shield response | Intervention orchestration service |
| Grow input records | Business, invoice, customer, items, payment status | Flat Grow payload | Ledger/invoice database |
| OCR extraction | SmartReader invoice fields and confidence | Grow `ocr` block | SmartReader OCR API |
| Voice bookkeeping | SmartVoice transcript and parsed fields | Grow `voice_entry` block | SmartVoice STT + parser |
| Ledger normalization | Stable bookkeeping entry | Grow `normalized_ledger_entry` block | Ledger database |
| Receipt images | Synthetic receipts for UI preview | `frontend/static/fixtures/receipts/` | Uploaded files/object storage |
| Cashflow summary | Inflow, outflow, net cashflow, largest customer | Grow `cashflow_summary` block | Ledger + bank transaction reconciliation |
| Cashflow forecast | Liquidity risk, shortfall, borrowing window | Grow `cashflow_forecast` block | Forecasting service over transaction history |
| Tax draft | VAT estimate, taxable revenue, filing status | Grow `tax_summary` block | Tax-rule engine/accountant workflow |
| E-invoice workflow | Provider status, validation errors, notes | Grow `einvoice_status` block | Certified e-invoice provider |
| Alternative credit | Trust graph, vnSocial reputation, credit score | Grow `alternative_credit_profile` block | Feature store + credit model |
| Explainability | Gradient-boosting/SHAP-style contributions | Nested `explainability` block | Model registry + SHAP pipeline |
| Capital connection | Partner loan/insurance offers, Smartbot advice | Grow `capital_connection` block | Partner-bank/insurer APIs + offer engine |

## Databases To Mock

These do not need real database infrastructure for MVP, but the demo should behave as if they exist.

### Scenario Store

Stores curated demo scenarios and synthetic cases.

MVP:

-   JSON files served by `/api/demo/dataset` and `/api/demo/synthetic-dataset`.

Later:

-   Tables for scenarios, personas, expected outcomes, tags, and demo metadata.

### Graph Database

Models users, accounts, phones, devices, transactions, reports, and watchlist snapshots.

MVP:

-   Flat features inside Shield payloads:
    -   `graph_risk_score`
    -   `graph_pattern`
    -   `inbound_sender_count_10m`
    -   `outbound_account_count_10m`
    -   `median_pass_through_minutes`
    -   `account_age_days`
    -   `shared_device_cluster_size`
    -   `funds_moved_within_minutes`

Later:

-   Neo4j or similar graph store.
-   Nodes: user, account, phone, device, transaction, report, watchlist snapshot.
-   Edges: owns, uses, sent_to, reported_as, shares_device, watchlisted_as.

### Reputation And Report Database

Stores scam reports, vnSocial mentions, customer-support cases, public/social reputation, and complaint trends.

MVP:

-   Shield fields:
    -   `vn_social_report_count`
    -   `vn_social_recent_keywords`
-   Grow fields:
    -   `vn_social_reputation_score`
    -   `vn_social_mentions_30d`
    -   `vn_social_sentiment`
    -   `vn_social_complaint_count_30d`

Later:

-   Report ingestion pipeline.
-   Entity resolution across phone, account, business name, tax ID, and social handles.
-   Confidence and moderation state for unverified reports.

### Ledger Database

Stores normalized business transactions from receipts, invoices, bank transactions, and voice entries.

MVP:

-   Grow payload blocks:
    -   `ocr`
    -   `voice_entry`
    -   `normalized_ledger_entry`
    -   `items`

Later:

-   Tables for businesses, invoices, receipts, ledger entries, counterparties, categories, attachments, source confidence, and edit history.

### Compliance Database

Stores tax drafts, e-invoice status, validation errors, provider request IDs, and audit state.

MVP:

-   Grow payload blocks:
    -   `tax_summary`
    -   `einvoice_status`

Later:

-   Tax-period tables.
-   E-invoice provider submissions.
-   Digital-signature state.
-   Cancellation/adjustment history.
-   Accountant/user review workflow.

### Forecast Database

Stores projected cashflow, liquidity risk, shortfall dates, and forecast driver snapshots.

MVP:

-   Grow `cashflow_forecast` block.

Later:

-   Forecast runs table.
-   Time-series features.
-   Recurring obligations.
-   Receivable settlement probabilities.
-   Model version and driver audit.

### Credit Feature Store And Model Registry

Stores model inputs, alternative-credit scores, model versions, and explanation artifacts.

MVP:

-   Grow `alternative_credit_profile`.
-   Nested `explainability` with mock gradient-boosting and SHAP-style outputs.

Later:

-   Feature store.
-   Model registry.
-   Training dataset lineage.
-   SHAP/explanation cache.
-   Bias/fairness and drift monitoring.

### Partner Offer Catalog

Stores partner-bank and insurer products, eligibility rules, pricing, required documents, and next steps.

MVP:

-   Grow `capital_connection` block with:
    -   `Mock Partner Bank A`
    -   `Mock Insurance Partner B`

Later:

-   Partner product catalog.
-   Eligibility engine.
-   Pricing/quote API integrations.
-   Consent and document handoff.
-   Quote expiry and binding offer status.

### Feedback And Pattern Registry

Stores intervention outcomes and anonymized fraud-pattern updates.

MVP:

-   Documented but not yet implemented as a route.
-   Could be a local JSONL file:
    -   `backend/app/data/feedback_events.jsonl`
    -   `backend/app/data/pattern_registry.json`

Later:

-   Append-only feedback table.
-   Offline model/rule update jobs.
-   Review queue for new scam patterns.

### Consent And Audit Log

Stores consent for audio analysis, social/reputation data use, partner data sharing, and user-facing advice.

MVP:

-   Payload flags and fields:
    -   `consent_granted`
    -   `capital_connection.consent_required`
    -   `capital_connection.data_sharing_scope`

Later:

-   Consent ledger.
-   Audit log for viewed advice, shared data, model version, offer version, and user action.

### VNPT Provider Trace Store

Stores per-call metadata and raw response references for VNPT-backed mock outputs.

MVP:

-   Inline provider trace objects in VNPT-backed payload blocks.
-   Return raw VNPT-style responses in the demo response for judge inspection; production should replace this with server-side raw response references.
-   Optional future mock file paths (not used by Shield challenge — real APIs only):
    -   `backend/app/data/vnpt_mocks/smartreader/`

Later:

-   Provider-call table with provider/product, endpoint ID, endpoint path, client session, file/audio/text IDs, status, raw request/response refs, error details, and timestamps.
-   Real Shield challenge calls can already be enabled with `VNPT_PROVIDER_MODE=real` and server-side VNPT token headers; the database layer should record the same trace fields once persistent storage is added.

## External Services To Mock

VNPT public contract cross-check and schema integration recommendations are documented in `docs/vnpt_schema_integration_plan.md`.

| Service | Used By | MVP mock |
|------------------------|------------------------|------------------------|
| SmartReader | Grow OCR | `ocr` block and fake receipt images |
| SmartVoice | Shield STT, Shield voice verification, Grow voice bookkeeping | `stt_transcript`, `voice_verification_status`, `voice_match_score`, `voice_entry`, confidence fields |
| Smartbot | Shield scam classification, Grow capital advice | `detected_patterns`, `llm_scam_type`, `smartbot_advice` |
| eKYC/vnFace | Shield deepfake/liveness | `ekyc_*` and face emotion fields |
| SmartUX/native telemetry | Shield remote-control and behavior anomaly | `smartux_*`, `native_telemetry_*`, remote-control flags |
| vnSocial | Shield recipient risk, Grow reputation | `vn_social_*` fields in Shield and Grow |
| SIMO/NHNN | Shield recipient watchlist | `simo_status`, `simo_last_checked_at` |
| E-invoice provider | Grow compliance | `einvoice_status` |
| Partner banks | Grow capital connection | `partner_offers` |
| Insurance partners | Grow capital connection | inventory insurance offer |

## MVP Build Priority

Build first:

1.  Curated demo dataset.
2.  Synthetic dataset generator.
3.  Fake receipt fixtures.
4.  Flat Shield recipient/telemetry/scam fields.
5.  Grow ledger, forecast, alternative credit, and capital connection blocks.
6.  Documentation for what each mock replaces.

Build only if time permits:

1.  JSONL feedback log.
2.  Mock pattern registry endpoint.
3.  Separate mock partner-offer catalog file.
4.  Separate mock graph response endpoint.
5.  Separate mock ledger store.

Avoid for the 5-day MVP:

1.  Real Neo4j setup.
2.  Real partner-bank API integrations.
3.  Real tax/e-invoice submission.
4.  Real model training pipeline.
5.  Real device telemetry capture.

## Current Recommendation

Keep the MVP data strategy simple:

-   Use `demo_dataset.json` for curated storytelling.
-   Use `synthetic_demo_dataset.json` for volume.
-   Use generated receipt images for OCR visuals.
-   Keep all derived service outputs embedded in each scenario payload.
-   Document future databases clearly, but do not implement them until the demo flow is stable.
