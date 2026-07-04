const shieldForm = document.querySelector("#shield-form");
const growForm = document.querySelector("#grow-form");
const shieldScenario = document.querySelector("#shield-scenario");
const growScenario = document.querySelector("#grow-scenario");
const shieldResult = document.querySelector("#shield-result");
const growResult = document.querySelector("#grow-result");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
let activeGrowItems = [];
let lastShieldPayload = null;

loadDemoDataset();

shieldScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("shield_scenarios", shieldScenario.value);
  if (selected) {
    fillForm(shieldForm, selected.payload);
    resetResult(shieldResult, "Run Shield analysis to see risk and intervention.");
  }
});

growScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("grow_invoices", growScenario.value);
  if (selected) {
    activeGrowItems = selected.payload.items;
    fillForm(growForm, selected.payload);
    fillGrowNestedFields(selected.payload);
    updateGrowReceiptPreview(selected.payload.input_source);
    resetResult(growResult, "Run Grow analysis to see credit readiness.");
  }
});

shieldForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = buildShieldPayload(new FormData(shieldForm));
  lastShieldPayload = payload;

  shieldResult.className = "result empty";
  shieldResult.textContent = "Analyzing Shield risk...";
  const response = await postJson("/api/shield/analyze", payload);
  shieldResult.className = "result";
  shieldResult.innerHTML = renderShield(response);
});

shieldResult.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-shield-challenge]");
  if (!button) {
    return;
  }

  button.disabled = true;
  await runShieldChallenge();
});

async function runShieldChallenge() {
  const payload = lastShieldPayload ?? buildShieldPayload(new FormData(shieldForm));
  const ekycImageRef = shieldResult.querySelector("[data-shield-ekyc-ref]")?.value ?? "mock_payload/ekyc_img_1";
  const sttAudioRef = shieldResult.querySelector("[data-shield-audio-ref]")?.value ?? "mock_payload/stt_audio_1";
  const challengeRequest = {
    transaction: payload,
    ekyc_image_ref: ekycImageRef,
    ekyc_document_ref: ekycImageRef,
    stt_audio_ref: sttAudioRef,
    client_session: "shield-demo-browser-session",
  };

  shieldResult.className = "result empty";
  shieldResult.textContent = "Running camera and voice challenge...";
  const response = await postJson("/api/shield/challenge", challengeRequest);
  lastShieldPayload = payload;
  shieldResult.className = "result";
  shieldResult.innerHTML = renderShield(response);
}

function buildShieldPayload(form) {
  return {
    transaction_amount: Number(form.get("transaction_amount")),
    recipient_name: String(form.get("recipient_name")),
    recipient_account: String(form.get("recipient_account")),
    active_call: form.get("active_call") === "on",
    caller_type: String(form.get("caller_type")),
    caller_number: String(form.get("caller_number")),
    recipient_known: form.get("recipient_known") === "on",
    recipient_phone: String(form.get("recipient_phone")),
    vn_social_report_count: Number(form.get("vn_social_report_count")),
    vn_social_recent_keywords: parseList(form.get("vn_social_recent_keywords")),
    simo_status: String(form.get("simo_status")),
    simo_last_checked_at: emptyToNull(form.get("simo_last_checked_at")),
    graph_risk_score: numberOrNull(form.get("graph_risk_score")),
    graph_pattern: emptyToNull(form.get("graph_pattern")),
    inbound_sender_count_10m: Number(form.get("inbound_sender_count_10m")),
    outbound_account_count_10m: Number(form.get("outbound_account_count_10m")),
    median_pass_through_minutes: numberOrNull(form.get("median_pass_through_minutes")),
    account_age_days: numberOrNull(form.get("account_age_days")),
    shared_device_cluster_size: Number(form.get("shared_device_cluster_size")),
    funds_moved_within_minutes: form.get("funds_moved_within_minutes") === "on",
    recipient_risk_level: String(form.get("recipient_risk_level")),
    remote_control_detected: form.get("remote_control_detected") === "on",
    native_telemetry_available: form.get("native_telemetry_available") === "on",
    native_telemetry_source: emptyToNull(form.get("native_telemetry_source")),
    installed_remote_access_app_detected: form.get("installed_remote_access_app_detected") === "on",
    accessibility_service_risk: form.get("accessibility_service_risk") === "on",
    screen_sharing_detected: form.get("screen_sharing_detected") === "on",
    ekyc_verification_status: String(form.get("ekyc_verification_status")),
    ekyc_liveness_score: numberOrNull(form.get("ekyc_liveness_score")),
    ekyc_mask_detected: form.get("ekyc_mask_detected") === "on",
    ekyc_face_match_score: numberOrNull(form.get("ekyc_face_match_score")),
    ekyc_injection_risk_score: numberOrNull(form.get("ekyc_injection_risk_score")),
    smartux_behavior_anomaly_score: numberOrNull(form.get("smartux_behavior_anomaly_score")),
    smartux_remote_control_score: numberOrNull(form.get("smartux_remote_control_score")),
    smartux_signals: parseList(form.get("smartux_signals")),
    consent_granted: form.get("consent_granted") === "on",
    audio_source: emptyToNull(form.get("audio_source")),
    stt_transcript: String(form.get("stt_transcript")),
    stt_confidence: numberOrNull(form.get("stt_confidence")),
    detected_patterns: parseList(form.get("detected_patterns")),
    llm_scam_type: emptyToNull(form.get("llm_scam_type")),
    llm_confidence: numberOrNull(form.get("llm_confidence")),
    voice_stress_score: numberOrNull(form.get("voice_stress_score")),
    voice_stress_labels: parseList(form.get("voice_stress_labels")),
    face_emotion_score: numberOrNull(form.get("face_emotion_score")),
    face_emotion_labels: parseList(form.get("face_emotion_labels")),
    scripted_behavior_score: numberOrNull(form.get("scripted_behavior_score")),
    scripted_behavior_labels: parseList(form.get("scripted_behavior_labels")),
    coercion_score: numberOrNull(form.get("coercion_score")),
    coercion_confidence: numberOrNull(form.get("coercion_confidence")),
    transcript: String(form.get("transcript")),
  };
}

growForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(growForm);
  const payload = {
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

  growResult.className = "result empty";
  growResult.textContent = "Analyzing Grow profile...";
  const response = await postJson("/api/grow/analyze-invoice", payload);
  growResult.className = "result";
  growResult.innerHTML = renderGrow(response);
});

growForm.elements.namedItem("input_source").addEventListener("input", (event) => {
  updateGrowReceiptPreview(event.target.value);
});

async function loadDemoDataset() {
  try {
    const response = await fetch("/api/demo/dataset");
    if (!response.ok) {
      throw new Error("Dataset request failed");
    }

    window.fidesDemoDataset = await response.json();
    populateScenarioSelect(shieldScenario, window.fidesDemoDataset.shield_scenarios);
    populateScenarioSelect(growScenario, window.fidesDemoDataset.grow_invoices);
    shieldScenario.dispatchEvent(new Event("change"));
    growScenario.dispatchEvent(new Event("change"));
  } catch (error) {
    console.error(error);
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText);
  }

  return response.json();
}

function renderShield(result) {
  return `
    <div class="metric-row">
      <span class="pill ${result.risk_level}">Risk ${result.risk_score}/100</span>
      <span class="pill ${result.risk_level}">${formatValue(result.risk_level)}</span>
      <span class="pill">${formatValue(result.action)}</span>
    </div>
    ${renderShieldCircuitBreaker(result)}
    <p>${escapeHtml(result.intervention_message)}</p>
    ${renderShieldChallengeAction(result)}
    ${renderTrustedAuthorityNotice(result)}
    ${renderExplanations(result.explanations)}
    ${renderProviderResponses(result.provider_raw_responses ?? result.mock_provider_raw_responses, result.provider_mode)}
  `;
}

function renderProviderResponses(responses, providerMode = "mock") {
  const entries = Object.entries(responses ?? {});
  if (!entries.length) {
    return "";
  }

  return `
    <details class="provider-json">
      <summary>${providerMode === "real" ? "VNPT provider JSON" : "Mock VNPT provider JSON"}</summary>
      ${entries
        .map(
          ([name, payload]) => `
            <div class="provider-json-block">
              <strong>${escapeHtml(name)}</strong>
              <pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
            </div>
          `,
        )
        .join("")}
    </details>
  `;
}

function renderShieldChallengeAction(result) {
  if (result.action !== "require_camera_voice_check") {
    return "";
  }

  return `
    <div class="challenge-actions">
      <label class="challenge-field">
        eKYC image payload
        <select data-shield-ekyc-ref>
          <option value="mock_payload/ekyc_img_1">ekyc_img_1 · passes eKYC</option>
          <option value="mock_payload/ekyc_img_2">ekyc_img_2 · fails eKYC</option>
        </select>
      </label>
      <label class="challenge-field">
        STT audio payload
        <select data-shield-audio-ref>
          <option value="mock_payload/stt_audio_1">stt_audio_1 · passes STT</option>
          <option value="mock_payload/stt_audio_2">stt_audio_2 · fails STT</option>
        </select>
      </label>
      <button type="button" class="secondary-button" data-shield-challenge="run">
        Submit Camera/Voice Challenge
      </button>
    </div>
  `;
}

function renderShieldCircuitBreaker(result) {
  const stageTwoScore = result.stage_two_score === null || result.stage_two_score === undefined
    ? "Pending"
    : `${result.stage_two_score}/100`;
  const stageTwoLabel = result.invasive_check_required
    ? "Camera and voice check required"
    : result.stage_two_score === null || result.stage_two_score === undefined
      ? "Not needed"
      : "Camera and voice check complete";

  return `
    <div class="stage-grid">
      <div class="stage-card">
        <strong>Stage 1 · outer circuit</strong>
        <span>${result.stage_one_score ?? result.risk_score}/100 · ${result.circuit_breaker_triggered ? "tripped" : "clear"}</span>
      </div>
      <div class="stage-card">
        <strong>Stage 2 · invasive challenge</strong>
        <span>${stageTwoScore} · ${stageTwoLabel}</span>
      </div>
      <div class="stage-card wide-stage">
        <strong>Decision stage</strong>
        <span>${formatValue(result.circuit_breaker_stage ?? "outer_context")}</span>
      </div>
    </div>
  `;
}

function renderTrustedAuthorityNotice(result) {
  if (!result.trusted_authority_notification) {
    return "";
  }

  return `
    <div class="authority-note">
      <strong>Hold ${result.transaction_hold_hours || 24}h · trusted authority notified</strong>
      <span>${escapeHtml(result.trusted_authority_message ?? "")}</span>
    </div>
  `;
}

function renderGrow(result) {
  return `
    <div class="metric-row">
      <span class="pill ${result.credit_band}">Trust ${result.trust_score}/100</span>
      <span class="pill ${result.credit_band}">${formatValue(result.credit_band)}</span>
      <span class="pill">${formatMoney(result.monthly_revenue_estimate)}/mo</span>
    </div>
    <p>${escapeHtml(result.recommended_action)}</p>
    ${renderExplanations(result.explanations)}
  `;
}

function renderExplanations(explanations) {
  if (!explanations.length) {
    return "";
  }

  return `
    <div class="explanations">
      ${explanations
        .map(
          (item) => `
            <div class="explanation">
              <strong>${escapeHtml(item.label)} · ${item.weight}</strong>
              <span>${escapeHtml(item.detail)}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function populateScenarioSelect(select, items) {
  select.innerHTML = items
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)}</option>`)
    .join("");
}

function getSelectedDemoItem(collectionName, id) {
  return window.fidesDemoDataset?.[collectionName]?.find((item) => item.id === id);
}

function fillForm(form, payload) {
  Object.entries(payload).forEach(([name, value]) => {
    const field = form.elements.namedItem(name);
    if (!field || name === "items") {
      return;
    }

    if (field.type === "checkbox") {
      field.checked = Boolean(value);
      return;
    }

    field.value = Array.isArray(value) ? value.join(", ") : value ?? "";
  });
}

function resetResult(element, text) {
  element.className = "result empty";
  element.textContent = text;
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

function setFieldValue(form, name, value) {
  const field = form.elements.namedItem(name);
  if (!field) {
    return;
  }
  field.value = value ?? "";
}

function formatValue(value) {
  return String(value).replaceAll("_", " ");
}

function emptyToNull(value) {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function numberOrNull(value) {
  const text = String(value ?? "").trim();
  return text ? Number(text) : null;
}

function roundOne(value) {
  return Math.round(value * 10) / 10;
}

function parseList(value) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatMoney(value) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
