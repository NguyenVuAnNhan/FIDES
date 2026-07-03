from fastapi import APIRouter

from backend.app.models import (
    GrowAnalyzeRequest,
    GrowAnalyzeResponse,
    GrowProcessRequest,
    GrowProcessResponse,
)
from backend.app.services.grow_pipeline_service import process_invoice
from backend.app.services.grow_service import analyze_invoice

router = APIRouter(prefix="/api/grow", tags=["grow"])


@router.post("/process-invoice", response_model=GrowProcessResponse)
def process_invoice_route(request: GrowProcessRequest) -> GrowProcessResponse:
    return process_invoice(request)


@router.post("/analyze-invoice", response_model=GrowAnalyzeResponse)
def analyze_invoice_route(request: GrowAnalyzeRequest) -> GrowAnalyzeResponse:
    return analyze_invoice(request)

