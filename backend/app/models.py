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
