import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.models import (
    CallListenResponse,
    ShieldAnalyzeRequest,
    ShieldAnalyzeResponse,
    ShieldChallengeRequest,
    ShieldSessionHeartbeatRequest,
    ShieldSessionHeartbeatResponse,
)
from backend.app.services.call_listen_service import analyze_call_audio
from backend.app.services.ekyc.paths import ALLOWED_EKYC_EXTENSIONS, ensure_ekyc_upload_dir
from backend.app.services.shield.paths import ALLOWED_VIDEO_EXTENSIONS, ensure_shield_upload_dir
from backend.app.services.shield.video import resolve_stt_audio_ref
from backend.app.services.smartvoice.paths import ALLOWED_AUDIO_EXTENSIONS, ensure_smartvoice_upload_dir
from backend.app.services.shield_challenge_service import run_transfer_monitoring_challenge
from backend.app.services.shield_service import analyze_shield_risk
from backend.app.services.shield_session_service import process_session_heartbeat

router = APIRouter(prefix="/api/shield", tags=["shield"])

_ALLOWED_UPLOAD_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
_MAX_EKYC_UPLOAD_BYTES = 8 * 1024 * 1024
_MAX_AUDIO_UPLOAD_BYTES = 16 * 1024 * 1024
_MAX_VIDEO_UPLOAD_BYTES = 32 * 1024 * 1024

_ALLOWED_AUDIO_TYPES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "application/octet-stream": ".wav",
}


class ShieldEkycUploadResponse(BaseModel):
    ekyc_image_ref: str
    ekyc_document_ref: str
    selfie_filename: str
    document_filename: str
    selfie_size_bytes: int = Field(ge=0)
    document_size_bytes: int = Field(ge=0)


class ShieldAudioUploadResponse(BaseModel):
    stt_audio_ref: str
    challenge_filename: str
    challenge_size_bytes: int = Field(ge=0)


class ShieldLiveCheckUploadResponse(BaseModel):
    ekyc_image_ref: str
    ekyc_document_ref: str
    stt_audio_ref: str
    challenge_video_ref: str
    challenge_frame_refs: list[str] = Field(default_factory=list)
    challenge_video_filename: str
    challenge_video_size_bytes: int = Field(ge=0)
    primary_selfie_filename: str
    frame_count: int = Field(ge=0)


@router.post("/analyze", response_model=ShieldAnalyzeResponse)
def analyze(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    return analyze_shield_risk(request)


@router.post("/session/heartbeat", response_model=ShieldSessionHeartbeatResponse)
def session_heartbeat(request: ShieldSessionHeartbeatRequest) -> ShieldSessionHeartbeatResponse:
    """Path B: continuous app-session context scoring from app entry."""
    return process_session_heartbeat(request)


@router.post("/challenge", response_model=ShieldAnalyzeResponse)
def challenge(request: ShieldChallengeRequest) -> ShieldAnalyzeResponse:
    return run_transfer_monitoring_challenge(request)


@router.post("/challenge/upload-ekyc", response_model=ShieldEkycUploadResponse)
async def upload_ekyc_challenge(
    selfie: UploadFile = File(...),
    document: UploadFile = File(...),
) -> ShieldEkycUploadResponse:
    selfie_ref, selfie_name, selfie_size = await _save_ekyc_upload(selfie, "selfie")
    document_ref, document_name, document_size = await _save_ekyc_upload(document, "document")

    return ShieldEkycUploadResponse(
        ekyc_image_ref=selfie_ref,
        ekyc_document_ref=document_ref,
        selfie_filename=selfie_name,
        document_filename=document_name,
        selfie_size_bytes=selfie_size,
        document_size_bytes=document_size,
    )


_ALLOWED_VIDEO_TYPES = {
    "video/webm": ".webm",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "application/octet-stream": ".webm",
}


@router.post("/challenge/upload-live-check", response_model=ShieldLiveCheckUploadResponse)
async def upload_live_check(
    challenge_video: UploadFile = File(...),
    document: UploadFile = File(...),
    challenge_audio: UploadFile | None = File(default=None),
    frame_0: UploadFile | None = File(default=None),
    frame_1: UploadFile | None = File(default=None),
    frame_2: UploadFile | None = File(default=None),
    frame_3: UploadFile | None = File(default=None),
    frame_4: UploadFile | None = File(default=None),
) -> ShieldLiveCheckUploadResponse:
    """Upload a live camera challenge clip plus sampled JPEG frames for eKYC + SmartVision."""
    video_ref, video_name, video_size = await _save_video_upload(challenge_video, "live-check")

    document_ref, _, _ = await _save_ekyc_upload(document, "document")

    uploaded_frames: list[tuple[str, str]] = []
    for index, frame_upload in enumerate([frame_0, frame_1, frame_2, frame_3, frame_4]):
        if frame_upload is None or not frame_upload.filename:
            continue
        frame_ref, frame_name, _ = await _save_frame_upload(frame_upload, f"frame-{index}")
        uploaded_frames.append((frame_ref, frame_name))

    if not uploaded_frames:
        raise HTTPException(
            status_code=422,
            detail="Live check must include sampled JPEG frames from the browser camera.",
        )

    primary_ref, primary_name = uploaded_frames[0]
    frame_refs = [item[0] for item in uploaded_frames]

    if challenge_audio is not None and challenge_audio.filename:
        audio_ref, _, _ = await _save_audio_upload(challenge_audio, "live-audio")
    else:
        audio_ref, _audio_format = resolve_stt_audio_ref(video_ref, ensure_smartvoice_upload_dir())

    return ShieldLiveCheckUploadResponse(
        ekyc_image_ref=primary_ref,
        ekyc_document_ref=document_ref,
        stt_audio_ref=audio_ref,
        challenge_video_ref=video_ref,
        challenge_frame_refs=frame_refs,
        challenge_video_filename=video_name,
        challenge_video_size_bytes=video_size,
        primary_selfie_filename=primary_name,
        frame_count=len(frame_refs),
    )


@router.post("/call-listen", response_model=CallListenResponse)
async def call_listen(
    call_audio: UploadFile = File(...),
    client_session: str = Form(default="call-listen-demo"),
    transcript: str | None = Form(default=None),
) -> CallListenResponse:
    """Path A: analyze a call audio clip for scam signals via SmartVoice STT + Smartbot NLP."""
    audio_ref, _, _ = await _save_audio_upload(call_audio, "call-listen")
    return analyze_call_audio(audio_ref, client_session, transcript)


@router.post("/challenge/upload-audio", response_model=ShieldAudioUploadResponse)
async def upload_audio_challenge(
    challenge_audio: UploadFile = File(...),
) -> ShieldAudioUploadResponse:
    challenge_ref, challenge_name, challenge_size = await _save_audio_upload(challenge_audio, "challenge")

    return ShieldAudioUploadResponse(
        stt_audio_ref=challenge_ref,
        challenge_filename=challenge_name,
        challenge_size_bytes=challenge_size,
    )


async def _save_ekyc_upload(upload: UploadFile, prefix: str) -> tuple[str, str, int]:
    extension = _extension_for_upload(upload)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{prefix} image is empty.")
    if len(data) > _MAX_EKYC_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail=f"{prefix} image must be 8MB or smaller.")

    uploads_dir = ensure_ekyc_upload_dir()
    filename = f"{prefix}-{uuid.uuid4().hex}{extension}"
    path = uploads_dir / filename
    path.write_bytes(data)
    return f"uploads/ekyc/{filename}", filename, len(data)


def _extension_for_upload(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    extension = _ALLOWED_UPLOAD_TYPES.get(content_type)
    if extension is None:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix in ALLOWED_EKYC_EXTENSIONS:
            extension = ".jpg" if suffix == ".jpeg" else suffix
    if extension is None:
        raise HTTPException(status_code=422, detail="Upload a PNG, JPG, or WEBP image.")
    return extension


async def _save_audio_upload(upload: UploadFile, prefix: str) -> tuple[str, str, int]:
    extension = _extension_for_audio_upload(upload)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{prefix} audio is empty.")
    if len(data) > _MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail=f"{prefix} audio must be 16MB or smaller.")

    uploads_dir = ensure_smartvoice_upload_dir()
    filename = f"{prefix}-{uuid.uuid4().hex}{extension}"
    path = uploads_dir / filename
    path.write_bytes(data)
    return f"uploads/smartvoice/{filename}", filename, len(data)


def _extension_for_audio_upload(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    extension = _ALLOWED_AUDIO_TYPES.get(content_type)
    if extension is None:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix in ALLOWED_AUDIO_EXTENSIONS:
            extension = suffix
    if extension is None:
        raise HTTPException(status_code=422, detail="Upload a WAV, MP3, WEBM, M4A, or OGG audio file.")
    return extension


async def _save_video_upload(upload: UploadFile, prefix: str) -> tuple[str, str, int]:
    extension = _extension_for_video_upload(upload)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{prefix} video is empty.")
    if len(data) > _MAX_VIDEO_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail=f"{prefix} video must be 32MB or smaller.")

    uploads_dir = ensure_shield_upload_dir()
    filename = f"{prefix}-{uuid.uuid4().hex}{extension}"
    path = uploads_dir / filename
    path.write_bytes(data)
    return f"uploads/shield/{filename}", filename, len(data)


def _extension_for_video_upload(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    extension = _ALLOWED_VIDEO_TYPES.get(content_type)
    if extension is None:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix in ALLOWED_VIDEO_EXTENSIONS:
            extension = suffix
    if extension is None:
        raise HTTPException(status_code=422, detail="Upload a WEBM, MP4, or MOV live-check video.")
    return extension


async def _save_frame_upload(upload: UploadFile, prefix: str) -> tuple[str, str, int]:
    extension = _extension_for_upload(upload)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail=f"{prefix} frame is empty.")
    if len(data) > _MAX_EKYC_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail=f"{prefix} frame must be 8MB or smaller.")

    uploads_dir = ensure_shield_upload_dir()
    filename = f"{prefix}-{uuid.uuid4().hex}{extension}"
    path = uploads_dir / filename
    path.write_bytes(data)
    return f"uploads/shield/{filename}", filename, len(data)
