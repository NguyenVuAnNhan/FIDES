import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.models import (
    GrowAnalyzeRequest,
    GrowAnalyzeResponse,
    GrowProcessRequest,
    GrowProcessResponse,
)
from backend.app.services.grow_pipeline_service import GrowOcrError, process_invoice
from backend.app.services.grow_service import analyze_invoice
from backend.app.services.ocr.paths import ensure_uploads_dir

router = APIRouter(prefix="/api/grow", tags=["grow"])

_ALLOWED_UPLOAD_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}
_MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class GrowUploadResponse(BaseModel):
    input_source: str
    filename: str
    size_bytes: int = Field(ge=0)


@router.post("/upload-receipt", response_model=GrowUploadResponse)
async def upload_receipt(file: UploadFile = File(...)) -> GrowUploadResponse:
    content_type = (file.content_type or "").lower()
    extension = _ALLOWED_UPLOAD_TYPES.get(content_type)
    if extension is None:
        # Fall back to filename extension for browsers that omit content-type.
        suffix = Path(file.filename or "").suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            extension = ".jpg" if suffix == ".jpeg" else suffix
        else:
            raise HTTPException(
                status_code=422,
                detail="Upload a PNG, JPG, or WEBP receipt image.",
            )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="Receipt image must be 8MB or smaller.")

    uploads_dir = ensure_uploads_dir()
    filename = f"upload-{uuid.uuid4().hex}{extension}"
    path = uploads_dir / filename
    path.write_bytes(data)

    return GrowUploadResponse(
        input_source=f"/static/uploads/receipts/{filename}",
        filename=filename,
        size_bytes=len(data),
    )


@router.post("/process-invoice", response_model=GrowProcessResponse)
def process_invoice_route(request: GrowProcessRequest) -> GrowProcessResponse:
    try:
        return process_invoice(request)
    except GrowOcrError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/analyze-invoice", response_model=GrowAnalyzeResponse)
def analyze_invoice_route(request: GrowAnalyzeRequest) -> GrowAnalyzeResponse:
    return analyze_invoice(request)
