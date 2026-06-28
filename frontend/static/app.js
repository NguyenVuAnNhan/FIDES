const shieldForm = document.querySelector("#shield-form");
const growForm = document.querySelector("#grow-form");
const shieldResult = document.querySelector("#shield-result");
const growResult = document.querySelector("#grow-result");

shieldForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(shieldForm);
  const payload = {
    transaction_amount: Number(form.get("transaction_amount")),
    recipient_name: String(form.get("recipient_name")),
    recipient_account: String(form.get("recipient_account")),
    active_call: form.get("active_call") === "on",
    caller_type: String(form.get("caller_type")),
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
    items: [
      { description: "Goods and services", amount: Number(form.get("invoice_total")) },
    ],
  };

  growResult.className = "result empty";
  growResult.textContent = "Analyzing Grow profile...";
  const response = await postJson("/api/grow/analyze-invoice", payload);
  growResult.className = "result";
  growResult.innerHTML = renderGrow(response);
});

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

function formatValue(value) {
  return String(value).replaceAll("_", " ");
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

