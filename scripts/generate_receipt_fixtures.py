#!/usr/bin/env python3
"""Generate fake receipt PNG fixtures from curated Grow records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

DATASET_PATH = Path("backend/app/data/demo_dataset.json")
STATIC_ROOT = Path("frontend/static")

REGULAR_FONT_CANDIDATES = [
    Path("/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf"),  # Linux
    Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),  # macOS
    Path("C:/Windows/Fonts/cour.ttf"),  # Windows
]
BOLD_FONT_CANDIDATES = [
    Path("/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Bold.otf"),  # Linux
    Path("/System/Library/Fonts/Supplemental/Courier New Bold.ttf"),  # macOS
    Path("C:/Windows/Fonts/courbd.ttf"),  # Windows
]


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    generated = []
    for record in dataset["grow_invoices"]:
        payload = record["payload"]
        input_source = payload.get("input_source")
        if payload.get("input_mode") != "invoice_photo" or not input_source:
            continue
        output_path = resolve_static_path(input_source)
        render_receipt(record, output_path)
        generated.append(output_path)

    for path in generated:
        print(f"Wrote {path}")


def resolve_static_path(input_source: str) -> Path:
    if not input_source.startswith("/static/"):
        raise ValueError(f"Receipt input_source must start with /static/: {input_source}")
    return STATIC_ROOT / input_source.removeprefix("/static/")


def render_receipt(record: dict[str, Any], output_path: Path) -> None:
    payload = record["payload"]
    ocr_fields = payload["ocr"]["extracted_fields"]
    items = ocr_fields["line_items"]
    width = 760
    row_height = 34
    height = 640 + len(items) * row_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (width, height), "#fbfaf5")
    draw = ImageDraw.Draw(image)
    font = load_font(REGULAR_FONT_CANDIDATES, 24)
    small = load_font(REGULAR_FONT_CANDIDATES, 20)
    bold = load_font(BOLD_FONT_CANDIDATES, 28)
    bold_small = load_font(BOLD_FONT_CANDIDATES, 21)

    draw.rectangle((22, 22, width - 22, height - 22), outline="#1f2933", width=2)
    draw.text((48, 44), "FIDES GROW RECEIPT", fill="#111827", font=bold)
    draw.text((48, 84), "Synthetic demo fixture", fill="#667085", font=small)
    draw.line((48, 122, width - 48, 122), fill="#cbd5e1", width=2)

    y = 150
    y = draw_field(draw, "Seller", ocr_fields["seller_name"], 48, y, small, bold_small)
    y = draw_field(draw, "Buyer", ocr_fields["buyer_name"], 48, y, small, bold_small)
    y = draw_field(draw, "Invoice", ocr_fields["invoice_id"], 48, y, small, bold_small)
    y = draw_field(draw, "Issue date", ocr_fields["issue_date"], 48, y, small, bold_small)
    y = draw_field(draw, "Due date", ocr_fields.get("due_date") or "-", 48, y, small, bold_small)

    y += 18
    draw.line((48, y, width - 48, y), fill="#cbd5e1", width=2)
    y += 22
    draw.text((48, y), "Description", fill="#111827", font=bold_small)
    draw.text((520, y), "Amount", fill="#111827", font=bold_small)
    y += 34

    for item in items:
        draw.text((48, y), truncate(item["description"], 36), fill="#111827", font=small)
        draw.text((520, y), format_vnd(item["amount"]), fill="#111827", font=small)
        y += row_height

    y += 8
    draw.line((48, y, width - 48, y), fill="#cbd5e1", width=2)
    y += 24
    y = draw_amount(draw, "Tax", ocr_fields["tax_amount"], 48, y, small, bold_small)
    y = draw_amount(draw, "Total", ocr_fields["total_amount"], 48, y, font, bold)

    y += 18
    draw.text((48, y), "OCR provider: SmartReader", fill="#667085", font=small)
    y += 30
    draw.text((48, y), f"Confidence: {payload['ocr']['confidence']:.2f}", fill="#667085", font=small)
    draw.text((48, height - 88), "Generated for FIDES HackAIthon MVP", fill="#667085", font=small)

    image.save(output_path)


def draw_field(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    x: int,
    y: int,
    font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
) -> int:
    draw.text((x, y), f"{label}:", fill="#344054", font=label_font)
    draw.text((x + 150, y), value, fill="#111827", font=font)
    return y + 32


def draw_amount(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: int,
    x: int,
    y: int,
    font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
) -> int:
    draw.text((x, y), f"{label}:", fill="#111827", font=label_font)
    draw.text((520, y), format_vnd(value), fill="#111827", font=font)
    return y + 38


def format_vnd(value: int) -> str:
    return f"{value:,.0f} VND"


def truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def load_font(candidates: list[Path], size: int) -> ImageFont.ImageFont:
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


if __name__ == "__main__":
    main()
