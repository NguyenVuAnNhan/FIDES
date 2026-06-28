# VNPT Endpoint Contracts

Generated: 2026-06-28

Scope: public VNPT documentation and public frontend bundles only. This file turns the scraped public docs into integration contracts. It is intentionally not a full mirror of the vendor docs.

Related inventory: [README.md](README.md) and [vnpt_public_api_reference.json](vnpt_public_api_reference.json). Machine-readable contracts: [vnpt_endpoint_contracts.json](vnpt_endpoint_contracts.json).

## Common Headers

Most documented VNPT AI REST endpoints use these token headers:

```http
Content-Type: application/json
Authorization: Bearer ${access_token}
Token-id: ${token_id}
Token-key: ${token_key}
```

eKYC JSON examples also include:

```http
mac-address: TEST1
```

Upload endpoints use `multipart/form-data` or binary audio bodies instead of JSON. Keep VNPT token values server-side.

## VNPT eKYC

Base URL: `https://api.idg.vnpt.vn`

Source: `https://ekyc.vnpt.vn/admin-dashboard/en/documents/api`

### eKYC Request Fields

| Endpoint | Body contract |
| --- | --- |
| `POST /file-service/v1/addFile` | `multipart/form-data`: `file: File` required, `title: string`, `description: string`. |
| `POST /ai/v1/classify/id` | JSON: `img_card: string` required, `client_session: string` required, `token: string` required. |
| `POST /ai/v1/card/liveness` | JSON: `img: string` required, `client_session: string` required. |
| `POST /ai/v1/ocr/id/front` | JSON: `img_front: string` required, `client_session: string` required, `type: integer`, `validate_postcode: boolean`, `token: string` required. |
| `POST /ai/v1/ocr/id/back` | JSON: `img_back: string` required, `client_session: string` required, `type: integer` required, `token: string` required. |
| `POST /ai/v1/ocr/id` | JSON: `img_front: string` required, `img_back: string` required, `client_session: string` required, `type: integer`, `crop_param: string`, `validate_postcode: boolean`, `token: string` required. |
| `POST /ai/v1/face/compare` | JSON: `img_front: string` required, `img_face: string` required, `client_session: string` required, `token: string` required. |
| `POST /ai/v1/face/liveness` | JSON: `img: string` required, `client_session: string` required, `token: string`. |
| `POST /ai/v1/face/mask` | JSON: `img: string` required, `face_bbox: string`, `face_lmark: string`, `client_session: string` required. |
| `POST /face-service/face/add` | JSON: `bbox`, `landmark`, `unit: string`, `customer_information` object. Customer fields include `card_id`, `passport_id`, `driver_license_id`, `military_id`, `police_id`, `other_id`, `fullname`, `dob`, `gender`, `address`, `hometown`, `nationality`, `ipfs`, `title`, `other_type`, `extra_info`. |
| `POST /face-service/face/verify` | JSON: `img: string`, `id_card: string`, `id_type: integer/string`, `unit: string`. |
| `POST /face-service/face/search` | JSON: `img: string`, `unit: string`. |
| `POST /face-service/face/search-k` | JSON: `img: string` required, `unit: string` required, `k: integer` required, `threshold: float` required. |
| `POST /aicommon-service/cic/v1/verify_face` | JSON: `card_id` required, `type_card` required, optional `img_face`, `img_front`, `fullname`, `birth_day`, `origin_location`, `recent_location`, `gender`, `nationality`, `issue_date`. This block is present in the public bundle but commented in the rendered Markdown. |
| `POST /aicommon-service/cic/v1/verify_customer` | JSON: `card_id: string` required, `fullname: string` required, `type_card: integer` required, `phonenumber: string` required, `verify: boolean`. |

### eKYC Response Fields

| Endpoint | Success response contract |
| --- | --- |
| `POST /file-service/v1/addFile` | `message`, `object.fileName`, `object.title`, `object.description`, `object.hash`, `object.fileType`, `object.uploadedDate`, `object.storageType`, `object.tokenId`. |
| `POST /ai/v1/classify/id` | `message`, `object.type`, `object.name`. Type values in docs: `0/1` old ID front/back, `2/3` new ID front/back, `5` passport, `4` other. |
| `POST /ai/v1/card/liveness` | `message`, `object.liveness`, `object.liveness_msg`, `object.face_swapping`, `object.fake_liveness`. |
| `POST /ai/v1/ocr/id/front` | `message`, `object.msg`, `object.card_type`, `object.id`, `object.id_probs`, `object.name`, `object.birth_day`, `object.birth_day_prob`, `object.nationality`, `object.nation`, `object.gender`, `object.valid_date`, `object.origin_location`, `object.origin_location_prob`, `object.recent_location`, `object.recent_location_prob`, `object.type_id`, `object.warning`, `object.warning_msg`, `object.expire_warning`, `object.back_expire_warning`, `object.post_code`, `object.tampering.is_legal`, `object.tampering.warning`. |
| `POST /ai/v1/ocr/id/back` | `message`, `object.issue_place`, `object.issue_date`, `object.issue_date_prob`, `object.issue_date_probs`, `object.issue_place_prob`, `object.back_type_id`, `object.back_expire_warning`, `object.msg_back`. |
| `POST /ai/v1/ocr/id` | Combined front/back OCR fields plus `message`, `object`, `server_version`. |
| `POST /ai/v1/face/compare` | `message`, `server_version`, `object.result`, `object.msg`, `object.prob`. `object.msg` examples: `MATCH`, `NOMATCH`. |
| `POST /ai/v1/face/liveness` | `message`, `object.liveness`, `object.liveness_msg`, `object.is_eye_open`. |
| `POST /ai/v1/face/mask` | `message`, `object.masked`. |
| `POST /face-service/face/add` | `message`, `object.result`, `object.msg`, `object.customer_information` including generated `customer_id`. |
| `POST /face-service/face/verify` | `message`, `object.result`, `object.msg`, `object.prob`, `object.id_card`, `object.id_type`. |
| `POST /face-service/face/search` | `message`, `object.result`, `object.msg`, `object.customer_information`, optional `face_probability`. |
| `POST /face-service/face/search-k` | `message`, `object.result`, `object.msg`, `object.customer_informations[]` with `customer_information` and `face_probability`. |
| `POST /aicommon-service/cic/v1/verify_face` | `message`, `object.informations`, `object.result`, `object.msg`. `informations` can include `face_probability`, `front_probability`, booleans for `card_id`, `fullname`, `gender`, `nationality`, `issue_date`, and nested booleans for date/address parts. |
| `POST /aicommon-service/cic/v1/verify_customer` | `message`, `object.informations.card_id`, `object.informations.phonenumber`, `object.informations.fullname`, `object.result`, `object.msg`. |

Common eKYC error shape: `status`, `message`, `statusCode`, `errors[]`.

## VNPT SmartVoice

Default base URL: `https://api.idg.vnpt.vn`

Voice Verification base URL: `https://api.idg.vnpt.vn/voice-service`

Sources:

- `https://smartvoice.vnpt.vn/documents/api`
- `https://smartvoice.vnpt.vn/en/sdk`
- `https://vnptai.io/smartvoice/en/documents/api`

### Auth

| Endpoint | Contract |
| --- | --- |
| `POST /auth-service/oauth/token` | Headers: `Content-Type: application/json`. Body: `username`, `password`, `client_id`, `grant_type`, `client_secret`. Success response: `access_token`, `token_type`, `refresh_token`, `expires_in`, `scope`. Vendor text renders this once as `/auth-service /oauth/token`; use `/auth-service/oauth/token`. |

### Text To Speech

| Endpoint | Request contract | Response contract |
| --- | --- | --- |
| `POST /ai/api/v1/text-to-speech` | Public/advanced JSON: `text`, `text_split`, `model` (`news` or `books`), `region`, `captcha`. | Success: `code`, `text_id`, `version`. Error: `code`, `message`, `version`. |
| `POST /ai/api/v1/text-to-speech/check-status` | JSON: `text_id`. | `code`, `playlist[]` with `idx`, `text`, `text_len`, `total`, `audio_link`, plus `text_id`, `version`. |
| `POST /ai/api/v1/text-to-speech/download` | JSON: `text_id`, `type` (`MP3` or `WAV`). | Binary audio file in the requested format. |
| `POST /tts-service/v1/standard` | Authenticated JSON: `text` required, `text_split`, `model`, `region`, `audio_format`, `sample_rate`, `use_abbr_converter`, `auto_silence`, `clear_cached`, `combine_final`, `domain`, `speed`, `prosody`, `captcha`. | Success: `message`, `object.code`, `object.text_id`, `object.version`, `hash_text`, `length_text`. Error: `messageObjects`, `messageFields`, `statusCode`, `message`, `status`, `error`, `hash_text`, `length_text`. |
| `POST /tts-service/v1/check-status` | JSON: `text_id`. | Success/pending response under `object`: `code`, `playlist[]`, `r_audio_full_finished`, `r_audio_full`, `text_id`, `version`, `version_ai`. |
| `POST /tts-service/v2/standard` | Authenticated JSON: `text` required, `model`, `region`, `audio_format`, `sample_rate`, `use_abbr_converter`, `auto_silence`, `clear_cached`, `domain`, `speed`, `prosody`, `captcha`. | `message`, `object.code`, `object.playlist[]`, `object.r_audio_full_finished`, `object.r_audio_full`, `object.text_id`, `object.version`, `object.version_ai`. |
| `POST /tts-service/v2/grpc` | Authenticated JSON similar to TTS v2; docs note a maximum text length of 1800 characters. | Streaming/audio-oriented TTS result; public docs expose gRPC service names rather than a full REST JSON response table. |

TTS gRPC service names found: `Synthesize(SynthesizeSpeechRequest)` and `SynthesizeOnline(SynthesizeSpeechRequest)`.

### Speech To Text

| Endpoint | Request contract | Response contract |
| --- | --- | --- |
| `POST /stt-service/v3/standard` | Binary audio body. Headers include token auth plus `Enable-Lm`, `Sample-Rate`, `content-type`, `bit-per-rate`, `domain`, `save-log`, `cap_punct_recovery`. Supported content types include `application/octet-stream`, `audio/wav`, `audio/x-wav`, `audio/wave`, `audio/mpeg`. | `message`, `object.id`, `object.audio_type`, `object.audio_url`, `object.audio_hash`, `object.sample_rate`, `object.transcript_model`, `object.transcript`, `object.transcript_list`, plus duration/model/version metadata in examples. |
| `POST /stt-service/v1/grpc/standard` | Binary `audioFile` and `clientSession`; token auth headers. | STT transcript response with recognized alternatives and audio metadata. |
| `POST /stt-service/v1/grpc/async/standard` | Binary `audioFile` and `clientSession` to start; later calls use `clientSession` to retrieve status/result. | Processing or completed transcript response. |
| `POST /stt-service/v1/async/vn` | Binary audio body for larger files; docs state `10MB < size <= 250MB` or duration up to 2 hours. | `description`, `errors[]`, `message`, `object.audio_id`, `status`. |
| `POST /stt-service/v1/async/status` | JSON/raw body: `audio_id: string`. | Pending: `object.message`, `object.status=ACCEPTED`. Complete: `object.audio_duration`, `object.results[]`, `object.status=OK`; alternatives include `transcript`, `confidence`, `channelTag`. |
| WebSocket `wss://websocket.vnpt.vn/v1/streaming-recognize?authorization=<accessToken>&token-id=<token-id>&token-key=<token-key>` | First message includes `streamingConfig.config.encoding`, `sampleRateHertz`, `languageCode`, `maxAlternatives`, `audioChannelCount`, `enableWordTimeOffsets`, `enableSeparateRecognitionPerChannel`, `model`, `customConfiguration.invert_text`, `customConfiguration.cap_punct_recovery`, `interimResults`; later messages stream audio. | Streaming recognition events/results. Vendor text has a stray space before `token-key`; remove it. |

STT gRPC service names found: `Recognize(RecognizeRequest)` and `StreamingRecognize(stream StreamingRecognizeRequest)`.

### Voice Verification

Base URL: `https://api.idg.vnpt.vn/voice-service`

| Endpoint | Request contract | Response contract |
| --- | --- | --- |
| `POST /v1/voice-id/audio/upload` | Auth headers. Body: audio `file` upload, `.wav` in examples. | `message`, `object.ok`, `object.result` audio URL. Error shape includes `messageFields`, `messageObjects`, `message`, `error`, `statusCode`, `status`. |
| `POST /v1/voice-id/audio/encode` | JSON: `audio_url`, `registered: integer` (`0` verification/default, `1` registration), `data.email` required, `data.name` optional. | `message`, `object.ok`, `object.result` audio ID. Validation errors use `detail[]`. |
| `GET /v1/voice-id/audio/unregister?email=<email>` | Query: `email`. | `message`, `object.ok`, `object.result`, `challengeCode`. |
| `POST /v1/voice-id/audio/search-by-upload` | Public guide lists the endpoint; request is upload/search audio payload. | Search response under `object`; the public page does not expose a complete field table in the scraped section. |
| `GET /v1/voice-id/audio/info-by-email?email=<email>` | Query: `email`. | `message`, `object.ok`, `object.result` voice enrollment info or `null`, optional `challengeCode`. |
| `GET /voiceid/api/v1/audio/verify` | Query: `audio_id1`, `audio_id2`. | Success: `message`, `object.ok`, `object.result.similarity`, `object.result.score`. Error: `object.ok=false`, `error_code`, `description`. |

## VNPT SmartReader

Base URL: `https://api.idg.vnpt.vn`

Sources:

- `https://console-smartreader.vnpt.vn/docs`
- `https://console-smartreader.vnpt.vn/assets/docs/danh-sach-api/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-upload-file/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-ocr/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-kie/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tu-xay-dung-mau-boc-tach-vb/vi.md`

### SmartReader Request Fields

Common SmartReader OCR/KIE JSON fields:

| Field | Type | Notes |
| --- | --- | --- |
| `token` | string | Customer/application token from VNPT docs. |
| `client_session` | string | Client session ID. |
| `file_hash` | string | Returned by `/file-service/v1/addFile`. |
| `file_type` | string | Examples include `PDF`, `JPG`, `PNG`, `HEIC`. |
| `details` | boolean | `false` for compact values, `true` for field/object detail such as bbox/confidence/warnings. |
| `exporter` | string | OCR export mode where supported: `docx`, `xlsx`, `xlsx_nsheet`, `json`. Advanced OCR docs say exporter is only supported with `details: true`. |

| Endpoint | Body contract |
| --- | --- |
| `POST /file-service/v1/addFile` | File upload body; response hash is used as `file_hash` for OCR/KIE. |
| `POST /rpa-service/aidigdoc/v1/ocr/scan` | Common OCR fields without `exporter`; basic typed-text OCR and DOCX-oriented output. |
| `POST /rpa-service/aidigdoc/v1/ocr/scan-table` | Common OCR fields plus `exporter`; table/document reconstruction output. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan` | Start async basic OCR: common fields, `details` defaults to `true` in docs, optional `exporter`. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan/result` | JSON: `session_id: string`. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan/cancel` | JSON: `session_id: string`. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan-table` | Start async advanced OCR/table: same shape as async basic, with table/export behavior. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan-table/result` | JSON: `session_id: string`. |
| `POST /rpa-service/aidigdoc/v1/integration/ocr/scan-table/cancel` | JSON: `session_id: string`. |
| `POST /rpa-service/aidigdoc/v1/ocr/van-ban-hanh-chinh` | Common KIE fields. |
| `POST /rpa-service/aidigdoc/v2/ocr/van-ban-hanh-chinh` | Common KIE fields; extended administrative-document field set. |
| `POST /rpa-service/aidigdoc/v1/ocr/dang-ky-kinh-doanh` | Common KIE fields for business registration extraction. |
| `POST /rpa-service/aidigdoc/v1/ocr/hoa-don-gtgt` | Common KIE fields for VAT invoice extraction. |
| CRUD `/template/config` | JSON includes `token`, `client_session`, `action` (`create`, `read`, `update`, `delete`), `id`, `name`, `document_id`, `file_link`, and `config` depending on action. |
| CRUD `/rpa-service/aidigdoc/template/config` | Listed in API inventory; detailed public template page uses `/template/config`. Verify with VNPT account docs before implementation. |
| `POST /rpa-service/aidigdoc/v1/llm/extraction` | Listed in API inventory only. No detailed public contract found. |

### SmartReader Response Fields

| Endpoint | Success response contract |
| --- | --- |
| `POST /file-service/v1/addFile` | `message`, `object.fileName`, `object.tokenId`, `object.description`, `object.storageType`, `object.title`, `object.uploadedDate`, `object.hash`, `object.fileType`. |
| `POST /rpa-service/aidigdoc/v1/ocr/scan` | `status`, `statusCode`, `message`, `server_version`, `object.lines`, `object.paragraphs`, `object.phrases`, `object.num_of_pages`, `object.warning_messages`, `object.warnings`; with `details=true`, text elements include bbox/confidence/font/text/type/warnings. |
| `POST /rpa-service/aidigdoc/v1/ocr/scan-table` | Same OCR wrapper plus table/document reconstruction fields and export links when `exporter` is used. |
| Async OCR start endpoints | `status`, `statusCode`, `message`, `server_version`, `object.session_id`, `object.num_of_pages`, warnings. |
| Async OCR result endpoints | Finished: `object.link`, OCR/table payload, `num_of_pages`, warnings. In progress: warning/status fields, `num_of_processed_page`, `num_of_remaining_pages`. |
| Async OCR cancel endpoints | `object.status=success`. |
| `POST /rpa-service/aidigdoc/v1/ocr/van-ban-hanh-chinh` | Administrative fields such as `category`, `left_m_cited`, `m_date`, `m_month`, `m_number`, `m_origin`, `m_year`, `num_of_pages`, warnings. |
| `POST /rpa-service/aidigdoc/v2/ocr/van-ban-hanh-chinh` | v1 fields plus extended fields such as `base`, `group`, `m_sign`, `signer_position`, recipients/publication-related fields where present. |
| `POST /rpa-service/aidigdoc/v1/ocr/dang-ky-kinh-doanh` | Business registration fields including owner/member/capital/address/registration change details. Field names in docs include `CHU_SO_HUU_*`, `DANG_KY_LAN_DAU`, `DANG_KY_THAY_DOI`, `DANH_SACH_THANH_VIEN_GOP_VON`, `DIA_CHI_TRU_SO_CHINH`. |
| `POST /rpa-service/aidigdoc/v1/ocr/hoa-don-gtgt` | Invoice fields such as `buyer_address`, `buyer_company_name`, `buyer_name`, `buyer_tax_code`, line-item `details`, `general_tax_rates`, `grand_total_after_tax`, `grand_total_after_tax_in_text`, `grand_total_before_tax`. |
| CRUD `/template/config` | `dataSign`, `dataBase64`, `logID`, `message`, `server_version`, `status`, `statusCode`, `object.name`, `object.file_link`, `object.id`, `object.document_id`, `object.config`. |

Common SmartReader error labels found: `TOKEN ID IS BLOCKED`, `ACCESS TOKEN IS INVALID`, `NO PERMISSION TO ACCESS API`, `TOKEN INVALID`, `TOKEN DEACTIVE`.

## Products Without Public Endpoint Contracts

These products were included in the scrape, but the public pages found do not expose complete request/response endpoint contracts:

| Product | Public result |
| --- | --- |
| VNPT SmartUX | Product pages and web tracking SDK scripts are public. Observed SDK methods include `track_sessions`, `track_pageview`, `track_clicks`, `track_scrolls`, `track_errors`, `track_links`, `track_forms`, `collect_from_forms`. No REST endpoint contract found. |
| VNPT SmartBot | Public pages and engine specs mention API/RAG integration. No endpoint contract found. |
| VNPT SmartVision | Product pages mention API/SDK deployment and a listed Face Camera API document filename. No public endpoint contract page found. |
| vnSocial | Product pages mention social monitoring and list an API integration document filename. No public endpoint contract page found. |
| vnFace | Public guide/spec pages cover product/admin setup. No endpoint inventory or request/response contract found publicly. |
