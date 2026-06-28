from fastapi import APIRouter

from backend.app.models import ShieldAnalyzeRequest, ShieldAnalyzeResponse
from backend.app.services.shield_service import analyze_shield_risk

router = APIRouter(prefix="/api/shield", tags=["shield"])


@router.post("/analyze", response_model=ShieldAnalyzeResponse)
def analyze(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    return analyze_shield_risk(request)

