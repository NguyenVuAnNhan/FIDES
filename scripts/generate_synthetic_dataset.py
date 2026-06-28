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
            "remote_control_detected": remote_control_detected,
            "transcript": transcript,
        },
    }


def build_grow_invoice(rng: random.Random, index: int, category: str) -> dict[str, Any]:
    template = GROW_TEMPLATES[category]
    total = round_to_nearest(rng.randint(*template["total_range"]), 100_000)
    business_name = f"{rng.choice(BUSINESS_PREFIXES)} {rng.choice(BUSINESS_TYPES)}"
    item_names = rng.choice(template["item_sets"])

    return {
        "id": f"synthetic-grow-{index:04d}",
        "category": category,
        "title": rng.choice(template["titles"]),
        "business_stage": rng.choice(template["business_stages"]),
        "demo_goal": "Synthetic madlib invoice for volume testing and dashboard demos.",
        "expected_band": expected_grow_band(category),
        "payload": {
            "business_name": business_name,
            "invoice_id": f"INV-2026-{index:04d}",
            "customer_name": rng.choice(CUSTOMER_NAMES),
            "invoice_total": total,
            "paid_on_time": template["paid_on_time"],
            "items": split_items(total, item_names),
        },
    }


def split_items(total: int, item_names: list[str]) -> list[dict[str, Any]]:
    if len(item_names) == 1:
        return [{"description": item_names[0], "amount": total}]

    remaining = total
    items = []
    for index, item_name in enumerate(item_names):
        if index == len(item_names) - 1:
            amount = remaining
        else:
            amount = round_to_nearest(total // len(item_names), 100_000)
            remaining -= amount
        items.append({"description": item_name, "amount": amount})
    return items


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
