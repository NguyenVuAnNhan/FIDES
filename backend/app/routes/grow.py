from fastapi import APIRouter

from backend.app.models import GrowAnalyzeRequest, GrowAnalyzeResponse
from backend.app.services.grow_service import analyze_invoice

router = APIRouter(prefix="/api/grow", tags=["grow"])


@router.post("/analyze-invoice", response_model=GrowAnalyzeResponse)
def analyze_invoice_route(request: GrowAnalyzeRequest) -> GrowAnalyzeResponse:
    return analyze_invoice(request)

