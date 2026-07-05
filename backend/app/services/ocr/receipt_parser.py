"""Parse FIDES synthetic receipt OCR text lines into structured fields."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.models import InvoiceItem, OcrExtractedFields

# Paddle often reads "Seller:" as "Seller." — accept ":" or "." after labels.
_LABEL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("seller_name", re.compile(r"^seller\s*[:.]\s*(.*)$", re.I)),
    ("buyer_name", re.compile(r"^buyer\s*[:.]\s*(.*)$", re.I)),
    ("invoice_id", re.compile(r"^invoice\s*[:.]\s*(.*)$", re.I)),
    ("issue_date", re.compile(r"^i(?:ssue|lssue)\s*date\s*[:.]\s*(.*)$", re.I)),
    ("due_date", re.compile(r"^due\s*date\s*[:.]\s*(.*)$", re.I)),
    ("tax_amount", re.compile(r"^tax\s*[:.]\s*(.*)$", re.I)),
    ("total_amount", re.compile(r"^total\s*[:.]\s*(.*)$", re.I)),
]

_SKIP_LINE = re.compile(
    r"^(fides\s*grow\s*receipt|fidesgrow\s*receipt|synthetic\s*de\s*mo\s*fixture|"
    r"synthetic\s*demo\s*fixture|synthetic\s*demofixture|description|amount|"
    r"ocr\s*provider\b|confidence\b|generated\s*for\b)",
    re.I,
)

_INVOICE_ID = re.compile(r"\b(INV-\d{4}-\d+)\b", re.I)
_ISSUE_DATE_INLINE = re.compile(r"(?:issue|lssue)\s*date\s*[:.]?\s*(\d{4}-\d{2}-\d{2})", re.I)
_BUYER_INLINE = re.compile(r"^buyer\s*[:.]\s*(.+)$", re.I)

_LINE_ITEM = re.compile(
    r"^(?P<description>.+?)\s+(?P<amount>\d[\d.,\s]*)\s*(?:vnd)?\s*$",
    re.I,
)

_AMOUNT_ONLY = re.compile(r"^(?P<amount>\d[\d.,\s]*)\s*(?:vnd)?\s*$", re.I)

_REQUIRED_FIELDS = ("seller_name", "buyer_name", "invoice_id", "total_amount")


@dataclass(frozen=True)
class ParseResult:
    fields: OcrExtractedFields
    confidence: float
    missing_required: list[str]


def parse_vnd(value: str | int | float | None) -> int:
    """Parse a VND amount string such as '32,000,000 VND' or '32.000.000'."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)

    text = str(value).strip()
    if not text:
        return 0

    text = re.sub(r"(?i)\bvnd\b", "", text).strip()
    text = text.replace(" ", "")

    if "," in text and "." in text:
        # Prefer the last separator as decimal only when it has 1-2 digits after it.
        if re.search(r",[0-9]{1,2}$", text):
            text = text.replace(".", "").replace(",", ".")
        elif re.search(r"\.[0-9]{1,2}$", text):
            text = text.replace(",", "")
        else:
            text = text.replace(",", "").replace(".", "")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts) if all(len(part) == 3 for part in parts[1:]) else text.replace(",", "")
    elif "." in text:
        parts = text.split(".")
        text = "".join(parts) if all(len(part) == 3 for part in parts[1:]) else text.replace(".", "")

    text = re.sub(r"[^0-9]", "", text)
    if not text:
        return 0
    return int(text)


def parse_receipt_lines(lines: list[str]) -> ParseResult:
    """Map OCR text lines from a FIDES receipt fixture into OcrExtractedFields."""
    cleaned = [_normalize_line(line) for line in lines]
    cleaned = [line for line in cleaned if line]

    values: dict[str, str | int | None] = {
        "seller_name": "",
        "buyer_name": "",
        "invoice_id": "",
        "issue_date": "",
        "due_date": None,
        "tax_amount": 0,
        "total_amount": 0,
    }
    line_items: list[InvoiceItem] = []
    pending_label: str | None = None
    pending_item_description: str | None = None
    in_items = False

    for line in cleaned:
        if _SKIP_LINE.match(line):
            if re.match(r"^description\b", line, re.I):
                in_items = True
            continue

        label, remainder = _match_label(line)
        if label:
            pending_label = None
            pending_item_description = None
            if label in {"tax_amount", "total_amount"}:
                in_items = False
                values[label] = parse_vnd(remainder) if remainder else 0
                if not remainder:
                    pending_label = label
            elif remainder:
                values[label] = remainder.strip()
            else:
                pending_label = label
            continue

        if pending_label:
            if pending_label in {"tax_amount", "total_amount"}:
                values[pending_label] = parse_vnd(line)
            else:
                values[pending_label] = line
            pending_label = None
            continue

        if in_items:
            if pending_item_description:
                amount = parse_vnd(line)
                if amount > 0:
                    line_items.append(
                        InvoiceItem(
                            description=pending_item_description,
                            amount=amount,
                            quantity=1,
                            unit_price=amount,
                        )
                    )
                    pending_item_description = None
                    continue
                pending_item_description = None

            item = _parse_line_item(line)
            if item:
                line_items.append(item)
                continue

            if _AMOUNT_ONLY.match(line) is None:
                pending_item_description = line
            continue

        # Paddle sometimes drops the "Total:" label and only emits the amount line.
        if (
            values["total_amount"] == 0
            and int(values["tax_amount"] or 0) > 0
            and _AMOUNT_ONLY.match(line)
        ):
            values["total_amount"] = parse_vnd(line)

    _apply_fides_receipt_heuristics(cleaned, values, line_items)

    fields = OcrExtractedFields(
        invoice_id=str(values["invoice_id"] or ""),
        seller_name=str(values["seller_name"] or ""),
        buyer_name=str(values["buyer_name"] or ""),
        issue_date=str(values["issue_date"] or ""),
        due_date=None if values["due_date"] in {None, "", "-"} else str(values["due_date"]),
        total_amount=int(values["total_amount"] or 0),
        tax_amount=int(values["tax_amount"] or 0),
        currency="VND",
        line_items=line_items,
    )
    missing = [name for name in _REQUIRED_FIELDS if not _has_required(fields, name)]
    present = len(_REQUIRED_FIELDS) - len(missing)
    confidence = round(present / len(_REQUIRED_FIELDS), 2)
    if line_items:
        confidence = min(1.0, round(confidence + 0.1, 2))
    return ParseResult(fields=fields, confidence=confidence, missing_required=missing)


def _normalize_line(line: str) -> str:
    text = str(line or "").replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _match_label(line: str) -> tuple[str | None, str]:
    for name, pattern in _LABEL_PATTERNS:
        match = pattern.match(line)
        if match:
            return name, match.group(1).strip()
    return None, ""


def _parse_line_item(line: str) -> InvoiceItem | None:
    match = _LINE_ITEM.match(line)
    if not match:
        return None
    description = match.group("description").strip(" -:")
    if not description or re.match(r"^(tax|total)\b", description, re.I):
        return None
    if _AMOUNT_ONLY.match(description):
        return None
    amount = parse_vnd(match.group("amount"))
    if amount <= 0:
        return None
    return InvoiceItem(description=description, amount=amount, quantity=1, unit_price=amount)


def _has_required(fields: OcrExtractedFields, name: str) -> bool:
    value = getattr(fields, name)
    if isinstance(value, int):
        return value > 0
    return bool(str(value or "").strip())


def _apply_fides_receipt_heuristics(
    cleaned: list[str],
    values: dict[str, str | int | None],
    line_items: list[InvoiceItem],
) -> None:
    """Fill missing fields when SmartReader OCR drops labels on FIDES synthetic receipts."""
    if not values["invoice_id"]:
        for line in cleaned:
            match = _INVOICE_ID.search(line)
            if match:
                values["invoice_id"] = match.group(1)
                break

    if not values["issue_date"]:
        for line in cleaned:
            match = _ISSUE_DATE_INLINE.search(line)
            if match:
                values["issue_date"] = match.group(1)
                break

    if not values["seller_name"]:
        for index, line in enumerate(cleaned):
            if not _BUYER_INLINE.match(line):
                continue
            for candidate in reversed(cleaned[:index]):
                if _SKIP_LINE.match(candidate):
                    continue
                if _INVOICE_ID.search(candidate) or _ISSUE_DATE_INLINE.search(candidate):
                    continue
                if _BUYER_INLINE.match(candidate) or re.match(
                    r"^(due|tax|total|invoice|seller)\b", candidate, re.I
                ):
                    continue
                if _AMOUNT_ONLY.match(candidate) or _LINE_ITEM.match(candidate):
                    continue
                values["seller_name"] = candidate
                break
            break

    item_sum = sum(item.amount for item in line_items)
    total = int(values["total_amount"] or 0)
    standalone_amounts = [
        parse_vnd(match.group("amount"))
        for line in cleaned
        if (match := _AMOUNT_ONLY.match(line))
    ]
    if standalone_amounts and (total <= 0 or (item_sum > 0 and total < item_sum)):
        values["total_amount"] = max(standalone_amounts)
        total = int(values["total_amount"] or 0)
        if int(values["tax_amount"] or 0) <= 0:
            smaller = [amount for amount in standalone_amounts if amount < total]
            if smaller:
                values["tax_amount"] = max(smaller)
