const growForm = document.querySelector("#grow-form");
const growScenario = document.querySelector("#grow-scenario");
const growResult = document.querySelector("#grow-result");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
let activeGrowPayload = null;
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
    activeGrowPayload = structuredClone(selected.payload);
    activeGrowItems = selected.payload.items ?? [];
    fillForm(growForm, selected.payload);
    fillGrowNestedFields(selected.payload);
    updateGrowReceiptPreview(selected.payload.input_source);
    resetResult(growResult, "Run Grow analysis to see credit readiness.");
  }
});

growForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(growForm);
  const payload = buildGrowPayloadFromForm(form);

  growResult.className = "result empty";
  growResult.textContent = "Analyzing Grow profile...";
  try {
    lastGrowRequest = payload;
    const response = await postJson("/api/grow/analyze-invoice", payload);
    growResult.className = "result";
    growResult.innerHTML = renderGrow(response, payload);
  } catch (error) {
    growResult.className = "result empty";
    growResult.textContent = `Grow analysis failed: ${error.message}`;
  }
});

growForm.elements.namedItem("input_source").addEventListener("input", (event) => {
  updateGrowReceiptPreview(event.target.value);
});

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

function buildGrowPayloadFromForm(form) {
  if (activeGrowPayload) {
    return mergeGrowPayloadFromForm(activeGrowPayload, form);
  }

  return buildGrowPayloadFromScratch(form);
}

function mergeGrowPayloadFromForm(base, form) {
  const payload = structuredClone(base);
  payload.business_id = String(form.get("business_id"));
  payload.business_name = String(form.get("business_name"));
  payload.input_mode = String(form.get("input_mode"));
  payload.input_source = emptyToNull(form.get("input_source"));
  payload.invoice_id = String(form.get("invoice_id"));
  payload.customer_name = String(form.get("customer_name"));
  payload.invoice_total = Number(form.get("invoice_total"));
  payload.paid_on_time = form.get("paid_on_time") === "on";
  payload.items = activeGrowItems.length
    ? activeGrowItems
    : payload.items?.length
      ? payload.items
      : [{ description: "Goods and services", amount: payload.invoice_total }];

  if (payload.ocr) {
    payload.ocr = {
      ...payload.ocr,
      status: String(form.get("ocr_status")),
      confidence: numberOrNull(form.get("ocr_confidence")) ?? payload.ocr.confidence,
    };
  }

  if (payload.voice_entry) {
    payload.voice_entry = {
      ...payload.voice_entry,
      status: String(form.get("voice_status")),
      confidence: numberOrNull(form.get("voice_confidence")) ?? payload.voice_entry.confidence,
      transcript: String(form.get("voice_transcript")),
    };
  }

  return payload;
}

function buildGrowPayloadFromScratch(form) {
  return {
    business_id: String(form.get("business_id")),
    business_name: String(form.get("business_name")),
    input_mode: String(form.get("input_mode")),
    input_source: emptyToNull(form.get("input_source")),
    ocr: buildOcrPayload(form),
    voice_entry: buildVoicePayload(form),
    normalized_ledger_entry: buildLedgerPayload(form),
    cashflow_summary: buildCashflowSummary(form),
    cashflow_forecast: buildCashflowForecast(form),
    tax_summary: buildTaxSummary(form),
    einvoice_status: buildEInvoiceStatus(form),
    alternative_credit_profile: buildAlternativeCreditProfile(form),
    capital_connection: buildCapitalConnection(form),
    invoice_id: String(form.get("invoice_id")),
    customer_name: String(form.get("customer_name")),
    invoice_total: Number(form.get("invoice_total")),
    paid_on_time: form.get("paid_on_time") === "on",
    items: activeGrowItems.length
      ? activeGrowItems
      : [{ description: "Goods and services", amount: Number(form.get("invoice_total")) }],
  };
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

function buildOcrPayload(form) {
  const total = Number(form.get("invoice_total"));
  const invoiceId = String(form.get("invoice_id"));
  const businessName = String(form.get("business_name"));
  const customerName = String(form.get("customer_name"));
  return {
    provider: "SmartReader",
    status: String(form.get("ocr_status")),
    confidence: numberOrNull(form.get("ocr_confidence")),
    extracted_fields: {
      invoice_id: invoiceId,
      seller_name: businessName,
      buyer_name: customerName,
      issue_date: "2026-06-28",
      due_date: "2026-07-05",
      total_amount: total,
      tax_amount: Math.round(total / 11),
      currency: "VND",
      line_items: activeGrowItems.length
        ? activeGrowItems
        : [{ description: "Goods and services", amount: total, quantity: 1, unit_price: total }],
    },
  };
}

function buildVoicePayload(form) {
  const amount = Number(form.get("invoice_total"));
  return {
    provider: "SmartVoice",
    status: String(form.get("voice_status")),
    audio_source: null,
    transcript: String(form.get("voice_transcript")),
    confidence: numberOrNull(form.get("voice_confidence")),
    parsed_fields: {
      transaction_type: "sale",
      amount,
      description: String(form.get("customer_name")),
      transaction_date: "2026-06-28",
      category: "sales_revenue",
    },
  };
}

function buildLedgerPayload(form) {
  return {
    entry_id: `ledger_${String(form.get("invoice_id")).toLowerCase().replaceAll("-", "_")}`,
    source_type: String(form.get("input_mode")),
    transaction_type: "sale",
    counterparty_name: String(form.get("customer_name")),
    amount: Number(form.get("invoice_total")),
    currency: "VND",
    transaction_date: "2026-06-28",
    category: "sales_revenue",
    confidence: numberOrNull(form.get("ocr_confidence")) ?? numberOrNull(form.get("voice_confidence")),
  };
}

function buildCashflowSummary(form) {
  const monthlyRevenue = Number(form.get("invoice_total")) * 4;
  const totalOutflow = Math.round(monthlyRevenue * 0.58);
  return {
    period: "2026-06",
    total_inflow: monthlyRevenue,
    total_outflow: totalOutflow,
    net_cashflow: monthlyRevenue - totalOutflow,
    largest_customer: String(form.get("customer_name")),
    revenue_confidence: numberOrNull(form.get("ocr_confidence")) ?? numberOrNull(form.get("voice_confidence")),
  };
}

function buildCashflowForecast(form) {
  const invoiceTotal = Number(form.get("invoice_total"));
  const paidOnTime = form.get("paid_on_time") === "on";
  const projectedInflow = invoiceTotal * (paidOnTime ? 4 : 3);
  const projectedOutflow = Math.round(invoiceTotal * (paidOnTime ? 3.1 : 3.6));
  const projectedNetCashflow = projectedInflow - projectedOutflow;
  const minimumCashBuffer = Math.round(invoiceTotal * 0.75);
  const shortfallAmount = Math.max(0, minimumCashBuffer - projectedNetCashflow);
  const liquidityRiskLevel = shortfallAmount
    ? shortfallAmount > invoiceTotal * 0.5
      ? "high"
      : "medium"
    : "low";

  return {
    forecast_period_days: 30,
    projected_inflow: projectedInflow,
    projected_outflow: projectedOutflow,
    projected_net_cashflow: projectedNetCashflow,
    minimum_cash_buffer: minimumCashBuffer,
    liquidity_risk_level: liquidityRiskLevel,
    shortfall_amount: shortfallAmount,
    shortfall_expected_date: shortfallAmount ? "2026-07-18" : null,
    recommended_borrowing_window: shortfallAmount ? "2026-07-10_to_2026-07-17" : "not_required",
    recommended_credit_amount: shortfallAmount ? Math.ceil((shortfallAmount * 1.2) / 1000000) * 1000000 : 0,
    drivers: [
      paidOnTime ? "on_time_receivables" : "late_receivable_risk",
      shortfallAmount ? "projected_cash_buffer_gap" : "positive_cash_buffer",
      invoiceTotal >= 20_000_000 ? "meaningful_revenue_base" : "thin_recent_revenue",
    ],
    confidence: paidOnTime ? 0.74 : 0.62,
  };
}

function buildTaxSummary(form) {
  const monthlyRevenue = Number(form.get("invoice_total")) * 4;
  const totalOutflow = Math.round(monthlyRevenue * 0.58);
  const deductibleExpenses = Math.round(totalOutflow * 0.55);
  return {
    period: "2026-06",
    vat_estimate: Math.round(monthlyRevenue / 11),
    taxable_revenue: monthlyRevenue,
    deductible_expenses: deductibleExpenses,
    estimated_tax_due: Math.max(0, Math.round((monthlyRevenue - deductibleExpenses) * 0.05)),
    filing_status: form.get("paid_on_time") === "on" ? "draft_ready" : "needs_review",
  };
}

function buildEInvoiceStatus(form) {
  const paidOnTime = form.get("paid_on_time") === "on";
  return {
    provider: "mock_einvoice",
    status: paidOnTime ? "draft_ready" : "needs_review",
    invoice_id: String(form.get("invoice_id")),
    validation_errors: paidOnTime ? [] : ["payment_status_late"],
    compliance_notes: [
      "Required buyer and seller fields present",
      "VAT estimate generated",
      "Ledger entry linked to source document",
    ],
  };
}

function buildAlternativeCreditProfile(form) {
  const invoiceTotal = Number(form.get("invoice_total"));
  const paidOnTime = form.get("paid_on_time") === "on";
  const hasMeaningfulRevenue = invoiceTotal >= 20_000_000;
  const itemCount = activeGrowItems.length || 1;
  const trustGraphScore = paidOnTime ? (hasMeaningfulRevenue ? 0.84 : 0.62) : 0.48;
  const vnSocialReputationScore = paidOnTime ? (hasMeaningfulRevenue ? 0.78 : 0.64) : 0.52;
  const cashflowStabilityScore = paidOnTime ? (hasMeaningfulRevenue ? 0.8 : 0.58) : 0.42;
  const complaints = paidOnTime ? 0 : 2;
  const alternativeCreditScore = Math.round(
    (trustGraphScore * 0.35 + vnSocialReputationScore * 0.3 + cashflowStabilityScore * 0.35) * 100,
  );

  return {
    trust_graph_score: trustGraphScore,
    repeat_counterparty_count: hasMeaningfulRevenue ? 12 : 3,
    verified_counterparty_count: hasMeaningfulRevenue ? 8 : 1,
    network_centrality_score: hasMeaningfulRevenue ? 0.68 : 0.42,
    cashflow_stability_score: cashflowStabilityScore,
    vn_social_reputation_score: vnSocialReputationScore,
    vn_social_mentions_30d: hasMeaningfulRevenue ? 36 : 10,
    vn_social_sentiment: paidOnTime ? "positive" : "mixed",
    vn_social_complaint_count_30d: complaints,
    alternative_credit_score: alternativeCreditScore,
    confidence: hasMeaningfulRevenue ? 0.76 : 0.62,
    signals: [
      paidOnTime ? "on_time_payment_history" : "late_payment_review",
      hasMeaningfulRevenue ? "repeat_buyer_relationships" : "thin_network_history",
      itemCount >= 2 ? "structured_invoice_detail" : "limited_invoice_detail",
    ],
    explainability: buildCreditExplainability({
      alternativeCreditScore,
      trustGraphScore,
      repeatCounterpartyCount: hasMeaningfulRevenue ? 12 : 3,
      cashflowStabilityScore,
      vnSocialReputationScore,
      complaints,
      paidOnTime,
    }),
  };
}

function buildCapitalConnection(form) {
  const invoiceTotal = Number(form.get("invoice_total"));
  const paidOnTime = form.get("paid_on_time") === "on";
  const forecast = buildCashflowForecast(form);
  const recommendedAmount = forecast.recommended_credit_amount || Math.min(invoiceTotal, 30_000_000);
  const eligibilityStatus = paidOnTime && forecast.liquidity_risk_level !== "high" ? "prequalified" : "needs_review";
  const workingCapitalOffer = {
    offer_id: `mock_wc_${recommendedAmount}_6mo`,
    partner_name: "Mock Partner Bank A",
    product_type: "working_capital_loan",
    max_amount: recommendedAmount,
    term_months: 6,
    monthly_payment_estimate: Math.round((recommendedAmount * 1.06) / 6),
    premium_estimate: null,
    eligibility_status: eligibilityStatus,
    fit_score: paidOnTime ? 0.84 : 0.58,
    required_documents: ["recent_invoices", "bank_statement_snapshot"],
    reason: forecast.shortfall_amount
      ? "Matches the projected cash-buffer gap."
      : "Optional working-capital line for growth inventory.",
    next_step: paidOnTime ? "show_prequalified_terms" : "request_partner_review",
  };
  const insuranceOffer = {
    offer_id: "mock_inventory_cover_basic",
    partner_name: "Mock Insurance Partner B",
    product_type: "inventory_insurance",
    max_amount: Math.round(invoiceTotal * 1.5),
    term_months: 12,
    monthly_payment_estimate: null,
    premium_estimate: Math.max(250000, Math.round(invoiceTotal * 0.018)),
    eligibility_status: "eligible",
    fit_score: forecast.drivers.includes("positive_cash_buffer") ? 0.56 : 0.7,
    required_documents: ["inventory_photo", "recent_invoice"],
    reason: "Protects stock or seasonal inventory tied to upcoming sales.",
    next_step: "show_insurance_summary",
  };

  return {
    status: "matched",
    recommended_offer_id: workingCapitalOffer.offer_id,
    partner_offers: [workingCapitalOffer, insuranceOffer],
    smartbot_advice: {
      provider: "Smartbot",
      message: forecast.shortfall_amount
        ? `A short working-capital offer before ${forecast.shortfall_expected_date} may cover the projected cash gap without over-borrowing.`
        : "No urgent borrowing is required, but a small prequalified line can support planned inventory growth.",
      confidence: forecast.confidence,
      disclaimer: "Demo advisory output, not a binding credit decision.",
    },
    data_sharing_scope: ["business_profile", "cashflow_forecast", "recent_invoices"],
    consent_required: true,
  };
}

function buildCreditExplainability(profile) {
  const baselineScore = 55;
  const contributions = [
    {
      feature: "trust_graph_score",
      value: profile.trustGraphScore,
      shap_value: roundOne((profile.trustGraphScore - 0.5) * 22),
      direction: profile.trustGraphScore >= 0.5 ? "positive" : "negative",
      reason: "A stronger transaction graph improves confidence in real business activity.",
    },
    {
      feature: "repeat_counterparty_count",
      value: profile.repeatCounterpartyCount,
      shap_value: roundOne(Math.min(profile.repeatCounterpartyCount, 18) * 0.45),
      direction: "positive",
      reason: "Repeat counterparties show durable buyer or supplier relationships.",
    },
    {
      feature: "cashflow_stability_score",
      value: profile.cashflowStabilityScore,
      shap_value: roundOne((profile.cashflowStabilityScore - 0.5) * 18),
      direction: profile.cashflowStabilityScore >= 0.5 ? "positive" : "negative",
      reason: "Stable cashflow reduces short-term repayment uncertainty.",
    },
    {
      feature: "vn_social_reputation_score",
      value: profile.vnSocialReputationScore,
      shap_value: roundOne((profile.vnSocialReputationScore - 0.5) * 14),
      direction: profile.vnSocialReputationScore >= 0.5 ? "positive" : "negative",
      reason: "Positive public reputation supports business legitimacy.",
    },
    {
      feature: "vn_social_complaint_count_30d",
      value: profile.complaints,
      shap_value: roundOne(profile.complaints * -2.5),
      direction: profile.complaints ? "negative" : "neutral",
      reason: "Recent complaints reduce confidence and trigger review.",
    },
  ].sort((left, right) => Math.abs(right.shap_value) - Math.abs(left.shap_value));

  return {
    model_type: "gradient_boosted_trees",
    model_version: "grow_alt_credit_mock_v1",
    baseline_score: baselineScore,
    final_score: profile.alternativeCreditScore,
    reason_codes: contributions
      .filter((item) => item.direction === "positive")
      .slice(0, 3)
      .map((item) => item.feature),
    feature_contributions: contributions,
  };
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
