async function loadDemoDataset() {
  const response = await fetch("/api/demo/dataset");
  if (!response.ok) {
    throw new Error("Dataset request failed");
  }

  window.fidesDemoDataset = await response.json();
  return window.fidesDemoDataset;
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

async function postFormData(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText);
  }

  return response.json();
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

function markActiveNavLink() {
  const page = document.body.dataset.page;
  document.querySelectorAll(".topbar nav a[data-nav]").forEach((link) => {
    link.classList.toggle("active", link.dataset.nav === page);
  });
}

document.addEventListener("DOMContentLoaded", markActiveNavLink);
