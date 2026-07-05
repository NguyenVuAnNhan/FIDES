const growForm = document.querySelector("#grow-form");
const growUpload = document.querySelector("#grow-upload");
const growUploadLabel = document.querySelector("#grow-upload-label");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
const growWizardSteps = document.querySelector("#grow-wizard-steps");
const growBack = document.querySelector("#grow-back");
const growNext = document.querySelector("#grow-next");
const growStatus = document.querySelector("#grow-status");
const growStepExtractBody = document.querySelector("#grow-step-extract-body");
const growStepCreditBody = document.querySelector("#grow-step-credit-body");
const growInputSource = growForm.elements.namedItem("input_source");

const WIZARD_STEPS = [
  { id: 1, nextLabel: "Run analysis" },
  { id: 2, nextLabel: "Continue to credit score" },
  { id: 3, nextLabel: "Start new case" },
];

let currentStep = 1;
let lastProcessResponse = null;

initGrowPage();

function initGrowPage() {
  resetCaptureForm();
  setWizardStep(1);
  setGrowStatus("Upload a receipt image to begin.");
}

if (growUpload) {
  growUpload.addEventListener("change", async () => {
    const file = growUpload.files?.[0];
    if (!file) {
      return;
    }

    growNext.disabled = true;
    setGrowStatus(`Uploading ${file.name}...`);
    try {
      const uploaded = await uploadReceipt(file);
      growInputSource.value = uploaded.input_source;
      setFieldValue(growForm, "invoice_id", "");
      setFieldValue(growForm, "business_name", "");
      setFieldValue(growForm, "customer_name", "");
      setFieldValue(growForm, "invoice_total", "0");
      setUploadLabel(`Uploaded: ${file.name}`);
      updateGrowReceiptPreview(uploaded.input_source);
      lastProcessResponse = null;
      clearResultPanels();
      setWizardStep(1);
      setGrowStatus("Receipt uploaded. Click Run analysis to run SmartReader OCR on this image.");
    } catch (error) {
      setGrowStatus(`Upload failed: ${formatApiError(error.message)}`);
    } finally {
      growNext.disabled = false;
    }
  });
}

growBack.addEventListener("click", () => {
  if (currentStep > 1) {
    setWizardStep(currentStep - 1);
  }
});

growNext.addEventListener("click", async () => {
  if (currentStep === 1) {
    await runGrowAnalysis();
    return;
  }

  if (currentStep < 3) {
    setWizardStep(currentStep + 1);
    return;
  }

  resetCaptureForm();
  setWizardStep(1);
  setGrowStatus("Upload a receipt image to begin.");
});

growForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

async function runGrowAnalysis() {
  const payload = buildMinimalGrowRequest(new FormData(growForm));
  if (!payload.input_source) {
    setGrowStatus("Upload a receipt image before running analysis.");
    return;
  }

  growNext.disabled = true;
  setGrowStatus("Running SmartReader OCR on receipt image, then LightGBM credit scoring...");

  try {
    lastProcessResponse = await postJson("/api/grow/process-invoice", payload);
    const provider = lastProcessResponse.request?.ocr?.provider || "OCR";
    const confidence = lastProcessResponse.request?.ocr?.confidence;
    const confidenceText =
      confidence != null ? ` Confidence ${Math.round(confidence * 100)}%.` : "";
    renderWizardResults(lastProcessResponse);
    setGrowStatus(
      `Analysis complete via ${provider}.${confidenceText} Review OCR extraction and credit score.`,
    );
    setWizardStep(2);
  } catch (error) {
    setGrowStatus(`Grow analysis failed: ${formatApiError(error.message)}`);
  } finally {
    growNext.disabled = false;
  }
}

function resetCaptureForm() {
  if (growUpload) {
    growUpload.value = "";
  }
  growInputSource.value = "";
  setFieldValue(growForm, "invoice_id", "");
  setFieldValue(growForm, "business_name", "");
  setFieldValue(growForm, "customer_name", "");
  setFieldValue(growForm, "invoice_total", "0");
  const paidOnTime = growForm.elements.namedItem("paid_on_time");
  if (paidOnTime) {
    paidOnTime.checked = true;
  }
  setUploadLabel("No receipt uploaded yet.");
  updateGrowReceiptPreview("");
  lastProcessResponse = null;
  clearResultPanels();
}

function formatApiError(message) {
  try {
    const parsed = JSON.parse(message);
    if (parsed && typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch (_error) {
    // Keep the original message when the body is not JSON.
  }
  return message;
}

async function uploadReceipt(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/grow/upload-receipt", {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function setUploadLabel(text) {
  if (growUploadLabel) {
    growUploadLabel.textContent = text;
  }
}

function renderWizardResults(response) {
  const request = response.request;
  const analysis = response.analysis;
  const ocr = request.ocr ?? {};
  const extracted = ocr.extracted_fields ?? {};

  growStepExtractBody.innerHTML = `
    <div class="grow-stage">
      ${renderGrowOcrStage(ocr, extracted, request)}
    </div>
    <div class="grow-stage">
      <h4>Normalized ledger</h4>
      ${renderLedgerBlock(request.normalized_ledger_entry)}
    </div>
  `;

  const explainability = analysis.credit_explainability ?? {};
  const contributions = explainability.feature_contributions ?? [];

  growStepCreditBody.innerHTML = `
    <p class="grow-disclaimer stage-muted">
      <strong>Preliminary only.</strong> One invoice cannot describe the whole business.
      Upload 2–3 more receipts (same business ID) before recommending a working-capital limit.
    </p>
    <div class="metric-row">
      <span class="pill ${analysis.credit_band}">Trust ${analysis.trust_score}/100</span>
      <span class="pill ${analysis.credit_band}">${formatValue(analysis.credit_band)}</span>
      <span class="pill">Est. ${formatMoney(analysis.monthly_revenue_estimate)}/mo (rough, from this invoice)</span>
      <span class="pill">${formatValue(analysis.loan_readiness)}</span>
    </div>
    <p class="grow-summary">${escapeHtml(analysis.recommended_action)}</p>
    <div class="grow-stage">
      ${renderTrustGraphBlock(request.alternative_credit_profile)}
    </div>
    <div class="grow-stage">
      ${renderGrowCreditStage(explainability, contributions, analysis.trust_score)}
    </div>
    ${renderExplanations(analysis.explanations)}
  `;
}

function renderLedgerBlock(ledger) {
  if (!ledger) {
    return `<p class="stage-muted">Ledger entry pending.</p>`;
  }

  return `
    <p class="stage-lead">
      Entry <strong>${escapeHtml(ledger.entry_id)}</strong> records
      ${formatMoney(ledger.amount)} as ${escapeHtml(formatValue(ledger.category))}.
    </p>
    <dl class="stage-facts">
      <div><dt>Counterparty</dt><dd>${escapeHtml(ledger.counterparty_name)}</dd></div>
      <div><dt>Date</dt><dd>${escapeHtml(ledger.transaction_date)}</dd></div>
      <div><dt>Source</dt><dd>${escapeHtml(formatValue(ledger.source_type))}</dd></div>
      <div><dt>Confidence</dt><dd>${ledger.confidence != null ? ledger.confidence.toFixed(2) : "n/a"}</dd></div>
    </dl>
  `;
}

function setWizardStep(step) {
  currentStep = step;
  const config = WIZARD_STEPS[step - 1];

  growForm.querySelectorAll(".wizard-panel").forEach((panel) => {
    const panelStep = Number(panel.dataset.step);
    const isActive = panelStep === step;
    panel.classList.toggle("is-active", isActive);
    panel.hidden = !isActive;
  });

  growWizardSteps.querySelectorAll(".wizard-step").forEach((item) => {
    const itemStep = Number(item.dataset.step);
    item.classList.toggle("is-active", itemStep === step);
    item.classList.toggle("is-complete", itemStep < step && lastProcessResponse != null);
  });

  growBack.disabled = step === 1;
  growNext.textContent = config.nextLabel;
  growNext.disabled = step > 1 && !lastProcessResponse;
}

function clearResultPanels() {
  growStepExtractBody.innerHTML = "";
  growStepCreditBody.innerHTML = "";
}

function setGrowStatus(message) {
  growStatus.textContent = message;
}

function buildMinimalGrowRequest(form) {
  return {
    business_id: String(form.get("business_id") || "biz_demo"),
    business_name: String(form.get("business_name") || ""),
    input_mode: String(form.get("input_mode") || "invoice_photo"),
    input_source: emptyToNull(form.get("input_source")),
    invoice_id: String(form.get("invoice_id") || ""),
    customer_name: String(form.get("customer_name") || ""),
    invoice_total: Number(form.get("invoice_total") || 0),
    paid_on_time: form.get("paid_on_time") === "on",
    items: [],
  };
}

function renderGrowOcrStage(ocr, extracted, request) {
  if (ocr.status !== "completed") {
    return `<p class="stage-muted">OCR status: ${escapeHtml(formatValue(ocr.status || "not_used"))}. Input mode: ${escapeHtml(formatValue(request.input_mode))}.</p>`;
  }

  const lineItems = extracted.line_items ?? request.items ?? [];
  const confidence = ocr.confidence != null ? `${Math.round(ocr.confidence * 100)}%` : "n/a";
  const provider = ocr.provider || "OCR";

  return `
    <div class="metric-row">
      <span class="pill strong">${escapeHtml(provider)}</span>
      <span class="pill">${escapeHtml(formatValue(ocr.status))}</span>
      <span class="pill">Confidence ${escapeHtml(confidence)}</span>
    </div>
    <h4>Fields read from receipt image</h4>
    <p class="stage-lead">
      Invoice ${escapeHtml(extracted.invoice_id || request.invoice_id)} extracted by
      <strong>${escapeHtml(provider)}</strong> from the uploaded image.
    </p>
    <p class="stage-muted">Source: ${escapeHtml(request.input_source || "n/a")}</p>
    <dl class="stage-facts">
      <div><dt>Seller</dt><dd>${escapeHtml(extracted.seller_name || request.business_name)}</dd></div>
      <div><dt>Buyer</dt><dd>${escapeHtml(extracted.buyer_name || request.customer_name)}</dd></div>
      <div><dt>Total</dt><dd>${formatMoney(extracted.total_amount ?? request.invoice_total)}</dd></div>
      <div><dt>Payment</dt><dd>${request.paid_on_time ? "On time" : "Late"}</dd></div>
    </dl>
    ${
      lineItems.length
        ? `<ul class="stage-list">${lineItems
            .map((item) => `<li>${escapeHtml(item.description)} · ${formatMoney(item.amount)}</li>`)
            .join("")}</ul>`
        : ""
    }
  `;
}

function renderTrustGraphBlock(profile) {
  if (!profile) {
    return `
      <h4>Trust graph (Neo4j)</h4>
      <p class="stage-muted">
        Trust graph unavailable. Start Neo4j (<code>docker compose up neo4j -d</code>)
        and set <code>NEO4J_ENABLED=true</code> in <code>.env</code>.
      </p>
    `;
  }

  const trust = profile.trust_graph_score != null ? profile.trust_graph_score.toFixed(2) : "n/a";
  const centrality =
    profile.network_centrality_score != null ? profile.network_centrality_score.toFixed(2) : "n/a";
  const confidence = profile.confidence != null ? `${Math.round(profile.confidence * 100)}%` : "n/a";
  const signals = profile.signals ?? [];

  return `
    <h4>Trust graph (Neo4j)</h4>
    <div class="metric-row">
      <span class="pill strong">Trust ${escapeHtml(trust)}</span>
      <span class="pill">${profile.repeat_counterparty_count} repeat</span>
      <span class="pill">${profile.verified_counterparty_count} verified</span>
      <span class="pill">Centrality ${escapeHtml(centrality)}</span>
      <span class="pill">Confidence ${escapeHtml(confidence)}</span>
    </div>
    ${
      signals.length
        ? `<ul class="stage-list">${signals
            .map((signal) => `<li>${escapeHtml(formatValue(signal))}</li>`)
            .join("")}</ul>`
        : `<p class="stage-muted">No graph signals yet for this business.</p>`
    }
  `;
}

function renderGrowCreditStage(explainability, contributions, trustScore) {
  if (!contributions.length) {
    return `<p class="stage-muted">Credit explainability not available.</p>`;
  }

  const modelVersion = explainability.model_version || "n/a";
  const baseline = explainability.baseline_score ?? "n/a";

  return `
    <h4>LightGBM credit model</h4>
    <p class="stage-lead">
      Model <strong>${escapeHtml(modelVersion)}</strong>
      · baseline ${escapeHtml(String(baseline))}
      · final <strong>${trustScore}/100</strong>
    </p>
    <div class="shap-list">${contributions
      .map(
        (item) => `
          <div class="shap-row">
            <span class="shap-label">${escapeHtml(formatValue(item.feature))}</span>
            <span class="shap-value ${item.direction}">${item.shap_value > 0 ? "+" : ""}${item.shap_value}</span>
          </div>
        `,
      )
      .join("")}</div>
  `;
}

function updateGrowReceiptPreview(source) {
  const src = String(source ?? "").trim();
  if (!src) {
    growReceiptPreview.removeAttribute("src");
    growReceiptPreview.hidden = true;
    return;
  }

  growReceiptPreview.src = src;
  growReceiptPreview.hidden = false;
}
