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
    recipient_phone: str = ""
    vn_social_report_count: int = Field(default=0, ge=0)
    vn_social_recent_keywords: list[str] = Field(default_factory=list)
    simo_status: str = "not_checked"
    simo_last_checked_at: str | None = None
    graph_risk_score: float | None = Field(default=None, ge=0, le=1)
    graph_pattern: str | None = None
    inbound_sender_count_10m: int = Field(default=0, ge=0)
    outbound_account_count_10m: int = Field(default=0, ge=0)
    median_pass_through_minutes: float | None = Field(default=None, ge=0)
    account_age_days: int | None = Field(default=None, ge=0)
    shared_device_cluster_size: int = Field(default=0, ge=0)
    funds_moved_within_minutes: bool = False
    recipient_risk_level: str = "unknown"
    remote_control_detected: bool = False
    native_telemetry_available: bool = False
    native_telemetry_source: str | None = None
    installed_remote_access_app_detected: bool = False
    accessibility_service_risk: bool = False
    screen_sharing_detected: bool = False
    ekyc_verification_status: str = "not_checked"
    ekyc_liveness_score: float | None = Field(default=None, ge=0, le=1)
    ekyc_mask_detected: bool = False
    ekyc_face_match_score: float | None = Field(default=None, ge=0, le=1)
    ekyc_injection_risk_score: float | None = Field(default=None, ge=0, le=1)
    smartux_behavior_anomaly_score: float | None = Field(default=None, ge=0, le=1)
    smartux_remote_control_score: float | None = Field(default=None, ge=0, le=1)
    smartux_signals: list[str] = Field(default_factory=list)
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
