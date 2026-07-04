from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from backend.app.models import (
    CreditExplainability,
    CreditFeatureContribution,
    GrowAnalyzeRequest,
)
from backend.app.services.ml.features import FEATURE_NAMES, FEATURE_REASONS, extract_features, feature_vector

MODEL_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
MODEL_PATH = MODEL_DIR / "grow_credit_lgb.txt"
META_PATH = MODEL_DIR / "grow_credit_model_meta.json"
MODEL_VERSION = "grow_credit_lgb_v1"

_booster = None
_meta: dict | None = None
_load_lock = Lock()


@dataclass(frozen=True)
class CreditModelPrediction:
    trust_score: int
    baseline_score: float
    feature_contributions: list[CreditFeatureContribution]
    model_version: str
    used_ml: bool


def predict_credit_score(request: GrowAnalyzeRequest) -> CreditModelPrediction:
    features = extract_features(request)
    booster = _load_model()
    if booster is None:
        return _rule_based_prediction(features)

    row = [feature_vector(features)]
    raw = booster.predict(row, num_iteration=booster.best_iteration)[0]
    trust_score = max(0, min(int(round(raw)), 100))

    contrib_raw = booster.predict(row, pred_contrib=True, num_iteration=booster.best_iteration)[0]
    baseline = float(contrib_raw[-1])
    shap_values = contrib_raw[:-1]

    contributions = _build_contributions(features, shap_values)
    return CreditModelPrediction(
        trust_score=trust_score,
        baseline_score=baseline,
        feature_contributions=contributions,
        model_version=_meta.get("model_version", MODEL_VERSION) if _meta else MODEL_VERSION,
        used_ml=True,
    )


def build_explainability(prediction: CreditModelPrediction) -> CreditExplainability:
    contributions = sorted(
        prediction.feature_contributions,
        key=lambda item: abs(item.shap_value),
        reverse=True,
    )
    return CreditExplainability(
        model_type="gradient_boosted_trees",
        model_version=prediction.model_version,
        baseline_score=max(0, min(int(round(prediction.baseline_score)), 100)),
        final_score=prediction.trust_score,
        reason_codes=[item.feature for item in contributions if item.direction == "positive"][:3],
        feature_contributions=contributions,
    )


def model_available() -> bool:
    return MODEL_PATH.exists() and META_PATH.exists()


def _load_model():
    global _booster, _meta
    if _booster is not None:
        return _booster
    if not model_available():
        return None

    with _load_lock:
        if _booster is not None:
            return _booster
        try:
            import lightgbm as lgb
        except ImportError:
            return None

        _booster = lgb.Booster(model_file=str(MODEL_PATH))
        _meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        return _booster


def _rule_based_prediction(features: dict[str, float]) -> CreditModelPrediction:
    score = 45.0
    contributions: list[CreditFeatureContribution] = []

    if features["invoice_total"] >= 20_000_000:
        score += 18
        contributions.append(_mock_contribution("invoice_total", features["invoice_total"], 18.0))
    if features["paid_on_time"] >= 0.5:
        score += 22
        contributions.append(_mock_contribution("paid_on_time", True, 22.0))
    else:
        score -= 12
        contributions.append(_mock_contribution("paid_on_time", False, -12.0))
    if features["item_count"] >= 2:
        score += 8
        contributions.append(_mock_contribution("item_count", int(features["item_count"]), 8.0))

    trust_score = max(0, min(int(round(score)), 100))
    return CreditModelPrediction(
        trust_score=trust_score,
        baseline_score=45.0,
        feature_contributions=contributions,
        model_version="grow_credit_rule_fallback",
        used_ml=False,
    )


def _build_contributions(
    features: dict[str, float],
    shap_values: list[float],
) -> list[CreditFeatureContribution]:
    contributions: list[CreditFeatureContribution] = []
    for name, shap_value in zip(FEATURE_NAMES, shap_values, strict=True):
        value: str | int | float | bool | None
        if name == "paid_on_time":
            value = features[name] >= 0.5
        elif name in {"item_count", "invoice_total"}:
            value = int(features[name])
        else:
            value = round(features[name], 4)

        direction = "neutral"
        if shap_value > 0.05:
            direction = "positive"
        elif shap_value < -0.05:
            direction = "negative"

        contributions.append(
            CreditFeatureContribution(
                feature=name,
                value=value,
                shap_value=round(float(shap_value), 1),
                direction=direction,
                reason=FEATURE_REASONS[name],
            )
        )
    return contributions


def _mock_contribution(feature: str, value: str | int | float | bool, shap_value: float) -> CreditFeatureContribution:
    direction = "positive" if shap_value > 0 else "negative" if shap_value < 0 else "neutral"
    return CreditFeatureContribution(
        feature=feature,
        value=value,
        shap_value=shap_value,
        direction=direction,
        reason=FEATURE_REASONS.get(feature, "Rule-based scoring signal."),
    )
