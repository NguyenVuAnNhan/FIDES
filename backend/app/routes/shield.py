import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.models import ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldChallengeRequest
from backend.app.services.ekyc.paths import ALLOWED_EKYC_EXTENSIONS, ensure_ekyc_upload_dir
from backend.app.services.smartvoice.paths import ALLOWED_AUDIO_EXTENSIONS, ensure_smartvoice_upload_dir
from backend.app.services.shield_challenge_service import run_transfer_monitoring_challenge
from backend.app.services.shield_service import analyze_shield_risk

router = APIRouter(prefix="/api/shield", tags=["shield"])

_ALLOWED_UPLOAD_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
_MAX_EKYC_UPLOAD_BYTES = 8 * 1024 * 1024
_MAX_AUDIO_UPLOAD_BYTES = 16 * 1024 * 1024

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
    ekyc_document_ref: str | None = None
    selfie_filename: str
    document_filename: str | None = None
    selfie_size_bytes: int = Field(ge=0)
    document_size_bytes: int | None = Field(default=None, ge=0)


class ShieldAudioUploadResponse(BaseModel):
    stt_audio_ref: str
    voice_reference_ref: str | None = None
    challenge_filename: str
    reference_filename: str | None = None
    challenge_size_bytes: int = Field(ge=0)
    reference_size_bytes: int | None = Field(default=None, ge=0)


@router.post("/analyze", response_model=ShieldAnalyzeResponse)
def analyze(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    return analyze_shield_risk(request)


@router.post("/challenge", response_model=ShieldAnalyzeResponse)
def challenge(request: ShieldChallengeRequest) -> ShieldAnalyzeResponse:
    return run_transfer_monitoring_challenge(request)


@router.post("/challenge/upload-ekyc", response_model=ShieldEkycUploadResponse)
async def upload_ekyc_challenge(
    selfie: UploadFile = File(...),
    document: UploadFile | None = File(default=None),
) -> ShieldEkycUploadResponse:
    selfie_ref, selfie_name, selfie_size = await _save_ekyc_upload(selfie, "selfie")
    document_ref = None
    document_name = None
    document_size = None
    if document is not None and document.filename:
        document_ref, document_name, document_size = await _save_ekyc_upload(document, "document")

    return ShieldEkycUploadResponse(
        ekyc_image_ref=selfie_ref,
        ekyc_document_ref=document_ref,
        selfie_filename=selfie_name,
        document_filename=document_name,
        selfie_size_bytes=selfie_size,
        document_size_bytes=document_size,
    )


@router.post("/challenge/upload-audio", response_model=ShieldAudioUploadResponse)
async def upload_audio_challenge(
    challenge_audio: UploadFile = File(...),
    voice_reference: UploadFile | None = File(default=None),
) -> ShieldAudioUploadResponse:
    challenge_ref, challenge_name, challenge_size = await _save_audio_upload(challenge_audio, "challenge")
    reference_ref = None
    reference_name = None
    reference_size = None
    if voice_reference is not None and voice_reference.filename:
        reference_ref, reference_name, reference_size = await _save_audio_upload(voice_reference, "voice-ref")

    return ShieldAudioUploadResponse(
        stt_audio_ref=challenge_ref,
        voice_reference_ref=reference_ref,
        challenge_filename=challenge_name,
        reference_filename=reference_name,
        challenge_size_bytes=challenge_size,
        reference_size_bytes=reference_size,
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
