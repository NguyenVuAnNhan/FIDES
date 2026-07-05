from __future__ import annotations

from threading import Lock
from typing import Any

import numpy as np

from backend.app.services.voice_stress.audio_io import load_mono_audio_from_array
from backend.app.services.voice_stress.prosody import TARGET_SAMPLE_RATE

DEFAULT_WAV2VEC_MODEL = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"

_model_bundle: dict[str, Any] | None = None
_load_lock = Lock()
_load_error: str | None = None


def predict_wav2vec_emotion(
    signal: np.ndarray,
    sample_rate: int,
    model_name: str = DEFAULT_WAV2VEC_MODEL,
) -> tuple[float, float, float] | None:
    """Return arousal, dominance, valence in [0, 1] or None if model unavailable."""
    bundle = _load_model(model_name)
    if bundle is None:
        return None

    import torch

    processor = bundle["processor"]
    model = bundle["model"]
    device = bundle["device"]

    if sample_rate != TARGET_SAMPLE_RATE:
        signal, _ = load_mono_audio_from_array(signal, sample_rate, TARGET_SAMPLE_RATE)
        sample_rate = TARGET_SAMPLE_RATE

    if signal.size < int(0.5 * sample_rate):
        padded = np.zeros(int(0.5 * sample_rate), dtype=np.float32)
        padded[: signal.size] = signal
        signal = padded

    inputs = processor(signal, sampling_rate=sample_rate, return_tensors="pt", padding=True)
    input_values = inputs["input_values"].to(device)
    attention_mask = inputs.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    with torch.no_grad():
        _, logits = model(input_values, attention_mask=attention_mask)

    values = logits.detach().cpu().numpy()[0]
    arousal, dominance, valence = (_clip01(float(v)) for v in values[:3])
    return arousal, dominance, valence


def model_load_error() -> str | None:
    return _load_error


def _load_model(model_name: str) -> dict[str, Any] | None:
    global _model_bundle, _load_error
    if _model_bundle is not None and _model_bundle.get("model_name") == model_name:
        return _model_bundle

    with _load_lock:
        if _model_bundle is not None and _model_bundle.get("model_name") == model_name:
            return _model_bundle
        try:
            import torch
            import torch.nn as nn
            from transformers import Wav2Vec2Model, Wav2Vec2PreTrainedModel, Wav2Vec2Processor

            class EmotionModel(Wav2Vec2PreTrainedModel):
                def __init__(self, config):
                    super().__init__(config)
                    self.wav2vec2 = Wav2Vec2Model(config)
                    self.classifier = nn.Linear(config.hidden_size, config.num_labels)

                def forward(self, input_values, attention_mask=None):
                    outputs = self.wav2vec2(input_values, attention_mask=attention_mask)
                    hidden_states = outputs[0]
                    hidden_states = torch.mean(hidden_states, dim=1)
                    logits = self.classifier(hidden_states)
                    return hidden_states, logits

            device = "cuda" if torch.cuda.is_available() else "cpu"
            processor = Wav2Vec2Processor.from_pretrained(model_name)
            model = EmotionModel.from_pretrained(model_name).to(device)
            model.eval()
            _model_bundle = {
                "processor": processor,
                "model": model,
                "device": device,
                "model_name": model_name,
            }
            _load_error = None
            return _model_bundle
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            _model_bundle = None
            return None


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))
