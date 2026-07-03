const growForm = document.querySelector("#grow-form");
const growScenario = document.querySelector("#grow-scenario");
const growResult = document.querySelector("#grow-result");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
let activeGrowItems = [];
let lastGrowRequest = null;

initGrowPage();

async function initGrowPage() {
  try {
    await loadDemoDataset();
    populateScenarioSelect(growScenario, window.fidesDemoDataset.grow_invoices);
    growScenario.dispatchEvent(new Event("change"));
  } catch (error) {
    console.error(error);
    resetResult(growResult, "Failed to load Grow demo scenarios.");
  }
}

growScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("grow_invoices", growScenario.value);
  if (selected) {
    activeGrowItems = selected.payload.items ?? [];
    fillForm(growForm, selected.payload);
    fillGrowNestedFields(selected.payload);
    updateGrowReceiptPreview(selected.payload.input_source);
    resetResult(growResult, "Run Grow analysis to see credit readiness.");
  }
});

growForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = buildMinimalGrowRequest(new FormData(growForm));

  growResult.className = "result empty";
  growResult.textContent = "Analyzing Grow profile...";
  try {
    const response = await postJson("/api/grow/process-invoice", payload);
    lastGrowRequest = response.request;
    growResult.className = "result";
    growResult.innerHTML = renderGrow(response.analysis, response.request);
  } catch (error) {
    growResult.className = "result empty";
    growResult.textContent = `Grow analysis failed: ${error.message}`;
  }
});

growForm.elements.namedItem("input_source").addEventListener("input", (event) => {
  updateGrowReceiptPreview(event.target.value);
});

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

function renderGrow(result, request = lastGrowRequest) {
  return `
    <div class="metric-row">
      <span class="pill ${result.credit_band}">Trust ${result.trust_score}/100</span>
      <span class="pill ${result.credit_band}">${formatValue(result.credit_band)}</span>
      <span class="pill">${formatMoney(result.monthly_revenue_estimate)}/mo</span>
      <span class="pill">${formatValue(result.loan_readiness)}</span>
    </div>
    <p class="grow-summary">${escapeHtml(result.recommended_action)}</p>
    ${request ? renderGrowPipeline(request, result) : ""}
    ${renderExplanations(result.explanations)}
  `;
}

function renderGrowPipeline(request, result) {
  const ocr = request.ocr ?? {};
  const extracted = ocr.extracted_fields ?? {};
  const forecast = request.cashflow_forecast ?? {};
  const profile = request.alternative_credit_profile ?? {};
  const capital = request.capital_connection ?? {};
  const offers = capital.partner_offers ?? [];
  const recommended = offers.find((offer) => offer.offer_id === capital.recommended_offer_id) ?? offers[0];
  const contributions = profile.explainability?.feature_contributions?.slice(0, 3) ?? [];

  return `
    <div class="grow-pipeline">
      <section class="grow-stage">
        <h3>1. SmartReader extraction</h3>
        ${renderGrowOcrStage(ocr, extracted, request)}
      </section>
      <section class="grow-stage">
        <h3>2. Ledger & cashflow</h3>
        ${renderGrowLedgerStage(request, forecast)}
      </section>
      <section class="grow-stage">
        <h3>3. Alternative credit</h3>
        ${renderGrowCreditStage(profile, contributions)}
      </section>
      <section class="grow-stage">
        <h3>4. Capital connection</h3>
        ${renderGrowCapitalStage(capital, recommended, result)}
      </section>
    </div>
  `;
}

function renderGrowOcrStage(ocr, extracted, request) {
  if (ocr.status !== "completed") {
    return `<p class="stage-muted">Input mode: ${escapeHtml(formatValue(request.input_mode))}.</p>`;
  }

  const lineItems = extracted.line_items ?? request.items ?? [];
  const confidence = ocr.confidence != null ? `${Math.round(ocr.confidence * 100)}%` : "n/a";

  return `
    <p class="stage-lead">Invoice ${escapeHtml(extracted.invoice_id || request.invoice_id)} extracted with ${confidence} confidence.</p>
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
  const ledger = request.normalized_ledger_entry;
  const summary = request.cashflow_summary;
  const tax = request.tax_summary;

  const ledgerLine = ledger
    ? `Ledger ${escapeHtml(ledger.entry_id)} recorded ${formatMoney(ledger.amount)} as ${escapeHtml(formatValue(ledger.category))}.`
    : "Ledger entry pending.";

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
    <p class="stage-lead">${ledgerLine}</p>
    ${cashflowLine ? `<p>${cashflowLine}</p>` : ""}
    ${forecastLine ? `<p>${forecastLine}</p>` : ""}
    ${taxLine ? `<p>${taxLine}</p>` : ""}
  `;
}

function renderGrowCreditStage(profile, contributions) {
  if (!profile.alternative_credit_score) {
    return `<p class="stage-muted">Alternative credit profile not available.</p>`;
  }

  return `
    <p class="stage-lead">
      Alternative score <strong>${profile.alternative_credit_score}/100</strong>
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

function fillGrowNestedFields(payload) {
  const ocr = payload.ocr ?? {};
  const voiceEntry = payload.voice_entry ?? {};
  setFieldValue(growForm, "ocr_status", ocr.status ?? "not_used");
  setFieldValue(growForm, "ocr_confidence", ocr.confidence ?? "");
  setFieldValue(growForm, "voice_status", voiceEntry.status ?? "not_used");
  setFieldValue(growForm, "voice_confidence", voiceEntry.confidence ?? "");
  setFieldValue(growForm, "voice_transcript", voiceEntry.transcript ?? "");
}
