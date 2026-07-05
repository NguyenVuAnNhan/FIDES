#!/usr/bin/env python3
"""End-to-end Path B test: Android emulator UI (stage 1) + backend API (stage 2).

Stage 1 drives the sample banking app on the emulator via adb/uiautomator.
Stage 2 calls the same Shield challenge endpoints the mobile SDK uses, because
CCCD picker + 10s live camera recording are not reliably automatable on CI emulators.
"""

from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ID = "ai.fides.sample.banking"
MAIN_ACTIVITY = "ai.fides.sample.banking/ai.fides.sample.ShieldTransferActivity"
ENV_SH = ROOT / "sdks/mobile/env.sh"
APK = ROOT / "sdks/mobile/sample-banking-app/build/outputs/apk/debug/sample-banking-app-debug.apk"
BACKEND = "http://127.0.0.1:8000"
EMULATOR_BACKEND = "http://10.0.2.2:8000"


def sh(cmd: str, *, check: bool = True, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["bash", "-lc", f"source '{ENV_SH}' && {cmd}"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {cmd}\n{proc.stderr or proc.stdout}")
    return proc


def adb(*args: str, check: bool = True, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return sh(" ".join(["adb", *args]), check=check, timeout=timeout)


def tap_text(text: str, *, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        bounds = find_bounds(text)
        if bounds:
            x = (bounds[0] + bounds[2]) // 2
            y = (bounds[1] + bounds[3]) // 2
            adb("shell", "input", "tap", str(x), str(y))
            return
        time.sleep(1)
    raise RuntimeError(f"UI text not found: {text!r}")


def find_bounds(text: str, *, prefer_clickable: bool = True) -> tuple[int, int, int, int] | None:
    adb("shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
    xml = adb("shell", "cat", "/sdcard/window_dump.xml").stdout
    root = ET.fromstring(xml)
    pattern = re.compile(re.escape(text), re.I)
    matches: list[tuple[tuple[int, int, int, int], bool]] = []
    for node in root.iter("node"):
        label = node.attrib.get("text") or node.attrib.get("content-desc") or ""
        if not pattern.search(label):
            continue
        raw = node.attrib.get("bounds", "")
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", raw)
        if not match:
            continue
        bounds = tuple(int(v) for v in match.groups())
        clickable = node.attrib.get("clickable") == "true"
        matches.append((bounds, clickable))
    if not matches:
        return None
    if prefer_clickable:
        clickable_matches = [item for item in matches if item[1]]
        if clickable_matches:
            return clickable_matches[-1][0]
    return matches[-1][0]


def wait_text(text: str, *, timeout: float = 45) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if find_bounds(text):
            return
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for UI text: {text!r}")


def grant_permissions() -> None:
    for perm in ("android.permission.CAMERA", "android.permission.RECORD_AUDIO", "android.permission.READ_PHONE_STATE"):
        adb("shell", "pm", "grant", APP_ID, perm, check=False)


def ensure_backend() -> None:
    import urllib.request

    for url in (f"{BACKEND}/api/health", f"{EMULATOR_BACKEND}/api/health"):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"[ok] backend reachable at {url}")
                    return
        except Exception:
            continue
    raise RuntimeError("FIDES backend is not reachable on :8000. Start uvicorn first.")


def ensure_app_installed() -> None:
    if not APK.is_file():
        sh(f"cd '{ROOT / 'sdks/mobile'}' && ./gradlew :sample-banking-app:assembleDebug")
    listed = adb("shell", "pm", "list", "packages", APP_ID, check=False).stdout
    if APP_ID not in listed:
        adb("install", "-r", str(APK))


def stage1_emulator_flow() -> dict:
    print("\n== Stage 1: emulator UI (analyze) ==")
    adb("shell", "am", "force-stop", APP_ID, check=False)
    adb("shell", "am", "start", "-n", MAIN_ACTIVITY)
    time.sleep(2)
    tap_text("Kiểm tra giao dịch")
    wait_text("Xác nhận chuyển khoản")
    tap_text("Xác nhận chuyển khoản")
    wait_text("Cảnh báo!", timeout=60)
    wait_text("Risk", timeout=10)
    print("[ok] Stage 1 warning overlay shown (identity check required)")
    tap_text("Tôi hiểu rủi ro, tiếp tục")
    wait_text("Xác minh danh tính", timeout=20)
    print("[ok] Stage 2 identity screen opened")
    return {"stage1": "warning_shown", "stage2_screen": "voice_verification"}


def _write_min_jpeg(path: Path) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 400), color=(240, 240, 240)).save(path, format="JPEG")


def _write_silence_wav(path: Path, seconds: float = 2.0, rate: int = 16000) -> None:
    sample_count = int(rate * seconds)
    data = b"\x00\x00" * sample_count
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"RIFF")
        handle.write(struct.pack("<I", 36 + len(data)))
        handle.write(b"WAVEfmt ")
        handle.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        handle.write(b"data")
        handle.write(struct.pack("<I", len(data)))
        handle.write(data)


def stage2_backend_challenge() -> dict:
    """Mirror mobile SDK runIdentityCheck against the backend."""
    print("\n== Stage 2: backend challenge (mobile-equivalent API) ==")
    import requests

    analyze_payload = {
        "shield_path": "transfer_monitoring",
        "transaction_amount": 65_000_000,
        "recipient_name": "Tran Van B",
        "recipient_account": "9704 2222 8800",
        "active_call": True,
        "caller_type": "unknown",
        "caller_number": "+84 909 000 555",
        "recipient_known": False,
        "consent_granted": True,
        "consent_call_monitoring": False,
        "consent_transfer_check": False,
        "native_telemetry_available": True,
        "ekyc_verification_status": "not_checked",
        "stt_transcript": "",
        "llm_scam_type": None,
    }

    analyze = requests.post(f"{BACKEND}/api/shield/analyze", json=analyze_payload, timeout=60)
    analyze.raise_for_status()
    analyze_body = analyze.json()
    print(f"[analyze] action={analyze_body.get('action')} risk={analyze_body.get('risk_score')}")
    if not analyze_body.get("invasive_check_required"):
        raise RuntimeError(f"Expected invasive check, got action={analyze_body.get('action')!r}")

    fixtures = ROOT / "uploads/e2e"
    cccd = fixtures / "cccd.jpg"
    clip = fixtures / "live-check.webm"
    frame = fixtures / "frame-001.jpg"
    _write_min_jpeg(cccd)
    _write_min_jpeg(frame)
    if not clip.is_file():
        _write_silence_wav(fixtures / "live-check.wav")
        clip = fixtures / "live-check.wav"

    files = {
        "document": ("cccd.jpg", cccd.read_bytes(), "image/jpeg"),
        "challenge_video": (clip.name, clip.read_bytes(), "video/webm" if clip.suffix == ".webm" else "audio/wav"),
        "frame_0": ("frame-001.jpg", frame.read_bytes(), "image/jpeg"),
    }
    upload = requests.post(
        f"{BACKEND}/api/shield/challenge/upload-live-check",
        files=files,
        timeout=120,
    )
    upload.raise_for_status()
    upload_body = upload.json()
    print(
        f"[upload] video={upload_body.get('challenge_video_ref')} "
        f"doc={upload_body.get('ekyc_document_ref')} frames={upload_body.get('frame_count')}"
    )

    challenge_payload = {
        "transaction": analyze_payload,
        "ekyc_image_ref": upload_body["ekyc_image_ref"],
        "ekyc_document_ref": upload_body["ekyc_document_ref"],
        "stt_audio_ref": upload_body["stt_audio_ref"],
        "challenge_video_ref": upload_body.get("challenge_video_ref"),
        "challenge_frame_refs": upload_body.get("challenge_frame_refs") or [],
        "client_session": "fides-e2e-emulator",
    }
    challenge = requests.post(f"{BACKEND}/api/shield/challenge", json=challenge_payload, timeout=180)
    challenge.raise_for_status()
    body = challenge.json()
    print(
        f"[challenge] action={body.get('action')} risk={body.get('risk_score')} "
        f"stage2={body.get('stage_two_score')}"
    )
    return body


def main() -> int:
    failures: list[str] = []
    try:
        sh("adb get-state")
    except Exception as exc:
        print(f"FAIL: no adb device — start emulator first ({exc})")
        return 1

    try:
        ensure_backend()
        ensure_app_installed()
        grant_permissions()
        stage1 = stage1_emulator_flow()
        stage2 = stage2_backend_challenge()
    except Exception as exc:
        failures.append(str(exc))

    print("\n== summary ==")
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1

    print(json.dumps({"status": "ok", "stage1": stage1, "stage2_action": stage2.get("action")}, indent=2))
    print("\nPath B e2e passed (emulator stage 1 + backend stage 2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
