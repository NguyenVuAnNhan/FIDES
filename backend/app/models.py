from pydantic import BaseModel, Field


class Explanation(BaseModel):
    label: str
    detail: str
    weight: int = Field(ge=0, le=100)


class ShieldAnalyzeRequest(BaseModel):
    transaction_amount: int = Field(ge=0)
    recipient_name: str
    recipient_account: str
    active_call: bool = False
    caller_type: str = "unknown"
    caller_number: str = ""
    recipient_known: bool = False
    remote_control_detected: bool = False
    consent_granted: bool = True
    audio_source: str | None = None
    stt_transcript: str = ""
    stt_confidence: float | None = Field(default=None, ge=0, le=1)
    detected_patterns: list[str] = Field(default_factory=list)
    llm_scam_type: str | None = None
    llm_confidence: float | None = Field(default=None, ge=0, le=1)
    voice_stress_score: float | None = Field(default=None, ge=0, le=1)
    voice_stress_labels: list[str] = Field(default_factory=list)
    face_emotion_score: float | None = Field(default=None, ge=0, le=1)
    face_emotion_labels: list[str] = Field(default_factory=list)
    scripted_behavior_score: float | None = Field(default=None, ge=0, le=1)
    scripted_behavior_labels: list[str] = Field(default_factory=list)
    coercion_score: float | None = Field(default=None, ge=0, le=1)
    coercion_confidence: float | None = Field(default=None, ge=0, le=1)
    transcript: str = ""


class ShieldAnalyzeResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    action: str
    scam_type: str | None
    explanations: list[Explanation]
    intervention_message: str


class InvoiceItem(BaseModel):
    description: str
    amount: int = Field(ge=0)


class GrowAnalyzeRequest(BaseModel):
    business_name: str
    invoice_id: str
    customer_name: str
    invoice_total: int = Field(ge=0)
    paid_on_time: bool = True
    items: list[InvoiceItem] = []


class GrowAnalyzeResponse(BaseModel):
    trust_score: int = Field(ge=0, le=100)
    credit_band: str
    monthly_revenue_estimate: int = Field(ge=0)
    loan_readiness: str
    explanations: list[Explanation]
    recommended_action: str
