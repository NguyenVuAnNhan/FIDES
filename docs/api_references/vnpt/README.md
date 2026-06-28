# VNPT Public API Reference Notes

Generated: 2026-06-28

Scope: public, unauthenticated documentation and frontend bundles only. This is not a verbatim mirror of VNPT documentation; it is a local integration reference extracted from public pages, with source links preserved.

## Source Status

| Product | Public API details found | Primary sources |
| --- | --- | --- |
| VNPT eKYC | Yes. Public endpoint inventory and SDK notes are embedded in the eKYC docs frontend. | https://ekyc.vnpt.vn/admin-dashboard/en/documents/api, https://vnptai.io/ekyc/en |
| VNPT SmartVoice | Yes. Public API guide, STT/TTS/voice verification endpoints, and SDK download links are exposed. | https://smartvoice.vnpt.vn/documents/api, https://smartvoice.vnpt.vn/en/sdk, https://vnptai.io/smartvoice/en/documents/api |
| VNPT SmartReader | Yes. Public Markdown docs expose endpoint lists and integration pages. | https://console-smartreader.vnpt.vn/docs, https://vnptai.io/smartreader/en |
| VNPT SmartUX | Partial. Public product pages and web SDK scripts are exposed, but no public REST API reference was found. | https://vnptai.io/smartux/en, https://smartux.vnpt.vn/en, https://console-smartux.vnpt.vn/sdk/web/core-track.js |
| VNPT SmartBot | Partial. Public engine specs mention API/RAG integration; no endpoint reference was found. | https://vnptai.io/smartbot/en, https://vnptai.io/smartbot/en/engine-specs |
| VNPT SmartVision | Partial. Product pages and a VNPT-listed API document filename were found; no direct public endpoint page was found. | https://vnptai.io/smartvision/en, https://vnptai.io/smartvision/en/feature |
| vnSocial | Partial. Product/pricing pages and a VNPT-listed API integration document filename were found; no direct public endpoint page was found. | https://vnptai.io/vnsocial/en, https://vnptai.io/vnsocial/en/price-1 |
| vnFace | Partial. Public guide/spec pages are product/admin guidance, not API endpoint reference. | https://vnptai.io/vnface/en, https://vnptai.io/vnface/en/documents/setting, https://vnptai.io/vnface/en/specs |

Machine-readable data is in [vnpt_public_api_reference.json](vnpt_public_api_reference.json).

## Shared Authentication Pattern

The public eKYC, SmartVoice, and SmartReader API docs all use VNPT-issued token credentials. Most REST examples require these headers:

```http
Authorization: Bearer ${access_token}
Token-id: ${token_id}
Token-key: ${token_key}
Content-Type: application/json
```

Some upload APIs use file or binary bodies. Treat token values as server-side secrets. The eKYC web SDK notes explicitly warn against exposing long-lived access tokens directly in browser code.

## VNPT eKYC

Base URL found in public docs: `https://api.idg.vnpt.vn`

Public docs describe account registration, token management, SDK integration, and these endpoint paths:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/file-service/v1/addFile` | Upload image/file and receive a hash used by downstream APIs. |
| POST | `/ai/v1/classify/id` | Classify identity document type. |
| POST | `/ai/v1/card/liveness` | Check whether document/card image appears live/direct. |
| POST | `/ai/v1/ocr/id/front` | OCR front side of ID document. |
| POST | `/ai/v1/ocr/id/back` | OCR back side of ID document. |
| POST | `/ai/v1/ocr/id` | OCR full ID document flow. |
| POST | `/ai/v1/face/compare` | Compare document portrait and selfie/face image. |
| POST | `/ai/v1/face/liveness` | Face liveness check. |
| POST | `/ai/v1/face/mask` | Masked-face detection. |
| POST | `/face-service/face/add` | Add/register face. |
| POST | `/face-service/face/verify` | Verify a face against registered data. |
| POST | `/face-service/face/search` | Search registered faces. |
| POST | `/face-service/face/search-k` | K-nearest face search. |
| POST | `/aicommon-service/cic/v1/verify_face` | CIC face verification flow. |
| POST | `/aicommon-service/cic/v1/verify_customer` | CIC customer verification flow. |

Public SDK docs found in the same frontend bundle:

| SDK | Notes |
| --- | --- |
| Android | Full flow, OCR-only flows, compare/liveness/add/verify flows; default base URL is `https://api.idg.vnpt.vn`. |
| iOS | Similar ID card scanner flows; uses supplied token key, token ID, username/password, authorization, and optional base URL. |
| Web | eKYC web integration notes include `BACKEND_URL` and recommend backend-mediated token handling. |

VNPT-listed customer document names found in product source include:

- `VNPTeKYC_Mo ta_API_v1.6_2025_guiKH (2).xlsx`
- `[VNPT][Android] Huong dan tich hop SDK eKYC v3.6.9.docx`
- `[VNPT][iOS] Huong dan tich hop SDK eKYC v3.6.7.docx`
- `API he thong ID Check identify-service RAR 10032026.docx`
- `eKYC_Tu dien ma loi_SPDV.xlsx`

## VNPT SmartVoice

Base URL found in public docs: `https://api.idg.vnpt.vn`

### Text To Speech

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth-service/oauth/token` | OAuth/token flow. VNPT text renders this with an extra space in one place as `/auth-service /oauth/token`; normalize before use. |
| POST | `/ai/api/v1/text-to-speech` | Advanced TTS request. |
| GET or POST | `/ai/api/v1/text-to-speech/check-status` | Check TTS processing status. Method should be verified against account docs before implementation. |
| GET or POST | `/ai/api/v1/text-to-speech/download` | Download generated audio. Method should be verified against account docs before implementation. |
| POST | `/tts-service/v1/standard` | Standard TTS REST flow. |
| GET or POST | `/tts-service/v1/check-status` | Check standard TTS status. |
| POST | `/tts-service/v2/standard` | TTS v2 standard REST flow. |
| POST | `/tts-service/v2/grpc` | TTS over REST wrapper for gRPC model. |

gRPC service names found: `SynthesizeSpeechResponse Synthesize(SynthesizeSpeechRequest)` and `stream SynthesizeSpeechResponse SynthesizeOnline(SynthesizeSpeechRequest)`.

### Speech To Text

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/stt-service/v1/grpc/standard` | Speech-to-text using gRPC model through API. |
| POST | `/stt-service/v1/grpc/async/standard` | Async gRPC STT flow. |
| POST | `/stt-service/v3/standard` | STT standard REST flow. |
| GET or POST | `/stt-service/v1/async/status` | Check async STT status. |
| POST | `/stt-service/v1/async/vn` | Async Vietnamese STT flow. |
| WebSocket | `wss://websocket.vnpt.vn/v1/streaming-recognize?authorization=<accessToken>&token-id=<token-id>&token-key=<token-key>` | Streaming recognition. Vendor text includes a stray space before `token-key`; remove it. |

gRPC service names found: `Recognize(RecognizeRequest)` and `StreamingRecognize(stream StreamingRecognizeRequest)`.

### Voice Verification

Voice verification uses the voice-service base in the public guide:

`https://api.idg.vnpt.vn/voice-service`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/voice-id/audio/upload` | Upload voice/audio sample. |
| POST | `/v1/voice-id/audio/encode` | Encode/register voice audio. |
| GET | `/v1/voice-id/audio/unregister?email=<email>` | Unregister voice by email. |
| POST | `/v1/voice-id/audio/search-by-upload` | Search by uploaded audio. |
| GET | `/v1/voice-id/audio/info-by-email?email=<email>` | Get voice enrollment info by email. |
| GET or POST | `/voiceid/api/v1/audio/verify` | Verify two audio samples or audio IDs. |

Public SDK download URLs exposed by the SDK page:

- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_IOS_STT_RestAPI.zip
- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_Android_STT_RestAPI.zip
- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_Web_STT_RestAPI.zip
- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_IOS_STT_gRPC.zip
- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_Android_STT_gRPC.zip
- https://smartvoice.vnpt.vn/sdk-download/VNPTSmartVoice_SDK_Web_TTS_RestAPI.zip

## VNPT SmartReader

Base URL found in public docs: `https://api.idg.vnpt.vn`

Public Markdown pages found:

- `https://console-smartreader.vnpt.vn/assets/docs/danh-sach-api/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/chuan-bi/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-upload-file/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-ocr/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tich-hop-api-kie/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/tu-xay-dung-mau-boc-tach-vb/vi.md`
- `https://console-smartreader.vnpt.vn/assets/docs/cac-loi-thuong-gap/vi.md`

Endpoint inventory:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/file-service/v1/addFile` | Upload file and receive hash/token for OCR/KIE APIs. |
| POST | `/rpa-service/aidigdoc/v1/ocr/scan` | Basic OCR; exports DOCX. |
| POST | `/rpa-service/aidigdoc/v1/ocr/scan-table` | Advanced OCR/table reconstruction; exports DOCX, XLSX, JSON. |
| POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan` | Start async basic OCR session. |
| GET or POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan/result` | Check async basic OCR session result. |
| POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan/cancel` | Cancel async basic OCR session. |
| POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan-table` | Start async advanced OCR/table session. |
| GET or POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan-table/result` | Check async advanced OCR/table result. |
| POST | `/rpa-service/aidigdoc/v1/integration/ocr/scan-table/cancel` | Cancel async advanced OCR/table session. |
| POST | `/rpa-service/aidigdoc/v1/ocr/van-ban-hanh-chinh` | Extract administrative document fields. |
| POST | `/rpa-service/aidigdoc/v2/ocr/van-ban-hanh-chinh` | Extract administrative document fields, extended-field version. |
| POST | `/rpa-service/aidigdoc/v1/ocr/dang-ky-kinh-doanh` | Extract business registration document fields. |
| POST | `/rpa-service/aidigdoc/v1/ocr/hoa-don-gtgt` | Extract VAT invoice fields. |
| CRUD | `/template/config` | Template create/read/update/delete in detailed docs. |
| CRUD | `/rpa-service/aidigdoc/template/config` | Template config path listed in the API list; differs from detailed docs. |
| POST | `/rpa-service/aidigdoc/v1/llm/extraction` | LLM extraction endpoint listed in API list. Detailed public integration page not found in this pass. |

Common SmartReader error labels found include `TOKEN ID IS BLOCKED`, `ACCESS TOKEN IS INVALID`, `NO PERMISSION TO ACCESS API`, `TOKEN INVALID`, and `TOKEN DEACTIVE`.

## SmartUX

Public product pages describe SmartUX as a web/mobile UX analytics product with heatmaps, click/scroll/form/error tracking, session tracking, and user-flow analytics. The public VNPT AI page embeds the web SDK script:

```html
<script src="https://console-smartux.vnpt.vn/sdk/web/core-track.js"></script>
<script src="https://console-smartux.vnpt.vn/sdk/web/minify.min.js"></script>
```

The product page initializes the SDK with an `app_key`, `url`, and queued methods such as:

- `track_sessions`
- `track_pageview`
- `track_clicks`
- `track_scrolls`
- `track_errors`
- `track_links`
- `track_forms`
- `collect_from_forms`

No public REST API reference or endpoint list was found.

VNPT-listed customer document names found in product source:

- `VNPT SmartUX_GTSP_ForPublic_310326_V1.0.pdf`
- `VNPT SmartUX_TNSP_ForPublic_310326_V1.0.pdf`
- `VNPT SmartUX_KHSP_ForPublic_310326_V1.0.pdf`

## SmartBot

Public VNPT AI pages describe SmartBot as an AI assistant/chatbot platform. Engine specs mention API integration and RAG integration capability, but no public endpoint reference was found.

VNPT-listed customer document names found in product source:

- `VNPT Smartbot_GTSP_Tong quan san pham_20260330_V1.0.docx`
- `VNPT Smartbot_GTSP_Tinh nang_20260330_V1.0.docx`
- `VNPT Smartbot_GTSP_Khach hang_20260330_V1.0.docx`

## SmartVision

Public pages describe document digitization, content detection, and face camera/AI camera related capabilities. A VNPT-listed API document filename was found, but no direct public endpoint page was found.

VNPT-listed customer document names found in product source:

- `VNPT SmartVision_TNSP_Tai lieu API Face Camera_20260327_V1.0.docx`
- `VNPT SmartVision_TNSP_Tai lieu HDSD Face Camera_20260327_V1.0.docx`
- `VNPT SmartVision_TNSP_Tieu chuan ky thuat Face Camera_20260327_V1.0.docx`
- `VNPT SmartVision_TNSP_Tai lieu HDSD CONTENT DETECTION_20260327_V1.0.docx`
- `VNPT SmartVision_GTSP_ForPublic_20260327_V1.0.pdf`

## vnSocial

Public pages describe social monitoring/analytics. The VNPT AI source lists an API integration document filename, but no direct public endpoint page was found.

VNPT-listed customer document names found in product source:

- `vnSocial - Tai lieu API tich hop he thong v2.docx`
- `vnSocial_GTSP_Gioi thieu_20260327_V1.0.docx`
- `vnSocial_GTSP_Tinh nang_20260327_V1.0.docx`
- `vnSocial_GTSP_Khach hang_20260327_V1.0.docx`

## vnFace

Public documents found:

- `https://vnptai.io/vnface/en/documents/setting`
- `https://vnptai.io/vnface/en/specs`

The public guide is a quick-start/admin operating guide for account registration, web admin, deploying vnFace, and logging in to attendance devices. It does not expose an API endpoint inventory. Product pages mention API support for retrieval/integration, but the detailed API spec appears to require customer/contact access.

Public console/product links observed:

- https://console-vnface.vnpt.vn
- https://console-vnface.vnpt.vn/en/auth/login
- https://vnface.vnpt.vn/en/account/register

VNPT-listed customer document names found in product source:

- `VNPT_vnFace_GTSP_GioiThieuSanPham_V2.docx`
- `vnFace_TNSP_ForPublic_20260327_V1.0.docx`
- `VNPT vnFace_TNSP_Huong dan su dung Web quan tri vnFace_20260327_V2.0.docx`
- `VNPT vnFace_TNSP_Tai lieu dac ta yeu cau phan mem_20260327_V1.0.docx`
