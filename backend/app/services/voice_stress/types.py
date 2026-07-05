from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProsodyFeatures:
    f0_mean_hz: float
    f0_std_hz: float
    pause_ratio: float
    long_pause_count: int
    speech_rate_syms_per_s: float
    energy_std: float
    zero_crossing_rate: float
    duration_s: float
    prosody_stress_score: float


@dataclass(frozen=True)
class VoiceStressResult:
    voice_stress_score: float
    voice_stress_labels: list[str]
    prosody: ProsodyFeatures
    arousal: float | None = None
    valence: float | None = None
    dominance: float | None = None
    distress_score: float | None = None
    top_emotions: list[tuple[str, float]] = field(default_factory=list)
    model_used: bool = False
    model_name: str | None = None
    model_backend: str | None = None
    locale: str = "vi"
    detail: str = ""
    raw: dict[str, object] = field(default_factory=dict)
