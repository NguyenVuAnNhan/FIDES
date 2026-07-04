from __future__ import annotations

import hashlib
import re


def normalize_counterparty_name(name: str) -> str:
    collapsed = re.sub(r"\s+", " ", name.strip().lower())
    return collapsed


def counterparty_id(name: str) -> str:
    normalized = normalize_counterparty_name(name)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"cp_{digest[:16]}"
