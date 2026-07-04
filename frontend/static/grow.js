const growForm = document.querySelector("#grow-form");
const growScenario = document.querySelector("#grow-scenario");
const growUpload = document.querySelector("#grow-upload");
const growUploadLabel = document.querySelector("#grow-upload-label");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
const growWizardSteps = document.querySelector("#grow-wizard-steps");
const growBack = document.querySelector("#grow-back");
const growNext = document.querySelector("#grow-next");
const growStatus = document.querySelector("#grow-status");
const growStepExtractBody = document.querySelector("#grow-step-extract-body");
const growStepFinanceBody = document.querySelector("#grow-step-finance-body");
const growStepCreditBody = document.querySelector("#grow-step-credit-body");
const growInputSource = growForm.elements.namedItem("input_source");

const WIZARD_STEPS = [
  { id: 1, nextLabel: "Run analysis" },
  { id: 2, nextLabel: "Continue to financial health" },
  { id: 3, nextLabel: "Continue to credit & capital" },
  { id: 4, nextLabel: "Start new case" },
];

let activeGrowItems = [];
let currentStep = 1;
let lastProcessResponse = null;

initGrowPage();

async function initGrowPage() {
  try {
    await loadDemoDataset();
    populateScenarioSelect(growScenario, window.fidesDemoDataset.grow_invoices);
    growScenario.dispatchEvent(new Event("change"));
    setWizardStep(1);
  } catch (error) {
    console.error(error);
    setGrowStatus("Failed to load Grow demo scenarios.");
  }
}

growScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("grow_invoices", growScenario.value);
  if (!selected) {
    return;
  }

  activeGrowItems = selected.payload.items ?? [];
  fillForm(growForm, selected.payload);
  if (growUpload) {
    growUpload.value = "";
  }
  setUploadLabel("Using demo fixture receipt.");
  updateGrowReceiptPreview(selected.payload.input_source);
  lastProcessResponse = null;
  clearResultPanels();
  setWizardStep(1);
  setGrowStatus("");
});

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
      activeGrowItems = [];
      setUploadLabel(`Uploaded: ${file.name} → ${uploaded.input_source}`);
      updateGrowReceiptPreview(uploaded.input_source);
      lastProcessResponse = null;
      clearResultPanels();
      setWizardStep(1);
      setGrowStatus("Receipt uploaded. Click Run analysis to run PaddleOCR on this image.");
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

  if (currentStep < 4) {
    setWizardStep(currentStep + 1);
    return;
  }

  growScenario.dispatchEvent(new Event("change"));
});

growForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

async function runGrowAnalysis() {
  const payload = buildMinimalGrowRequest(new FormData(growForm));
  growNext.disabled = true;
  setGrowStatus("Running PaddleOCR on receipt image, then ledger, cashflow, and credit scoring...");

  try {
    lastProcessResponse = await postJson("/api/grow/process-invoice", payload);
    const provider = lastProcessResponse.request?.ocr?.provider || "OCR";
    const confidence = lastProcessResponse.request?.ocr?.confidence;
    const confidenceText =
      confidence != null ? ` Confidence ${Math.round(confidence * 100)}%.` : "";
    renderWizardResults(lastProcessResponse);
    setGrowStatus(
      `Analysis complete via ${provider}.${confidenceText} Review each step to see how Grow built the trust profile.`,
    );
    setWizardStep(2);
  } catch (error) {
    setGrowStatus(`Grow analysis failed: ${formatApiError(error.message)}`);
  } finally {
    growNext.disabled = false;
  }
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

  growStepFinanceBody.innerHTML = `
    <div class="grow-stage">
      ${renderGrowLedgerStage(request, request.cashflow_forecast ?? {})}
    </div>
    ${renderEInvoiceBlock(request.einvoice_status)}
  `;

  const profile = request.alternative_credit_profile ?? {};
  const capital = request.capital_connection ?? {};
  const offers = capital.partner_offers ?? [];
  const recommended =
    offers.find((offer) => offer.offer_id === capital.recommended_offer_id) ?? offers[0];
  const contributions = profile.explainability?.feature_contributions?.slice(0, 3) ?? [];

  growStepCreditBody.innerHTML = `
    <div class="metric-row">
      <span class="pill ${analysis.credit_band}">Trust ${analysis.trust_score}/100</span>
      <span class="pill ${analysis.credit_band}">${formatValue(analysis.credit_band)}</span>
      <span class="pill">${formatMoney(analysis.monthly_revenue_estimate)}/mo</span>
      <span class="pill">${formatValue(analysis.loan_readiness)}</span>
    </div>
    <p class="grow-summary">${escapeHtml(analysis.recommended_action)}</p>
    <div class="grow-stage">
      ${renderGrowCreditStage(profile, contributions)}
    </div>
    <div class="grow-stage">
      ${renderGrowCapitalStage(capital, recommended, analysis)}
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

function renderEInvoiceBlock(einvoice) {
  if (!einvoice) {
    return "";
  }

  const errors = einvoice.validation_errors?.length
    ? `<p class="stage-muted">Validation: ${escapeHtml(einvoice.validation_errors.join(", "))}</p>`
    : "";

  return `
    <div class="grow-stage">
      <h4>E-invoice compliance</h4>
      <p class="stage-lead">Status: <strong>${escapeHtml(formatValue(einvoice.status))}</strong> for ${escapeHtml(einvoice.invoice_id)}.</p>
      ${errors}
    </div>
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
  growStepFinanceBody.innerHTML = "";
  growStepCreditBody.innerHTML = "";
}

function setGrowStatus(message) {
  growStatus.textContent = message;
}

function buildMinimalGrowRequest(form) {
  const items = activeGrowItems.length
    ? activeGrowItems
    : [{ description: "Goods and services", amount: Number(form.get("invoice_total")) }];

  return {
    business_id: String(form.get("business_id")),
    business_name: String(form.get("business_name")),
    input_mode: String(form.get("input_mode")),
    input_source: emptyToNull(form.get("input_source")),
    invoice_id: String(form.get("invoice_id")),
    customer_name: String(form.get("customer_name")),
    invoice_total: Number(form.get("invoice_total")),
    paid_on_time: form.get("paid_on_time") === "on",
    items,
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
      <strong>${escapeHtml(provider)}</strong> (not demo JSON).
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

function renderGrowLedgerStage(request, forecast) {
  const summary = request.cashflow_summary;
  const tax = request.tax_summary;

  const cashflowLine = summary
    ? `${escapeHtml(summary.period)} net cashflow ${formatMoney(summary.net_cashflow)} (in ${formatMoney(summary.total_inflow)}, out ${formatMoney(summary.total_outflow)}).`
    : "";

  const forecastLine = forecast.forecast_period_days
    ? `${forecast.forecast_period_days}-day liquidity risk: <strong>${escapeHtml(formatValue(forecast.liquidity_risk_level))}</strong>${
        forecast.shortfall_amount
          ? `; projected shortfall ${formatMoney(forecast.shortfall_amount)}`
          : "; no shortfall projected"
      }.`
    : "";

  const taxLine = tax
    ? `Tax draft: VAT estimate ${formatMoney(tax.vat_estimate)}, filing ${escapeHtml(formatValue(tax.filing_status))}.`
    : "";

  return `
    ${cashflowLine ? `<p class="stage-lead">${cashflowLine}</p>` : ""}
    ${forecastLine ? `<p>${forecastLine}</p>` : ""}
    ${taxLine ? `<p>${taxLine}</p>` : ""}
  `;
}

function renderGrowCreditStage(profile, contributions) {
  if (!profile.alternative_credit_score) {
    return `<p class="stage-muted">Alternative credit profile not available.</p>`;
  }

  return `
    <h4>Alternative credit profile</h4>
    <p class="stage-lead">
      Score <strong>${profile.alternative_credit_score}/100</strong>
      · trust graph ${profile.trust_graph_score?.toFixed(2) ?? "n/a"}
      · vnSocial ${profile.vn_social_reputation_score?.toFixed(2) ?? "n/a"}
    </p>
    ${
      contributions.length
        ? `<div class="shap-list">${contributions
            .map(
              (item) => `
                <div class="shap-row">
                  <span class="shap-label">${escapeHtml(formatValue(item.feature))}</span>
                  <span class="shap-value ${item.direction}">${item.shap_value > 0 ? "+" : ""}${item.shap_value}</span>
                </div>
              `,
            )
            .join("")}</div>`
        : ""
    }
  `;
}

function renderGrowCapitalStage(capital, recommended, result) {
  const advice = capital.smartbot_advice?.message;

  return `
    <h4>Partner capital connection</h4>
    ${
      recommended
        ? `<div class="offer-card">
            <strong>${escapeHtml(recommended.partner_name)} · ${escapeHtml(formatValue(recommended.product_type))}</strong>
            <span>Up to ${formatMoney(recommended.max_amount)} · ${escapeHtml(formatValue(recommended.eligibility_status))}</span>
            <span>${escapeHtml(recommended.reason)}</span>
          </div>`
        : `<p class="stage-muted">No partner offer matched.</p>`
    }
    ${advice ? `<p class="smartbot-advice">${escapeHtml(advice)}</p>` : ""}
    <p class="stage-muted">Final readiness: ${escapeHtml(formatValue(result.loan_readiness))}.</p>
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
