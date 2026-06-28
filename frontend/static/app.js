const shieldForm = document.querySelector("#shield-form");
const growForm = document.querySelector("#grow-form");
const shieldScenario = document.querySelector("#shield-scenario");
const growScenario = document.querySelector("#grow-scenario");
const shieldResult = document.querySelector("#shield-result");
const growResult = document.querySelector("#grow-result");
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
    remote_control_detected: form.get("remote_control_detected") === "on",
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
    business_name: String(form.get("business_name")),
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
