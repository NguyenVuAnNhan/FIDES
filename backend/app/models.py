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
    quantity: float | None = Field(default=None, ge=0)
    unit_price: int | None = Field(default=None, ge=0)


class OcrExtractedFields(BaseModel):
    invoice_id: str = ""
    seller_name: str = ""
    buyer_name: str = ""
    issue_date: str = ""
    due_date: str | None = None
    total_amount: int = Field(default=0, ge=0)
    tax_amount: int = Field(default=0, ge=0)
    currency: str = "VND"
    line_items: list[InvoiceItem] = Field(default_factory=list)


class GrowOcrInput(BaseModel):
    provider: str = "SmartReader"
    status: str = "not_used"
    confidence: float | None = Field(default=None, ge=0, le=1)
    extracted_fields: OcrExtractedFields | None = None


class VoiceParsedFields(BaseModel):
    transaction_type: str = ""
    amount: int = Field(default=0, ge=0)
    description: str = ""
    transaction_date: str = ""
    category: str = ""


class GrowVoiceEntry(BaseModel):
    provider: str = "SmartVoice"
    status: str = "not_used"
    audio_source: str | None = None
    transcript: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)
    parsed_fields: VoiceParsedFields | None = None


class NormalizedLedgerEntry(BaseModel):
    entry_id: str = ""
    source_type: str = ""
    transaction_type: str = ""
    counterparty_name: str = ""
    amount: int = Field(default=0, ge=0)
    currency: str = "VND"
    transaction_date: str = ""
    category: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)


class CashflowSummary(BaseModel):
    period: str = ""
    total_inflow: int = Field(default=0, ge=0)
    total_outflow: int = Field(default=0, ge=0)
    net_cashflow: int = 0
    largest_customer: str = ""
    revenue_confidence: float | None = Field(default=None, ge=0, le=1)


class TaxSummary(BaseModel):
    period: str = ""
    vat_estimate: int = Field(default=0, ge=0)
    taxable_revenue: int = Field(default=0, ge=0)
    deductible_expenses: int = Field(default=0, ge=0)
    estimated_tax_due: int = Field(default=0, ge=0)
    filing_status: str = "not_ready"


class EInvoiceStatus(BaseModel):
    provider: str = "mock_einvoice"
    status: str = "not_started"
    invoice_id: str = ""
    validation_errors: list[str] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)


class AlternativeCreditProfile(BaseModel):
    trust_graph_score: float | None = Field(default=None, ge=0, le=1)
    repeat_counterparty_count: int = Field(default=0, ge=0)
    verified_counterparty_count: int = Field(default=0, ge=0)
    network_centrality_score: float | None = Field(default=None, ge=0, le=1)
    cashflow_stability_score: float | None = Field(default=None, ge=0, le=1)
    vn_social_reputation_score: float | None = Field(default=None, ge=0, le=1)
    vn_social_mentions_30d: int = Field(default=0, ge=0)
    vn_social_sentiment: str = "unknown"
    vn_social_complaint_count_30d: int = Field(default=0, ge=0)
    alternative_credit_score: int | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    signals: list[str] = Field(default_factory=list)


class GrowAnalyzeRequest(BaseModel):
    business_id: str = ""
    business_name: str
    input_mode: str = "manual_entry"
    input_source: str | None = None
    ocr: GrowOcrInput = Field(default_factory=GrowOcrInput)
    voice_entry: GrowVoiceEntry = Field(default_factory=GrowVoiceEntry)
    normalized_ledger_entry: NormalizedLedgerEntry | None = None
    cashflow_summary: CashflowSummary | None = None
    tax_summary: TaxSummary | None = None
    einvoice_status: EInvoiceStatus | None = None
    alternative_credit_profile: AlternativeCreditProfile | None = None
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
