const shieldForm = document.querySelector("#shield-form");
const growForm = document.querySelector("#grow-form");
const shieldScenario = document.querySelector("#shield-scenario");
const growScenario = document.querySelector("#grow-scenario");
const shieldResult = document.querySelector("#shield-result");
const growResult = document.querySelector("#grow-result");
const growReceiptPreview = document.querySelector("#grow-receipt-preview");
let activeGrowItems = [];

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
  const form = new FormData(shieldForm);
  const payload = {
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

  shieldResult.className = "result empty";
  shieldResult.textContent = "Analyzing Shield risk...";
  const response = await postJson("/api/shield/analyze", payload);
  shieldResult.className = "result";
  shieldResult.innerHTML = renderShield(response);
});

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
    <p>${escapeHtml(result.intervention_message)}</p>
    ${renderExplanations(result.explanations)}
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
