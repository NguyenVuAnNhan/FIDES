from fastapi import APIRouter

from backend.app.models import ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldChallengeRequest
from backend.app.services.shield_service import analyze_shield_risk, run_mock_camera_voice_challenge

router = APIRouter(prefix="/api/shield", tags=["shield"])


@router.post("/analyze", response_model=ShieldAnalyzeResponse)
def analyze(request: ShieldAnalyzeRequest) -> ShieldAnalyzeResponse:
    return analyze_shield_risk(request)


@router.post("/challenge", response_model=ShieldAnalyzeResponse)
def challenge(request: ShieldChallengeRequest) -> ShieldAnalyzeResponse:
    return run_mock_camera_voice_challenge(request)
