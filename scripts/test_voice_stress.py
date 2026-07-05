from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import Settings
from backend.app.services.voice_stress.analyzer import analyze_voice_stress
from backend.app.services.voice_stress.prosody import analyze_prosody, prosody_labels


def _write_wav(path: Path, signal: np.ndarray, sample_rate: int = 16000) -> None:
    pcm = np.clip(signal, -1.0, 1.0)
    pcm16 = (pcm * 32767).astype(np.int16)
    data = pcm16.tobytes()
    with path.open("wb") as handle:
        handle.write(b"RIFF")
        handle.write(struct.pack("<I", 36 + len(data)))
        handle.write(b"WAVEfmt ")
        handle.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        handle.write(b"data")
        handle.write(struct.pack("<I", len(data)))
        handle.write(data)


from backend.app.services.voice_stress.emotion2vec_model import (
    _map_distress_scores,
    _normalize_emotion_label,
)


class VoiceStressProsodyTests(unittest.TestCase):
    def test_pausey_audio_gets_hesitation_label(self) -> None:
        sample_rate = 16000
        chunks = [np.zeros(sample_rate // 2), np.sin(2 * np.pi * 220 * np.linspace(0, 0.4, int(0.4 * sample_rate)))]
        signal = np.concatenate(chunks)
        prosody = analyze_prosody(signal.astype(np.float32), sample_rate)
        labels = prosody_labels(prosody)
        self.assertGreaterEqual(prosody.pause_ratio, 0.1)
        self.assertIn("speech_hesitation", labels)

    def test_analyzer_prosody_only_mode(self) -> None:
        sample_rate = 16000
        t = np.linspace(0, 1.5, int(1.5 * sample_rate), endpoint=False)
        signal = (0.35 * np.sin(2 * np.pi * 260 * t)).astype(np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "stress.wav"
            _write_wav(wav_path, signal, sample_rate)
            settings = Settings(
                voice_stress_enabled=True,
                voice_stress_mode="prosody",
            )
            result = analyze_voice_stress(str(wav_path), settings)
            self.assertFalse(result.model_used)
            self.assertGreaterEqual(result.voice_stress_score, 0.0)
            self.assertLessEqual(result.voice_stress_score, 1.0)
            self.assertTrue(result.voice_stress_labels)

    def test_emotion2vec_distress_mapping(self) -> None:
        ranked = [("fearful", 0.62), ("neutral", 0.21), ("sad", 0.09)]
        distress, arousal, valence, _dominance = _map_distress_scores(ranked)
        self.assertGreater(distress, 0.5)
        self.assertGreater(arousal, 0.4)
        self.assertLess(valence, 0.55)

    def test_bilingual_emotion_labels_normalize_to_english(self) -> None:
        self.assertEqual(_normalize_emotion_label("中立/neutral"), "neutral")
        self.assertEqual(_normalize_emotion_label("难过/sad"), "sad")
        ranked = [("中立/neutral", 0.2), ("难过/sad", 0.55), ("生气/angry", 0.25)]
        distress, _arousal, _valence, _dominance = _map_distress_scores(ranked)
        self.assertGreater(distress, 0.5)


if __name__ == "__main__":
    unittest.main()
