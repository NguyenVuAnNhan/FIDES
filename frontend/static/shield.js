const shieldForm = document.querySelector("#shield-form");
const shieldScenario = document.querySelector("#shield-scenario");
const shieldResult = document.querySelector("#shield-result");

initShieldPage();

async function initShieldPage() {
  try {
    await loadDemoDataset();
    populateScenarioSelect(shieldScenario, window.fidesDemoDataset.shield_scenarios);
    shieldScenario.dispatchEvent(new Event("change"));
  } catch (error) {
    console.error(error);
    resetResult(shieldResult, "Failed to load Shield demo scenarios.");
  }
}

shieldScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("shield_scenarios", shieldScenario.value);
  if (selected) {
    fillForm(shieldForm, selected.payload);
    resetResult(shieldResult, "Run Shield analysis to see risk and intervention.");
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
  try {
    const response = await postJson("/api/shield/analyze", payload);
    shieldResult.className = "result";
    shieldResult.innerHTML = renderShield(response);
  } catch (error) {
    shieldResult.className = "result empty";
    shieldResult.textContent = `Shield analysis failed: ${error.message}`;
  }
});

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
