#!/usr/bin/env python3
"""Generate deterministic madlib-style synthetic FIDES demo data."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_SEED = 20260628
DEFAULT_COUNT = 1000
DEFAULT_OUTPUT = Path("backend/app/data/synthetic_demo_dataset.json")

FIRST_NAMES = [
    "An",
    "Binh",
    "Chi",
    "Dung",
    "Giang",
    "Hanh",
    "Khoa",
    "Lan",
    "Minh",
    "Nam",
    "Phuc",
    "Quang",
    "Thao",
    "Trang",
    "Tuan",
    "Vy",
]

LAST_NAMES = [
    "Nguyen",
    "Tran",
    "Le",
    "Pham",
    "Hoang",
    "Phan",
    "Vu",
    "Dang",
    "Bui",
    "Do",
]

BUSINESS_PREFIXES = [
    "An Nhien",
    "Bep Nha",
    "Hoa Sen",
    "Minh Phu",
    "Nam Phuong",
    "Song Xanh",
    "Thanh Tam",
    "Viet Tin",
]

BUSINESS_TYPES = [
    "Coffee",
    "Mini Mart",
    "Packaging",
    "Foods",
    "Devices",
    "Textiles",
    "Logistics",
    "Bakery",
]

CUSTOMER_NAMES = [
    "Office Pantry Co.",
    "District Repair Network",
    "Local Wholesale Buyer",
    "Co-working Lunch Club",
    "Community School",
    "Hotel Supply Desk",
    "Neighborhood Retail Group",
    "Factory Canteen",
]

SHIELD_TEMPLATES = {
    "fake_authority": {
        "titles": [
            "Fake police verification",
            "Fake prosecutor transfer request",
            "Authority impersonation call",
        ],
        "personas": ["Retail banking customer", "Senior customer", "First-time digital banking user"],
        "caller_types": ["unknown", "voip", "international"],
        "amount_range": (45_000_000, 120_000_000),
        "recipient_names": ["Nguyen Van A", "Tran Bao Long", "Le Minh Duc", "Pham Quoc Huy"],
        "transcripts": [
            "Toi la {agency}. Tai khoan cua ban lien quan {case_type}. Hay chuyen tien de xac minh va giu bi mat.",
            "Ben {agency} dang dieu tra {case_type}. Anh chi can chuyen tien vao tai khoan nay de xac minh.",
            "Day la lenh bao mat tu {agency}. Khong duoc noi voi ai va phai chuyen tien ngay de phong toa rui ro.",
        ],
        "tokens": {
            "agency": ["cong an", "vien kiem sat", "co quan dieu tra"],
            "case_type": ["vu an rua tien", "vu an lua dao", "ho so tin dung bat thuong"],
        },
    },
    "otp_theft": {
        "titles": ["OTP theft coaching", "Security support OTP request", "Wallet unlock OTP call"],
        "personas": ["Digital wallet user", "Mobile banking user", "New eKYC customer"],
        "caller_types": ["voip", "unknown"],
        "amount_range": (35_000_000, 90_000_000),
        "recipient_names": ["Tai khoan ho tro bao mat", "Trung tam khoa giao dich", "Bo phan xac minh"],
        "transcripts": [
            "De khoa giao dich la, anh chi doc ma OTP vua nhan duoc. Ma xac thuc nay chi dung de bao ve tai khoan.",
            "He thong dang loi. Vui long doc ma OTP va ma xac thuc de chung toi huy giao dich treo.",
            "Nhan vien ngan hang can OTP de xac minh chu tai khoan. Anh chi doc ma trong tin nhan ngay bay gio.",
        ],
        "tokens": {},
    },
    "investment": {
        "titles": ["Guaranteed investment return", "High-yield trading offer", "Urgent private investment slot"],
        "personas": ["Young investor", "Freelancer", "Savings customer"],
        "caller_types": ["unknown", "voip"],
        "amount_range": (20_000_000, 80_000_000),
        "recipient_names": ["Cong ty Dau Tu Sao Viet", "Quy Loi Nhuan 30", "San Giao Dich Alpha"],
        "transcripts": [
            "Goi dau tu nay cam ket loi nhuan {return_rate} phan tram moi thang. Neu chuyen tien hom nay se duoc uu tien.",
            "Co hoi dau tu noi bo chi mo trong ngay. Cam ket loi nhuan cao va rut von bat cu luc nao.",
            "Chuyen tien vao goi dau tu de giu cho. Loi nhuan duoc cam ket va co chuyen gia ho tro rieng.",
        ],
        "tokens": {"return_rate": ["20", "25", "30", "35"]},
    },
    "remote_support": {
        "titles": ["Remote support payment", "Screen-sharing support scam", "Fake technical help transfer"],
        "personas": ["Mobile banking user", "Small business owner", "Older customer"],
        "caller_types": ["voip", "unknown"],
        "amount_range": (15_000_000, 65_000_000),
        "recipient_names": ["Trung Tam Ho Tro Thiet Bi", "Dich Vu Bao Mat Tu Xa", "Ho Tro Ngan Hang Online"],
        "transcripts": [
            "Anh chi mo ung dung dieu khien man hinh de toi sua loi. Sau do chuyen tien kiem tra va toi se hoan lai.",
            "Tai khoan bi treo vi ung dung la. Hay chia se man hinh va chuyen mot khoan xac minh.",
            "Can cai cong cu ho tro tu xa de bao ve tai khoan. Sau khi cai xong hay chuyen tien test he thong.",
        ],
        "tokens": {},
    },
    "legitimate_supplier": {
        "titles": ["Known supplier payment", "Routine invoice settlement", "Verified business transfer"],
        "personas": ["Household business owner", "SME accountant", "Store manager"],
        "caller_types": ["trusted"],
        "amount_range": (3_000_000, 28_000_000),
        "recipient_names": ["Minh Phu Packaging", "Hoa Sen Foods", "Song Xanh Logistics", "Viet Tin Supplies"],
        "transcripts": [
            "Thanh toan hoa don {supply_type} thang {month} theo hop dong da doi soat.",
            "Chuyen tien cho nha cung cap quen thuoc theo lich thanh toan dinh ky.",
            "Tra tien don hang da nhan va co hoa don dien tu kem theo.",
        ],
        "tokens": {
            "supply_type": ["bao bi", "nguyen lieu", "van chuyen", "thiet bi"],
            "month": ["4", "5", "6", "7"],
        },
    },
}

GROW_TEMPLATES = {
    "strong_business": {
        "titles": ["Strong invoice-backed profile", "Stable merchant revenue", "On-time B2B invoice"],
        "business_stages": ["Established household business", "Growing SME"],
        "total_range": (24_000_000, 95_000_000),
        "paid_on_time": True,
        "item_sets": [
            ["Monthly supply", "Delivery and handling"],
            ["Catering package", "Recurring service fee"],
            ["Replacement parts", "Maintenance package", "Shipping"],
        ],
    },
    "emerging_thin_file": {
        "titles": ["Emerging thin-file business", "Newly digitized invoice", "First structured sales record"],
        "business_stages": ["Newly digitized household business", "Thin-file merchant"],
        "total_range": (6_000_000, 18_000_000),
        "paid_on_time": True,
        "item_sets": [["Goods and delivery"], ["Retail order"], ["Food boxes"]],
    },
    "late_payment": {
        "titles": ["Late-payment invoice", "Delayed customer settlement", "Cashflow pressure invoice"],
        "business_stages": ["Thin-file retailer", "Seasonal household business"],
        "total_range": (18_000_000, 55_000_000),
        "paid_on_time": False,
        "item_sets": [["Packaged goods"], ["Wholesale stock"], ["Equipment rental"]],
    },
    "seasonal_cashflow": {
        "titles": ["Seasonal cashflow spike", "Holiday inventory invoice", "Short-term working capital need"],
        "business_stages": ["Seasonal merchant", "Growing household business"],
        "total_range": (16_000_000, 70_000_000),
        "paid_on_time": True,
        "item_sets": [["Holiday inventory", "Temporary staff"], ["Seasonal supplies"], ["Event order", "Delivery"]],
    },
    "high_volume": {
        "titles": ["High-volume reseller invoice", "Large repeat buyer invoice", "Working-capital ready merchant"],
        "business_stages": ["Growing SME", "Established merchant"],
        "total_range": (70_000_000, 160_000_000),
        "paid_on_time": True,
        "item_sets": [
            ["Device stock", "Accessories", "Repair kits"],
            ["Bulk packaged goods", "Warehouse delivery"],
            ["Textile order", "Finishing service", "Transport"],
        ],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Total records across Shield and Grow.")
    parser.add_argument("--shield-count", type=int, default=None)
    parser.add_argument("--grow-count", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    shield_count, grow_count = resolve_counts(args.count, args.shield_count, args.grow_count)
    rng = random.Random(args.seed)
    dataset = build_dataset(rng, args.seed, shield_count, grow_count)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"Wrote {shield_count + grow_count} records "
        f"({shield_count} Shield, {grow_count} Grow) to {args.output}"
    )


def resolve_counts(total: int, shield_count: int | None, grow_count: int | None) -> tuple[int, int]:
    if total <= 0:
        raise SystemExit("--count must be positive")

    if shield_count is None and grow_count is None:
        return total // 2, total - (total // 2)

    if shield_count is None:
        shield_count = total - int(grow_count)
    if grow_count is None:
        grow_count = total - int(shield_count)

    if shield_count < 0 or grow_count < 0:
        raise SystemExit("shield/grow counts cannot be negative")
    if shield_count + grow_count != total:
        raise SystemExit("shield-count + grow-count must equal count")

    return shield_count, grow_count


def build_dataset(rng: random.Random, seed: int, shield_count: int, grow_count: int) -> dict[str, Any]:
    shield_categories = list(SHIELD_TEMPLATES)
    grow_categories = list(GROW_TEMPLATES)

    shield_scenarios = [
        build_shield_scenario(rng, index + 1, shield_categories[index % len(shield_categories)])
        for index in range(shield_count)
    ]
    grow_invoices = [
        build_grow_invoice(rng, index + 1, grow_categories[index % len(grow_categories)])
        for index in range(grow_count)
    ]

    return {
        "version": "synthetic-madlib-v1",
        "seed": seed,
        "total_records": shield_count + grow_count,
        "shield_count": shield_count,
        "grow_count": grow_count,
        "category_counts": {
            "shield": count_categories(shield_scenarios),
            "grow": count_categories(grow_invoices),
        },
        "shield_scenarios": shield_scenarios,
        "grow_invoices": grow_invoices,
    }


def build_shield_scenario(rng: random.Random, index: int, category: str) -> dict[str, Any]:
    template = SHIELD_TEMPLATES[category]
    amount = round_to_nearest(rng.randint(*template["amount_range"]), 100_000)
    transcript = render_template(rng.choice(template["transcripts"]), template.get("tokens", {}), rng)
    recipient_name = rng.choice(template["recipient_names"])
    caller_type = rng.choice(template["caller_types"])
    active_call = category != "legitimate_supplier"
    recipient_known = category == "legitimate_supplier"
    remote_control_detected = category == "remote_support"
    consent_granted = active_call
    llm_scam_type = None if category == "legitimate_supplier" else category
    coercion_signals = make_coercion_signals(rng, category) if consent_granted else empty_coercion_signals()

    return {
        "id": f"synthetic-shield-{index:04d}",
        "category": category,
        "title": rng.choice(template["titles"]),
        "persona": rng.choice(template["personas"]),
        "demo_goal": "Synthetic madlib case for volume testing and dashboard demos.",
        "expected_band": expected_shield_band(category),
        "payload": {
            "transaction_amount": amount,
            "recipient_name": recipient_name,
            "recipient_account": make_account(rng),
            "active_call": active_call,
            "caller_type": caller_type,
            "caller_number": make_caller_number(rng, caller_type, category),
            "recipient_known": recipient_known,
            "recipient_phone": make_recipient_phone(rng),
            **make_recipient_intelligence(rng, category),
            "remote_control_detected": remote_control_detected,
            **make_native_telemetry_signals(rng, category),
            "consent_granted": consent_granted,
            "audio_source": make_audio_source(category, index) if consent_granted else None,
            "stt_transcript": transcript if consent_granted else "",
            "stt_confidence": make_confidence(rng, 0.86, 0.98) if consent_granted else None,
            "detected_patterns": detected_patterns_for_category(category),
            "llm_scam_type": llm_scam_type,
            "llm_confidence": make_confidence(rng, 0.78, 0.96) if llm_scam_type else None,
            **coercion_signals,
            "transcript": transcript,
        },
    }


def build_grow_invoice(rng: random.Random, index: int, category: str) -> dict[str, Any]:
    template = GROW_TEMPLATES[category]
    total = round_to_nearest(rng.randint(*template["total_range"]), 100_000)
    business_name = f"{rng.choice(BUSINESS_PREFIXES)} {rng.choice(BUSINESS_TYPES)}"
    item_names = rng.choice(template["item_sets"])
    items = split_items(total, item_names)
    invoice_id = f"INV-2026-{index:04d}"
    customer_name = rng.choice(CUSTOMER_NAMES)
    input_mode = "voice_entry" if category == "seasonal_cashflow" and index % 2 == 0 else "invoice_photo"
    input_source = (
        make_grow_voice_source(index)
        if input_mode == "voice_entry"
        else f"mock://receipts/synthetic-grow-{index:04d}.png"
    )
    issue_date = f"2026-06-{(index % 28) + 1:02d}"

    return {
        "id": f"synthetic-grow-{index:04d}",
        "category": category,
        "title": rng.choice(template["titles"]),
        "business_stage": rng.choice(template["business_stages"]),
        "demo_goal": "Synthetic madlib invoice for volume testing and dashboard demos.",
        "expected_band": expected_grow_band(category),
        "payload": {
            "business_id": make_business_id(business_name),
            "input_mode": input_mode,
            "input_source": input_source,
            "business_name": business_name,
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "invoice_total": total,
            "paid_on_time": template["paid_on_time"],
            "items": items,
            "ocr": make_ocr_payload(input_mode, invoice_id, business_name, customer_name, issue_date, total, items, rng),
            "voice_entry": make_voice_entry_payload(input_mode, input_source, total, customer_name, issue_date, rng),
            "normalized_ledger_entry": make_ledger_entry(
                invoice_id,
                input_mode,
                customer_name,
                total,
                issue_date,
                category,
                confidence=0.9 if input_mode == "invoice_photo" else 0.86,
            ),
        },
    }


def split_items(total: int, item_names: list[str]) -> list[dict[str, Any]]:
    if len(item_names) == 1:
        return [{"description": item_names[0], "quantity": 1, "unit_price": total, "amount": total}]

    remaining = total
    items = []
    for index, item_name in enumerate(item_names):
        if index == len(item_names) - 1:
            amount = remaining
        else:
            amount = round_to_nearest(total // len(item_names), 100_000)
            remaining -= amount
        items.append({"description": item_name, "quantity": 1, "unit_price": amount, "amount": amount})
    return items


def make_business_id(business_name: str) -> str:
    return "biz_" + business_name.lower().replace(" ", "_").replace(".", "")


def make_grow_voice_source(index: int) -> str:
    return f"mock://audio/grow-voice-{index:04d}.wav"


def make_ocr_payload(
    input_mode: str,
    invoice_id: str,
    business_name: str,
    customer_name: str,
    issue_date: str,
    total: int,
    items: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any]:
    if input_mode != "invoice_photo":
        return {
            "provider": "SmartReader",
            "status": "not_used",
            "confidence": None,
            "extracted_fields": None,
        }

    return {
        "provider": "SmartReader",
        "status": "completed",
        "confidence": make_confidence(rng, 0.86, 0.96),
        "extracted_fields": {
            "invoice_id": invoice_id,
            "seller_name": business_name,
            "buyer_name": customer_name,
            "issue_date": issue_date,
            "due_date": "2026-07-05",
            "total_amount": total,
            "tax_amount": round(total / 11),
            "currency": "VND",
            "line_items": items,
        },
    }


def make_voice_entry_payload(
    input_mode: str,
    input_source: str,
    total: int,
    customer_name: str,
    issue_date: str,
    rng: random.Random,
) -> dict[str, Any]:
    if input_mode != "voice_entry":
        return {
            "provider": "SmartVoice",
            "status": "not_used",
            "audio_source": None,
            "transcript": "",
            "confidence": None,
            "parsed_fields": None,
        }

    transcript = (
        f"Hom nay ghi nhan doanh thu {total:,} dong tu khach hang {customer_name}, "
        "phan loai doanh thu ban hang."
    )
    return {
        "provider": "SmartVoice",
        "status": "completed",
        "audio_source": input_source,
        "transcript": transcript,
        "confidence": make_confidence(rng, 0.82, 0.94),
        "parsed_fields": {
            "transaction_type": "sale",
            "amount": total,
            "description": customer_name,
            "transaction_date": issue_date,
            "category": "sales_revenue",
        },
    }


def make_ledger_entry(
    invoice_id: str,
    input_mode: str,
    customer_name: str,
    total: int,
    issue_date: str,
    category: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "entry_id": "ledger_" + invoice_id.lower().replace("-", "_"),
        "source_type": input_mode,
        "transaction_type": "sale",
        "counterparty_name": customer_name,
        "amount": total,
        "currency": "VND",
        "transaction_date": issue_date,
        "category": category,
        "confidence": confidence,
    }


def render_template(template: str, tokens: dict[str, list[str]], rng: random.Random) -> str:
    rendered = template
    for key, values in tokens.items():
        rendered = rendered.replace("{" + key + "}", rng.choice(values))
    return rendered


def make_account(rng: random.Random) -> str:
    return f"9704 {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"


def make_caller_number(rng: random.Random, caller_type: str, category: str) -> str:
    if caller_type == "trusted":
        return f"+84 {rng.randint(900, 989)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
    if caller_type == "international":
        return rng.choice(
            [
                f"+65 {rng.randint(6000, 9999)} {rng.randint(1000, 9999)}",
                f"+855 {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                f"+882 {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
            ]
        )
    if caller_type == "voip":
        return rng.choice(
            [
                f"+882 {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                f"+883 {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                f"1900 {rng.randint(100, 999)} {rng.randint(100, 999)}",
            ]
        )
    if category in {"fake_authority", "remote_support"}:
        return rng.choice(
            [
                f"+882 {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
                f"1900 {rng.randint(100, 999)} {rng.randint(100, 999)}",
            ]
        )
    return f"+84 {rng.randint(700, 899)} {rng.randint(100, 999)} {rng.randint(100, 999)}"


def make_recipient_phone(rng: random.Random) -> str:
    return f"+84 {rng.randint(900, 989)} {rng.randint(100, 999)} {rng.randint(100, 999)}"


def make_recipient_intelligence(rng: random.Random, category: str) -> dict[str, Any]:
    specs = {
        "fake_authority": {
            "reports": (18, 45),
            "keywords": ["cong an", "xac minh tai khoan", "chuyen tien", "vu an"],
            "simo": ["not_listed", "watchlisted"],
            "graph": (0.78, 0.96),
            "patterns": ["fan_in_fan_out", "rapid_pass_through"],
            "inbound": (9, 22),
            "outbound": (5, 15),
            "pass_through": (1.5, 6.0),
            "age": (1, 14),
            "cluster": (2, 9),
            "risk_level": "critical",
            "moved": True,
        },
        "otp_theft": {
            "reports": (5, 18),
            "keywords": ["otp", "ma xac thuc", "khoa giao dich"],
            "simo": ["not_listed", "watchlisted"],
            "graph": (0.62, 0.86),
            "patterns": ["rapid_pass_through", "fan_in"],
            "inbound": (5, 13),
            "outbound": (3, 9),
            "pass_through": (3.0, 10.0),
            "age": (3, 30),
            "cluster": (1, 6),
            "risk_level": "elevated",
            "moved": True,
        },
        "investment": {
            "reports": (1, 9),
            "keywords": ["dau tu", "loi nhuan cao", "cam ket"],
            "simo": ["not_listed"],
            "graph": (0.35, 0.68),
            "patterns": ["new_account_high_activity", "fan_in"],
            "inbound": (2, 8),
            "outbound": (0, 4),
            "pass_through": (8.0, 40.0),
            "age": (7, 90),
            "cluster": (0, 3),
            "risk_level": "elevated",
            "moved": False,
        },
        "remote_support": {
            "reports": (10, 28),
            "keywords": ["ho tro tu xa", "chia se man hinh", "hoan tien"],
            "simo": ["not_listed", "watchlisted"],
            "graph": (0.7, 0.92),
            "patterns": ["fan_in_fan_out", "rapid_pass_through"],
            "inbound": (7, 18),
            "outbound": (5, 13),
            "pass_through": (2.0, 8.0),
            "age": (1, 21),
            "cluster": (2, 8),
            "risk_level": "critical",
            "moved": True,
        },
        "legitimate_supplier": {
            "reports": (0, 0),
            "keywords": [],
            "simo": ["not_listed"],
            "graph": (0.02, 0.18),
            "patterns": ["trusted_supplier_history"],
            "inbound": (0, 2),
            "outbound": (0, 2),
            "pass_through": None,
            "age": (180, 1400),
            "cluster": (0, 1),
            "risk_level": "low",
            "moved": False,
        },
    }
    spec = specs[category]
    pass_through = None
    if spec["pass_through"]:
        pass_through = make_confidence(rng, *spec["pass_through"])
    return {
        "vn_social_report_count": rng.randint(*spec["reports"]),
        "vn_social_recent_keywords": sample_labels(rng, spec["keywords"]) if spec["keywords"] else [],
        "simo_status": rng.choice(spec["simo"]),
        "simo_last_checked_at": "2026-06-28T10:00:00Z",
        "graph_risk_score": make_confidence(rng, *spec["graph"]),
        "graph_pattern": rng.choice(spec["patterns"]),
        "inbound_sender_count_10m": rng.randint(*spec["inbound"]),
        "outbound_account_count_10m": rng.randint(*spec["outbound"]),
        "median_pass_through_minutes": pass_through,
        "account_age_days": rng.randint(*spec["age"]),
        "shared_device_cluster_size": rng.randint(*spec["cluster"]),
        "funds_moved_within_minutes": spec["moved"],
        "recipient_risk_level": spec["risk_level"],
    }


def make_native_telemetry_signals(rng: random.Random, category: str) -> dict[str, Any]:
    specs = {
        "fake_authority": {
            "status": "passed",
            "liveness": (0.84, 0.98),
            "face_match": (0.82, 0.96),
            "injection": (0.02, 0.18),
            "behavior": (0.42, 0.72),
            "remote": (0.08, 0.38),
            "signals": ["unusual_navigation_sequence", "paste_into_amount_field", "repeated_confirmation_view"],
            "installed_remote": False,
            "accessibility": False,
            "screen_sharing": False,
        },
        "otp_theft": {
            "status": "passed",
            "liveness": (0.86, 0.98),
            "face_match": (0.84, 0.96),
            "injection": (0.02, 0.16),
            "behavior": (0.58, 0.86),
            "remote": (0.14, 0.52),
            "signals": ["paste_into_otp_field", "rapid_focus_switching", "unusual_navigation_sequence"],
            "installed_remote": False,
            "accessibility": False,
            "screen_sharing": False,
        },
        "investment": {
            "status": "passed",
            "liveness": (0.84, 0.98),
            "face_match": (0.82, 0.96),
            "injection": (0.02, 0.2),
            "behavior": (0.25, 0.58),
            "remote": (0.03, 0.28),
            "signals": ["repeated_amount_edits", "hesitation_before_submit"],
            "installed_remote": False,
            "accessibility": False,
            "screen_sharing": False,
        },
        "remote_support": {
            "status": "review",
            "liveness": (0.74, 0.94),
            "face_match": (0.74, 0.92),
            "injection": (0.08, 0.34),
            "behavior": (0.72, 0.94),
            "remote": (0.78, 0.98),
            "signals": [
                "rapid_pointer_jumps",
                "screen_instruction_following",
                "paste_into_amount_field",
                "unusual_navigation_sequence",
            ],
            "installed_remote": True,
            "accessibility": True,
            "screen_sharing": True,
        },
        "legitimate_supplier": {
            "status": "passed",
            "liveness": (0.9, 0.99),
            "face_match": (0.88, 0.99),
            "injection": (0.0, 0.06),
            "behavior": (0.02, 0.18),
            "remote": (0.0, 0.08),
            "signals": [],
            "installed_remote": False,
            "accessibility": False,
            "screen_sharing": False,
        },
    }
    spec = specs[category]
    return {
        "native_telemetry_available": True,
        "native_telemetry_source": "mock_android_sdk",
        "installed_remote_access_app_detected": spec["installed_remote"],
        "accessibility_service_risk": spec["accessibility"],
        "screen_sharing_detected": spec["screen_sharing"],
        "ekyc_verification_status": spec["status"],
        "ekyc_liveness_score": make_confidence(rng, *spec["liveness"]),
        "ekyc_mask_detected": False,
        "ekyc_face_match_score": make_confidence(rng, *spec["face_match"]),
        "ekyc_injection_risk_score": make_confidence(rng, *spec["injection"]),
        "smartux_behavior_anomaly_score": make_confidence(rng, *spec["behavior"]),
        "smartux_remote_control_score": make_confidence(rng, *spec["remote"]),
        "smartux_signals": sample_labels(rng, spec["signals"]) if spec["signals"] else [],
    }


def make_audio_source(category: str, index: int) -> str:
    return f"fixtures/audio/synthetic/{category}-{index:04d}.wav"


def make_confidence(rng: random.Random, low: float, high: float) -> float:
    return round(rng.uniform(low, high), 2)


def detected_patterns_for_category(category: str) -> list[str]:
    patterns = {
        "fake_authority": [
            "fake_authority",
            "case_involvement",
            "transfer_for_verification",
            "secrecy_pressure",
        ],
        "otp_theft": [
            "otp_theft",
            "credential_extraction",
            "security_support_impersonation",
        ],
        "investment": [
            "investment",
            "guaranteed_return",
            "urgency_pressure",
        ],
        "remote_support": [
            "remote_support",
            "screen_control",
            "refund_promise",
            "transfer_test",
        ],
        "legitimate_supplier": [],
    }
    return patterns[category]


def make_coercion_signals(rng: random.Random, category: str) -> dict[str, Any]:
    ranges = {
        "fake_authority": {
            "voice": (0.72, 0.95),
            "face": (0.62, 0.9),
            "scripted": (0.62, 0.88),
            "coercion": (0.72, 0.94),
            "confidence": (0.78, 0.94),
            "voice_labels": ["elevated_pitch", "speech_hesitation", "fast_breathing"],
            "face_labels": ["fear", "distress", "low_eye_contact"],
            "scripted_labels": ["monotone_reading", "long_pauses_before_answers", "repeats_caller_phrasing"],
        },
        "otp_theft": {
            "voice": (0.5, 0.78),
            "face": (0.38, 0.68),
            "scripted": (0.5, 0.78),
            "coercion": (0.52, 0.78),
            "confidence": (0.72, 0.9),
            "voice_labels": ["short_answers", "speech_hesitation", "quiet_voice"],
            "face_labels": ["concern", "reduced_attention"],
            "scripted_labels": ["repeats_caller_phrasing", "long_pauses_before_answers"],
        },
        "investment": {
            "voice": (0.28, 0.55),
            "face": (0.22, 0.5),
            "scripted": (0.25, 0.55),
            "coercion": (0.28, 0.55),
            "confidence": (0.62, 0.84),
            "voice_labels": ["excited_speech", "rapid_response"],
            "face_labels": ["high_engagement"],
            "scripted_labels": ["repeats_caller_phrasing"],
        },
        "remote_support": {
            "voice": (0.62, 0.88),
            "face": (0.5, 0.82),
            "scripted": (0.7, 0.95),
            "coercion": (0.68, 0.9),
            "confidence": (0.76, 0.93),
            "voice_labels": ["speech_hesitation", "fast_breathing"],
            "face_labels": ["distress", "low_eye_contact"],
            "scripted_labels": ["monotone_reading", "repeats_caller_phrasing", "screen_instruction_following"],
        },
    }
    spec = ranges[category]
    return {
        "voice_stress_score": make_confidence(rng, *spec["voice"]),
        "voice_stress_labels": sample_labels(rng, spec["voice_labels"]),
        "face_emotion_score": make_confidence(rng, *spec["face"]),
        "face_emotion_labels": sample_labels(rng, spec["face_labels"]),
        "scripted_behavior_score": make_confidence(rng, *spec["scripted"]),
        "scripted_behavior_labels": sample_labels(rng, spec["scripted_labels"]),
        "coercion_score": make_confidence(rng, *spec["coercion"]),
        "coercion_confidence": make_confidence(rng, *spec["confidence"]),
    }


def empty_coercion_signals() -> dict[str, Any]:
    return {
        "voice_stress_score": None,
        "voice_stress_labels": [],
        "face_emotion_score": None,
        "face_emotion_labels": [],
        "scripted_behavior_score": None,
        "scripted_behavior_labels": [],
        "coercion_score": None,
        "coercion_confidence": None,
    }


def sample_labels(rng: random.Random, labels: list[str]) -> list[str]:
    if not labels:
        return []
    sample_size = rng.randint(1, len(labels))
    return sorted(rng.sample(labels, sample_size))


def round_to_nearest(value: int, unit: int) -> int:
    return round(value / unit) * unit


def expected_shield_band(category: str) -> str:
    if category in {"fake_authority", "otp_theft", "investment", "remote_support"}:
        return "critical"
    return "low"


def expected_grow_band(category: str) -> str:
    if category in {"strong_business", "seasonal_cashflow", "high_volume"}:
        return "strong"
    if category == "emerging_thin_file":
        return "emerging"
    return "thin_file_or_emerging"


def count_categories(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record["category"]] = counts.get(record["category"], 0) + 1
    return counts


if __name__ == "__main__":
    main()
