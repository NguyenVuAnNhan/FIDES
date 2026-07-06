# FIDES

Nền tảng AI cho ngân hàng hiện đại, gồm hai module MVP:

| Module | Mô tả |
|--------|--------|
| **FIDES Shield** | Circuit breaker phát hiện lừa đảo khi chuyển khoản (Path B: eKYC + STT + Smartbot) |
| **FIDES Grow** | Phân tích hóa đơn → hồ sơ tín dụng thay thế (OCR + Neo4j + LightGBM) |

Stack: **FastAPI** backend, frontend tĩnh (`frontend/static/`), SDK web/mobile.

---

## Yêu cầu

- Python 3.10+
- (Khuyến nghị) Docker — chạy Neo4j trust graph
- (Tùy chọn) Android SDK — build app mẫu `sdks/mobile/`
- Credentials VNPT — eKYC, SmartVoice, Smartbot, SmartVision, SmartReader (xem `.env.example`)

---

## Cài đặt

### Cách nhanh (khuyến nghị)

```bash
./scripts/bootstrap.sh
```

Script sẽ: tạo `.venv`, cài dependencies, tạo `.env` từ `.env.example`, sinh receipt fixtures, train model Grow, khởi động Neo4j (nếu có Docker), chạy smoke tests và mở server tại http://127.0.0.1:8000.

Chỉ setup, không chạy server:

```bash
./scripts/bootstrap.sh --no-run
```

### Cài đặt thủ công

```bash
# 1. Clone và vào thư mục dự án
cd FIDES

# 2. Virtualenv + dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt

# 3. Biến môi trường
cp .env.example .env
# Chỉnh sửa .env — điền VNPT_* tokens (không commit file này)

# 4. Dữ liệu demo
python scripts/generate_receipt_fixtures.py
python scripts/train_grow_credit_model.py

# 5. (Tùy chọn) Neo4j trust graph
docker compose up neo4j -d
# Bật NEO4J_ENABLED=true trong .env, rồi:
python scripts/init_neo4j_schema.py
python scripts/seed_grow_graph.py
python scripts/train_grow_credit_model.py

# 6. Chạy server
uvicorn backend.app.main:app --reload
```

Mở trình duyệt: http://127.0.0.1:8000

| Trang | URL |
|-------|-----|
| Grow (mặc định) | `/grow` |
| Shield | `/shield` |
| Call Listen (Path A) | `/call` |
| API docs | `/docs` |

---

## Cấu hình

Sao chép `.env.example` → `.env`. Các nhóm biến chính:

```bash
# VNPT — mỗi sản phẩm có token riêng hoặc dùng VNPT_ACCESS_TOKEN chung
VNPT_EKYC_MODE=real
VNPT_SMARTVOICE_MODE=real
VNPT_SMARTBOT_MODE=real
VNPT_SMARTVISION_MODE=real
VNPT_SMARTREADER_MODE=real

# Neo4j — Grow trust graph
NEO4J_ENABLED=false
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=fides-dev-password
```

- Không có credentials VNPT → Shield challenge đánh dấu bước đó failed/skipped (không có mock offline).
- Neo4j browser: http://localhost:7474 (`neo4j` / `fides-dev-password`).
- Chi tiết adapter VNPT: [`docs/vnpt_provider_adapter.md`](docs/vnpt_provider_adapter.md).

---

## Cấu trúc dự án

```
backend/app/
  routes/          # API: shield, grow, demo, health
  services/        # Logic: shield, grow, OCR, VNPT, ML, graph
  data/            # Demo dataset, model LightGBM
frontend/static/   # UI web (shield, grow, call)
sdks/
  web/             # JavaScript SDK
  mobile/          # Android/iOS SDK + sample-banking-app
scripts/           # Bootstrap, train, smoke tests
docs/              # Schema & tích hợp chi tiết
```

**Luồng Grow:** SmartReader OCR → ledger → Neo4j trust graph → LightGBM + SHAP.

**Luồng Shield Path B:** analyze → live camera clip (~4s) → eKYC/SmartVision + SmartVoice STT + Smartbot + voice stress.

**Luồng Shield Path A (Call Listen):** upload audio cuộc gọi → STT + Smartbot → cảnh báo scam.

---

## API chính

| Endpoint | Mô tả |
|----------|--------|
| `GET /api/health` | Health check |
| `POST /api/shield/analyze` | Phân tích giao dịch (stage 1) |
| `POST /api/shield/challenge` | Challenge sau live check (stage 2) |
| `POST /api/shield/challenge/upload-live-check` | Upload clip camera + mic (Path B) |
| `POST /api/shield/call-listen` | Phân tích audio cuộc gọi (Path A) |
| `POST /api/grow/upload-receipt` | Upload ảnh hóa đơn |
| `POST /api/grow/process-invoice` | OCR + chấm điểm tín dụng |
| `GET /api/demo/dataset` | Dataset demo Shield + Grow |

---

## SDK & app mobile

- Web SDK: `sdks/web/`
- Mobile SDK: `sdks/mobile/` — xem [`sdks/mobile/README.md`](sdks/mobile/README.md)

Build app mẫu Android (Jetpack Compose):

```bash
cd sdks/mobile
./gradlew :sample-banking-app:installDebug
```

Lần đầu trên macOS: `brew install --cask android-commandlinetools android-platform-tools`, rồi `./setup_android.sh`.

Backend phải chạy với `--host 0.0.0.0` để emulator truy cập qua `http://10.0.2.2:8000`.

---

## Kiểm thử nhanh

```bash
source .venv/bin/activate

# Parser (không cần VNPT)
python scripts/test_receipt_parser.py
python scripts/smoke_grow_ml.py

# VNPT (cần credentials trong .env)
python scripts/smoke_vnpt_smartreader.py
python scripts/smoke_vnpt_ekyc.py
python scripts/smoke_vnpt_smartvoice.py
```

---

## Tài liệu chi tiết

| Chủ đề | File |
|--------|------|
| Shield scam schema | [`docs/scam_schema_explained.md`](docs/scam_schema_explained.md) |
| Grow schema | [`docs/grow_schema_explained.md`](docs/grow_schema_explained.md) |
| Neo4j trust graph | [`docs/grow_trust_graph_neo4j_plan.md`](docs/grow_trust_graph_neo4j_plan.md) |
| SDK design | [`docs/sdk_scaffold.md`](docs/sdk_scaffold.md) |
| Mock data inventory | [`docs/mock_data_inventory.md`](docs/mock_data_inventory.md) |
