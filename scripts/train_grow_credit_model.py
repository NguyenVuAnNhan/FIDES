#!/usr/bin/env python3
"""Train the Grow credit-scoring LightGBM model on synthetic invoice features."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lightgbm as lgb
import pandas as pd

from backend.app.models import (
    AlternativeCreditProfile,
    GrowAnalyzeRequest,
    GrowOcrInput,
    InvoiceItem,
    OcrExtractedFields,
)
from backend.app.services.grow_service import compute_rule_trust_score
from backend.app.services.ml.features import FEATURE_NAMES, extract_features, synthetic_graph_features

MODEL_DIR = ROOT / "backend/app/data/models"
MODEL_PATH = MODEL_DIR / "grow_credit_lgb.txt"
META_PATH = MODEL_DIR / "grow_credit_model_meta.json"

GROW_TEMPLATES = {
    "strong_business": {"total_range": (24_000_000, 95_000_000), "paid_on_time": True, "item_counts": (2, 3)},
    "emerging_thin_file": {"total_range": (6_000_000, 18_000_000), "paid_on_time": True, "item_counts": (1, 2)},
    "late_payment": {"total_range": (18_000_000, 55_000_000), "paid_on_time": False, "item_counts": (1, 3)},
    "seasonal_cashflow": {"total_range": (16_000_000, 70_000_000), "paid_on_time": True, "item_counts": (2, 3)},
    "high_volume": {"total_range": (70_000_000, 160_000_000), "paid_on_time": True, "item_counts": (2, 4)},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=3000, help="Synthetic training rows.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = build_training_rows(rng, args.samples)
    frame = pd.DataFrame(rows)
    x = frame[FEATURE_NAMES]
    y = frame["trust_score"]

    split = int(len(frame) * 0.85)
    train_data = lgb.Dataset(x.iloc[:split], label=y.iloc[:split], feature_name=FEATURE_NAMES)
    valid_data = lgb.Dataset(x.iloc[split:], label=y.iloc[split:], feature_name=FEATURE_NAMES, reference=train_data)

    params = {
        "objective": "regression",
        "metric": "rmse",
        "learning_rate": 0.05,
        "num_leaves": 15,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 1,
        "verbose": -1,
        "seed": args.seed,
    }

    booster = lgb.train(
        params,
        train_data,
        num_boost_round=300,
        valid_sets=[valid_data],
        callbacks=[lgb.early_stopping(stopping_rounds=30), lgb.log_evaluation(period=0)],
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(MODEL_PATH))

    meta = {
        "model_version": "grow_credit_lgb_v2",
        "feature_names": FEATURE_NAMES,
        "training_samples": len(frame),
        "valid_rmse": float(booster.best_score["valid_0"]["rmse"]),
        "best_iteration": int(booster.best_iteration),
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote model to {MODEL_PATH}")
    print(f"Validation RMSE: {meta['valid_rmse']:.3f} (iteration {meta['best_iteration']})")
    return 0


def build_training_rows(rng: random.Random, sample_count: int) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    categories = list(GROW_TEMPLATES)
    per_category = max(1, sample_count // len(categories))

    for category in categories:
        template = GROW_TEMPLATES[category]
        for _ in range(per_category):
            invoice_total = rng.randint(*template["total_range"])
            paid_on_time = template["paid_on_time"]
            if rng.random() < 0.08:
                paid_on_time = not paid_on_time

            item_count = rng.randint(*template["item_counts"])
            items = _make_items(rng, invoice_total, item_count)
            tax_amount = round(invoice_total / 11)
            ocr_confidence = round(rng.uniform(0.72, 0.98), 2)
            graph_feats = synthetic_graph_features(category)
            profile = AlternativeCreditProfile(
                trust_graph_score=graph_feats["trust_graph_score"],
                repeat_counterparty_count=int(graph_feats["repeat_counterparty_count"]),
                verified_counterparty_count=int(graph_feats["verified_counterparty_count"]),
                network_centrality_score=graph_feats["network_centrality_score"],
                signals=[],
                confidence=0.8,
            )

            request = GrowAnalyzeRequest(
                business_id=f"biz_{category}",
                business_name=f"Demo {category}",
                input_mode="invoice_photo",
                invoice_id=f"INV-{rng.randint(1000, 9999)}",
                customer_name="Demo Buyer Co.",
                invoice_total=invoice_total,
                paid_on_time=paid_on_time,
                items=items,
                alternative_credit_profile=profile,
                ocr=GrowOcrInput(
                    provider="SmartReader",
                    status="completed",
                    confidence=ocr_confidence,
                    extracted_fields=OcrExtractedFields(
                        total_amount=invoice_total,
                        tax_amount=tax_amount,
                        line_items=items,
                    ),
                ),
            )

            features = extract_features(request)
            label = compute_rule_trust_score(request)
            rows.append({**features, "trust_score": label, "category": category})

    rng.shuffle(rows)
    return rows[:sample_count]


def _make_items(rng: random.Random, invoice_total: int, item_count: int) -> list[InvoiceItem]:
    if item_count <= 1:
        return [InvoiceItem(description="Goods and services", amount=invoice_total, quantity=1, unit_price=invoice_total)]

    weights = [rng.random() for _ in range(item_count)]
    total_weight = sum(weights)
    amounts = [max(1, round(invoice_total * weight / total_weight)) for weight in weights]
    diff = invoice_total - sum(amounts)
    amounts[0] += diff

    return [
        InvoiceItem(description=f"Line item {index + 1}", amount=amount, quantity=1, unit_price=amount)
        for index, amount in enumerate(amounts)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
