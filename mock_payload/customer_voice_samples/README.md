# Mock Customer Voice Samples

Place enrolled or known-good customer voice samples here.

Use these files as `voice_reference_ref` in `POST /api/shield/challenge`.

Expected meaning:

- `voice_reference_ref`: stored customer voice sample or voice enrollment reference.
- `stt_audio_ref`: newly captured challenge audio from the current transaction.

For the MVP, the files are nonsense placeholders and the backend maps filenames to VNPT-like mock JSON responses. In real mode, the adapter uploads the reference sample and challenge audio, encodes them, and calls VNPT voice verification.
