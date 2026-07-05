from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmotionPrediction:
    arousal: float
    valence: float
    dominance: float
    distress_score: float
    top_emotions: list[tuple[str, float]] = field(default_factory=list)
    backend: str = ""
    model_name: str = ""
