# VNPT Schema Integration Plan

## Purpose

This document cross-checks the VNPT API contract references against the FIDES mock data inventory and recommends schema updates for integrating real VNPT-backed services later.

Source references:

- `docs/api_references/vnpt/README.md`
- `docs/api_references/vnpt/endpoint_contracts.md`
- `docs/api_references/vnpt/vnpt_endpoint_contracts.json`
- `docs/mock_data_inventory.md`

## Executive Recommendation

Do not replace the FIDES domain schema with raw VNPT response schemas.

Instead, keep the current normalized Shield and Grow fields, then add a small provider-integration envelope to any block that can come from VNPT:

```json
{
  "provider_trace": {
    "provider": "VNPT",
    "product": "SmartReader",
    "endpoint_id": "smartreader.vat_invoice_ocr",
    "endpoint_path": "/rpa-service/aidigdoc/v1/ocr/hoa-don-gtgt",
    "client_session": "demo-grow-001",
    "file_hash": "mock_file_hash_001",
    "job_id": "",
    "status": "completed",
    "raw_response_ref": "mock://vnpt/smartreader/grow-coffee-strong.json",
    "error_code": null,
    "error_message": null
  }
}
```

This lets us:

- keep app logic stable,
- preserve vendor audit details,
- swap mock data for real VNPT adapters later,
- store raw vendor responses outside the business payload,
- avoid leaking VNPT tokens or raw credentials into frontend code.

Current MVP status: Shield challenge mocks now follow this pattern. Raw VNPT-shaped eKYC and SmartVoice JSON fixtures live in `backend/app/data/vnpt_mocks/`; the adapter loads those fixtures, normalizes them into Shield scoring fields, and returns `provider_raw_responses` for demo inspection.

The same boundary is now plug-in ready for real calls. With `VNPT_PROVIDER_MODE=mock`, the backend remains fully offline. With `VNPT_PROVIDER_MODE=real` and `VNPT_ACCESS_TOKEN`, `VNPT_TOKEN_ID`, `VNPT_TOKEN_KEY`, and `VNPT_EKYC_TOKEN` set server-side, the Shield challenge calls:

- `POST /ai/v1/face/liveness`
- `POST /ai/v1/face/mask`
- `POST /ai/v1/face/compare`
- `POST /stt-service/v3/standard`

The adapter keeps credentials out of the frontend, uploads local image refs via `/file-service/v1/addFile` and passes the returned hash to face APIs, sends STT as binary audio, then normalizes the provider JSON into the existing Shield scoring fields.

For `face/compare`, the request schema accepts `ekyc_document_ref` separately from `ekyc_image_ref`. Upload both via `POST /api/shield/challenge/upload-ekyc` or pass stored customer document refs from onboarding.

## Cross-Check Summary

| VNPT product | Public contract status | Current mock coverage | Main schema gap | Recommended schema update |
| --- | --- | --- | --- | --- |
| SmartReader | Full endpoint contracts for upload, OCR, table OCR, VAT invoice OCR, business registration OCR | Grow `ocr`, fake receipts | Missing file hash, client session, endpoint ID, warnings, VAT invoice native fields | Add provider trace and extend OCR extracted fields |
| SmartVoice STT | Full endpoint contracts for REST, async, gRPC, WebSocket STT | Shield `stt_transcript`, Grow `voice_entry` | Missing audio ID, audio URL/hash, transcript model, alternatives, async status | Add provider trace and STT metadata fields |
| SmartVoice TTS | Full endpoint contracts for TTS submit/status/download | Shield intervention docs, Smartbot advice text | No TTS output schema for generated intervention audio | Add `intervention_tts` or response-side TTS block |
| SmartVoice voice verification | Endpoint contracts for voice upload/encode/verify | Shield challenge `voice_verification_status`, `voice_match_score`, `voice_match_threshold` | Missing persistent enrollment and voice reference DB | Add provider trace/persistent enrollment store later |
| eKYC | Full endpoint contracts for ID OCR, liveness, mask, face compare, face verify/search | Shield `ekyc_*` flat fields | Missing client session, file hashes, result/msg/prob, card liveness, face swapping, fake liveness, tampering warnings | Add nested `ekyc_result` while keeping flat fields for MVP |
| SmartUX | Public SDK methods only, no REST contract | Shield `smartux_*` fields | Missing SDK session/event metadata | Add optional SDK trace fields, keep current risk fields |
| SmartBot | Product/API/RAG mention only, no public endpoint contract | Shield `llm_*`, Grow `smartbot_advice` | Missing bot session, policy/model version, RAG source refs | Add optional Smartbot trace metadata |
| SmartVision | Product pages and document names only | Shield face emotion/coercion labels | No public endpoint contract | Keep mock output; add provider trace only if private docs arrive |
| vnSocial | Product pages and document names only | Shield recipient reports, Grow reputation | Missing query/entity-resolution metadata | Add reputation query metadata, keep current scores |
| vnFace | Admin/product docs only | Shield face/emotion/eKYC-adjacent fields | No public endpoint contract | Keep mock output; integrate only with private API docs |

## Proposed Shared Schema Primitives

### Provider Trace

Add a reusable trace object:

```json
{
  "provider_trace": {
    "provider": "VNPT",
    "product": "SmartVoice",
    "endpoint_id": "smartvoice.stt_v3_standard",
    "endpoint_path": "/stt-service/v3/standard",
    "client_session": "shield-call-001",
    "request_id": "mock-request-001",
    "file_hash": "",
    "audio_id": "mock-audio-id-001",
    "text_id": "",
    "job_id": "",
    "status": "completed",
    "status_code": 200,
    "raw_response_ref": "mock://vnpt/smartvoice/shield-fake-police.json",
    "error_code": null,
    "error_message": null
  }
}
```

Recommended fields:

| Field | Meaning |
| --- | --- |
| `provider` | Usually `VNPT`. |
| `product` | `SmartReader`, `SmartVoice`, `eKYC`, `SmartUX`, `SmartBot`, `vnSocial`, etc. |
| `endpoint_id` | Local endpoint ID from `vnpt_endpoint_contracts.json`. |
| `endpoint_path` | VNPT endpoint path. |
| `client_session` | VNPT request/session correlation ID where supported. |
| `request_id` | FIDES-side request correlation ID. |
| `file_hash` | Hash returned by `/file-service/v1/addFile`. |
| `audio_id` | SmartVoice async/voice ID where available. |
| `text_id` | SmartVoice TTS ID where available. |
| `job_id` | Generic async job/session ID. |
| `status` | `mocked`, `submitted`, `processing`, `completed`, `failed`, or `not_available`. |
| `status_code` | HTTP or vendor status code. |
| `raw_response_ref` | Pointer to raw response stored server-side. |
| `error_code` | Vendor error code if any. |
| `error_message` | Vendor error message if any. |

This trace can be added to nested blocks without changing the UI logic.

### Raw Response Storage

Do not store full VNPT raw payloads in frontend-facing request objects.

Use references such as:

```json
"raw_response_ref": "mock://vnpt/smartreader/grow-coffee-strong.json"
```

Later, this can point to object storage or a database table with access controls.

## Shield Schema Updates

### SmartVoice STT

Current fields:

- `audio_source`
- `stt_transcript`
- `stt_confidence`
- `detected_patterns`
- `llm_scam_type`
- `llm_confidence`

VNPT contract fields to preserve:

- `object.id`
- `object.audio_type`
- `object.audio_url`
- `object.audio_hash`
- `object.sample_rate`
- `object.transcript_model`
- `object.transcript`
- `object.transcript_list`
- async `object.audio_id`
- async `object.results[].alternatives[].transcript`
- async `object.results[].alternatives[].confidence`

Recommended Shield addition:

```json
{
  "stt_provider_trace": {
    "provider": "VNPT",
    "product": "SmartVoice",
    "endpoint_id": "smartvoice.stt_v3_standard",
    "endpoint_path": "/stt-service/v3/standard",
    "audio_id": "mock-audio-id-001",
    "status": "completed",
    "raw_response_ref": "mock://vnpt/smartvoice/stt/shield-fake-police.json"
  },
  "stt_audio_url": "mock://audio/fake-police-001.wav",
  "stt_audio_hash": "mock_audio_hash_001",
  "stt_sample_rate": 16000,
  "stt_transcript_model": "vnpt-stt-standard",
  "stt_alternatives": [
    {
      "transcript": "Toi la cong an...",
      "confidence": 0.94
    }
  ]
}
```

Keep `stt_transcript` as the normalized transcript used by Shield rules.

### SmartVoice TTS For Intervention

Current schema only stores intervention text in the response/docs. VNPT TTS supports `text_id`, playlist/audio links, and download.

Recommended response-side block:

```json
{
  "intervention_tts": {
    "provider": "SmartVoice",
    "text": "Hay tam dung giao dich...",
    "text_id": "mock-tts-001",
    "audio_url": "mock://tts/shield-warning-001.mp3",
    "audio_format": "MP3",
    "voice": "female_northern",
    "status": "ready",
    "provider_trace": {
      "provider": "VNPT",
      "product": "SmartVoice",
      "endpoint_id": "smartvoice.tts_v2_standard",
      "endpoint_path": "/tts-service/v2/standard",
      "text_id": "mock-tts-001",
      "status": "completed"
    }
  }
}
```

This belongs in Shield response/intervention orchestration, not in incoming transaction risk input.

### SmartVoice Voice Verification

Current fields:

- `voice_reference_source`
- `voice_verification_status`
- `voice_match_score`
- `voice_match_threshold`

VNPT contract flow:

- upload reference and challenge audio with `/v1/voice-id/audio/upload`
- encode uploaded audio URLs with `/v1/voice-id/audio/encode`
- compare encoded IDs with `/voiceid/api/v1/audio/verify`

Recommended Shield behavior:

```json
{
  "voice_reference_source": "mock_payload/customer_voice_samples/voice_ref_1",
  "voice_verification_status": "passed",
  "voice_match_score": 0.91,
  "voice_match_threshold": 0.75
}
```

Voice verification should answer only whether the challenge voice resembles the enrolled customer sample. It should not replace scam-script detection, coercion detection, or eKYC. In the MVP scorer, a score below `0.55` fails Stage 2, a score below `0.75` enters review, and a score at or above threshold adds no voice-identity risk.

### eKYC

Current fields:

- `ekyc_verification_status`
- `ekyc_liveness_passed`
- `ekyc_mask_detected`
- `ekyc_face_match_score`
- `ekyc_injection_risk_score`

VNPT endpoint contracts map to:

- face compare: `object.result`, `object.msg`, `object.prob`
- face liveness: `object.liveness`, `object.liveness_msg`, `object.is_eye_open`
- face mask: `object.masked`
- card liveness: `object.liveness`, `object.face_swapping`, `object.fake_liveness`
- ID OCR warning/tampering: `object.warning`, `object.warning_msg`, `object.tampering.*`

Recommended Shield addition:

```json
{
  "ekyc_result": {
    "provider": "VNPT eKYC",
    "client_session": "shield-ekyc-001",
    "document_file_hash": "mock_doc_hash",
    "face_file_hash": "mock_face_hash",
    "face_compare_result": "MATCH",
    "face_compare_score": 0.9,
    "face_compare_message": "MATCH",
    "face_liveness": true,
    "face_liveness_message": "LIVE",
    "is_eye_open": true,
    "mask_detected": false,
    "card_liveness": true,
    "face_swapping_detected": false,
    "fake_liveness_detected": false,
    "tampering_detected": false,
    "warning_codes": [],
    "provider_traces": [
      {
        "provider": "VNPT",
        "product": "eKYC",
        "endpoint_id": "ekyc.face_compare",
        "endpoint_path": "/ai/v1/face/compare",
        "status": "completed"
      }
    ]
  }
}
```

Keep the existing flat `ekyc_*` fields as summary fields for MVP scoring.

### SmartUX

VNPT public docs expose SDK methods, not REST contracts:

- `track_sessions`
- `track_pageview`
- `track_clicks`
- `track_scrolls`
- `track_errors`
- `track_links`
- `track_forms`
- `collect_from_forms`

Current fields are good for risk fusion:

- `smartux_behavior_anomaly_score`
- `smartux_remote_control_score`
- `smartux_signals`

Recommended optional metadata:

```json
{
  "smartux_session": {
    "provider": "VNPT SmartUX",
    "sdk_session_id": "mock-smartux-session-001",
    "app_key_ref": "server-side-config",
    "tracked_event_count": 42,
    "last_event_at": "2026-06-28T10:07:00Z",
    "sdk_methods": [
      "track_sessions",
      "track_forms",
      "track_errors"
    ]
  }
}
```

### vnSocial

No public endpoint contract was found, but the product maps directly to our mock reputation/report database.

Recommended metadata:

```json
{
  "vn_social_lookup": {
    "query_type": "phone_or_account",
    "query_value_hash": "mock_hash",
    "entity_resolution_confidence": 0.82,
    "source_window_days": 30,
    "raw_response_ref": "mock://vnpt/vnsocial/shield-recipient-001.json"
  }
}
```

Keep current normalized fields for scoring.

## Grow Schema Updates

### SmartReader Invoice OCR

Current fields:

- `ocr.provider`
- `ocr.status`
- `ocr.confidence`
- `ocr.extracted_fields.invoice_id`
- `ocr.extracted_fields.seller_name`
- `ocr.extracted_fields.buyer_name`
- `ocr.extracted_fields.total_amount`
- `ocr.extracted_fields.tax_amount`
- `ocr.extracted_fields.line_items`

VNPT SmartReader VAT invoice endpoint includes:

- `buyer_address`
- `buyer_company_name`
- `buyer_name`
- `buyer_tax_code`
- `details`
- `general_tax_rates`
- `grand_total_after_tax`
- `grand_total_after_tax_in_text`
- `grand_total_before_tax`

Recommended Grow OCR addition:

```json
{
  "ocr": {
    "provider": "SmartReader",
    "status": "completed",
    "confidence": 0.93,
    "provider_trace": {
      "provider": "VNPT",
      "product": "SmartReader",
      "endpoint_id": "smartreader.vat_invoice_ocr",
      "endpoint_path": "/rpa-service/aidigdoc/v1/ocr/hoa-don-gtgt",
      "client_session": "grow-ocr-001",
      "file_hash": "mock_receipt_hash_001",
      "status": "completed",
      "raw_response_ref": "mock://vnpt/smartreader/grow-coffee-strong.json"
    },
    "extracted_fields": {
      "invoice_id": "INV-2026-001",
      "seller_name": "An Nhien Coffee",
      "seller_tax_code": "mock_seller_tax_code",
      "seller_address": "mock seller address",
      "buyer_name": "Office Pantry Co.",
      "buyer_company_name": "Office Pantry Co.",
      "buyer_tax_code": "mock_buyer_tax_code",
      "buyer_address": "mock buyer address",
      "subtotal_amount": 29090909,
      "tax_amount": 2909091,
      "total_amount": 32000000,
      "total_amount_in_text": "Ba muoi hai trieu dong",
      "general_tax_rates": ["10%"],
      "currency": "VND",
      "line_items": []
    }
  }
}
```

Line-item extension:

```json
{
  "description": "Monthly coffee bean supply",
  "quantity": 1,
  "unit_price": 18000000,
  "amount": 18000000,
  "tax_rate": "10%",
  "tax_amount": 1636364
}
```

### SmartReader Business Registration OCR

SmartReader exposes `dang-ky-kinh-doanh` extraction. This is not in Grow yet, but it is valuable for KYB and partner-bank handoff.

Recommended new Grow block:

```json
{
  "business_verification": {
    "provider": "SmartReader",
    "status": "completed",
    "business_registration_file_hash": "mock_registration_hash",
    "business_tax_code": "mock_tax_code",
    "registered_business_name": "An Nhien Coffee",
    "registered_owner_name": "Nguyen Thi An",
    "registered_address": "mock registered address",
    "registration_date": "2023-04-12",
    "charter_capital": 500000000,
    "verification_confidence": 0.88,
    "provider_trace": {
      "provider": "VNPT",
      "product": "SmartReader",
      "endpoint_id": "smartreader.business_registration_ocr",
      "endpoint_path": "/rpa-service/aidigdoc/v1/ocr/dang-ky-kinh-doanh",
      "status": "completed"
    }
  }
}
```

This can feed `capital_connection.required_documents` and partner-bank review.

### SmartVoice Grow Bookkeeping

Current `voice_entry` is good as a normalized object, but should preserve VNPT STT metadata:

```json
{
  "voice_entry": {
    "provider": "SmartVoice",
    "status": "completed",
    "audio_source": "mock://audio/grow-voice-001.wav",
    "audio_id": "mock-audio-id-grow-001",
    "audio_hash": "mock_audio_hash",
    "sample_rate": 16000,
    "transcript_model": "vnpt-stt-standard",
    "transcript": "Hom nay ghi nhan doanh thu...",
    "confidence": 0.91,
    "provider_trace": {
      "provider": "VNPT",
      "product": "SmartVoice",
      "endpoint_id": "smartvoice.stt_v3_standard",
      "endpoint_path": "/stt-service/v3/standard",
      "audio_id": "mock-audio-id-grow-001",
      "status": "completed"
    },
    "parsed_fields": {}
  }
}
```

### SmartBot Capital Advice

No public SmartBot endpoint contract was found, but SmartBot is used in Grow capital advice.

Recommended addition inside `smartbot_advice`:

```json
{
  "smartbot_advice": {
    "provider": "Smartbot",
    "message": "A modest working-capital offer may help...",
    "confidence": 0.66,
    "conversation_id": "mock-grow-advice-001",
    "model_version": "mock_smartbot_v1",
    "policy_version": "capital_advice_guardrails_v1",
    "rag_source_refs": [
      "cashflow_forecast",
      "capital_connection.partner_offers"
    ],
    "disclaimer": "Demo advisory output, not a binding credit decision."
  }
}
```

## Mock Inventory Updates

Add one explicit mock database area:

### VNPT Provider Trace Store

Stores per-call provider metadata and raw response references for VNPT-backed mocks.

MVP:

- Inline `provider_trace` objects in dataset payloads.
- Optional raw response mock files later under:
  - `backend/app/data/vnpt_mocks/smartreader/`
  - `backend/app/data/vnpt_mocks/smartvoice/`

Later:

- `provider_calls` table with:
  - request ID,
  - provider/product,
  - endpoint ID/path,
  - client session,
  - file/audio/text IDs,
  - status,
  - raw request/response storage refs,
  - error code/message,
  - timestamps.

## Priority For Schema Changes

### Priority 1: Safe MVP Additions

These are low risk because they can be optional and do not change scoring:

1. Add shared `provider_trace` schema.
2. Add `provider_trace` to `GrowOcrInput`.
3. Add `provider_trace`, `audio_id`, `audio_hash`, `sample_rate`, and `transcript_model` to `GrowVoiceEntry`.
4. Add `stt_provider_trace`, `stt_audio_hash`, `stt_sample_rate`, and `stt_transcript_model` to Shield.
5. Add `provider_trace` metadata to Smartbot capital advice.

### Priority 2: Useful For Demo Polish

1. Extend `OcrExtractedFields` with VNPT VAT invoice fields:
   - `seller_tax_code`
   - `seller_address`
   - `buyer_company_name`
   - `buyer_tax_code`
   - `buyer_address`
   - `subtotal_amount`
   - `total_amount_in_text`
   - `general_tax_rates`
2. Extend `InvoiceItem` with:
   - `tax_rate`
   - `tax_amount`
3. Add `business_verification` for SmartReader business registration OCR.

### Priority 3: Later Integration

1. Add nested `ekyc_result` and keep flat `ekyc_*` summary fields.
2. Add `intervention_tts` to Shield response or intervention orchestration.
3. Add `smartux_session`.
4. Add `vn_social_lookup`.
5. Add raw response mock files under `backend/app/data/vnpt_mocks/`.

## Recommended Immediate Schema Update

For the current codebase, the best next implementation step is:

1. Add a reusable `ProviderTrace` Pydantic model.
2. Add optional provider trace fields to:
   - `GrowOcrInput`
   - `GrowVoiceEntry`
   - `SmartbotCapitalAdvice`
3. Extend Grow invoice OCR fields for SmartReader VAT invoice output.
4. Leave Shield eKYC and SmartUX as-is for now, because their current flat summary fields already support risk scoring.

This gives us strong VNPT alignment for the Grow demo, where the public SmartReader and SmartVoice contracts are most concrete, while keeping Shield stable.
