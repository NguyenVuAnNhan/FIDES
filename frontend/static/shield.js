const shieldForm = document.querySelector("#shield-form");
const shieldScenario = document.querySelector("#shield-scenario");
const shieldWizardSteps = document.querySelector("#shield-wizard-steps");
const shieldBack = document.querySelector("#shield-back");
const shieldNext = document.querySelector("#shield-next");
const shieldStatus = document.querySelector("#shield-status");
const shieldStepContextBody = document.querySelector("#shield-step-context-body");
const shieldStepChallengeBody = document.querySelector("#shield-step-challenge-body");
const shieldChallengeProfile = document.querySelector("#shield-challenge-profile");

const WIZARD_STEPS = [
  { id: 1, nextLabel: "Analyze transfer" },
  { id: 2, nextLabel: "Run in-app check" },
  { id: 3, nextLabel: "Start new case" },
];

const CHALLENGE_PROFILES = {
  pass: {
    ekyc_image_ref: "mock_payload/ekyc_img_1",
    ekyc_document_ref: "mock_payload/customer_document_faces/doc_face_1",
    stt_audio_ref: "mock_payload/stt_audio_1",
    voice_reference_ref: "mock_payload/customer_voice_samples/voice_ref_1",
  },
  fail_scam: {
    ekyc_image_ref: "mock_payload/ekyc_img_1",
    ekyc_document_ref: "mock_payload/customer_document_faces/doc_face_1",
    stt_audio_ref: "mock_payload/stt_audio_2",
    voice_reference_ref: "mock_payload/customer_voice_samples/voice_ref_1",
  },
  fail_biometric: {
    ekyc_image_ref: "mock_payload/ekyc_img_2",
    ekyc_document_ref: "mock_payload/customer_document_faces/doc_face_2",
    stt_audio_ref: "mock_payload/stt_audio_1",
    voice_reference_ref: "mock_payload/customer_voice_samples/voice_ref_1",
  },
};

let currentStep = 1;
let lastAnalyzeResponse = null;
let lastAnalyzePayload = null;

initShieldPage();

async function initShieldPage() {
  try {
    await loadDemoDataset();
    populateScenarioSelect(shieldScenario, window.fidesDemoDataset.shield_scenarios);
    if (shieldScenario.querySelector('option[value="shield-stage-one-challenge-required"]')) {
      shieldScenario.value = "shield-stage-one-challenge-required";
    }
    shieldScenario.dispatchEvent(new Event("change"));
    setWizardStep(1);
    setShieldStatus("Path B: analyze transfer context first. In-app check runs in step 2 when required.");
  } catch (error) {
    console.error(error);
    setShieldStatus("Failed to load Shield demo scenarios.");
  }
}

shieldScenario.addEventListener("change", () => {
  const selected = getSelectedDemoItem("shield_scenarios", shieldScenario.value);
  if (selected) {
    fillForm(shieldForm, selected.payload);
    const callMonitoring = shieldForm.elements.namedItem("consent_call_monitoring");
    if (callMonitoring && selected.id === "shield-stage-one-challenge-required") {
      callMonitoring.checked = false;
    }
    lastAnalyzeResponse = null;
    lastAnalyzePayload = null;
    clearResultPanels();
    setWizardStep(1);
    setShieldStatus("Scenario loaded. Click Analyze transfer.");
  }
});

shieldBack.addEventListener("click", () => {
  if (currentStep > 1) {
    setWizardStep(currentStep - 1);
  }
});

shieldNext.addEventListener("click", async () => {
  if (currentStep === 1) {
    await runShieldAnalyze();
    return;
  }

  if (currentStep === 2) {
    await runShieldChallenge();
    return;
  }

  resetShieldCase();
});

shieldForm.addEventListener("submit", (event) => {
  event.preventDefault();
});

async function runShieldAnalyze() {
  const payload = buildShieldAnalyzePayload(new FormData(shieldForm));
  lastAnalyzePayload = payload;

  shieldNext.disabled = true;
  setShieldStatus("Analyzing transfer context (Path B stage 1)...");

  try {
    lastAnalyzeResponse = await postJson("/api/shield/analyze", payload);
    renderContextResult(lastAnalyzeResponse);

    if (lastAnalyzeResponse.invasive_check_required) {
      setShieldStatus(
        "Circuit breaker tripped. Continue to in-app camera and voice check (step 2).",
      );
      setWizardStep(2);
    } else {
      setShieldStatus("Analysis complete. No in-app check required for this scenario.");
      setWizardStep(1);
      shieldNext.textContent = "Start new case";
      currentStep = 3;
      updateWizardChrome();
    }
  } catch (error) {
    setShieldStatus(`Shield analysis failed: ${formatApiError(error.message)}`);
  } finally {
    shieldNext.disabled = false;
  }
}

async function runShieldChallenge() {
  if (!lastAnalyzePayload) {
    setShieldStatus("Run transfer analysis first.");
    return;
  }

  const profileKey = shieldChallengeProfile?.value || "pass";
  const artifacts = CHALLENGE_PROFILES[profileKey] || CHALLENGE_PROFILES.pass;

  shieldNext.disabled = true;
  setShieldStatus("Running in-app check via /api/shield/challenge...");

  try {
    const response = await postJson("/api/shield/challenge", {
      transaction: lastAnalyzePayload,
      ...artifacts,
      client_session: "shield-path-b-demo",
    });
    lastAnalyzeResponse = response;
    renderChallengeResult(response);
    setShieldStatus("In-app check complete. Review final decision below.");
    shieldNext.textContent = "Start new case";
    currentStep = 3;
    updateWizardChrome();
  } catch (error) {
    setShieldStatus(`Challenge failed: ${formatApiError(error.message)}`);
  } finally {
    shieldNext.disabled = false;
  }
}

function resetShieldCase() {
  lastAnalyzeResponse = null;
  lastAnalyzePayload = null;
  clearResultPanels();
  shieldScenario.dispatchEvent(new Event("change"));
  setWizardStep(1);
  setShieldStatus("Path B: analyze transfer context first.");
}

function buildShieldAnalyzePayload(form) {
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
    consent_call_monitoring: form.get("consent_call_monitoring") === "on",
    consent_transfer_check: false,
    shield_path: String(form.get("shield_path") || "transfer_monitoring"),
    ekyc_verification_status: "not_checked",
    ekyc_liveness_passed: null,
    ekyc_liveness_score: null,
    ekyc_mask_detected: false,
    ekyc_face_match_score: null,
    ekyc_injection_risk_score: null,
    smartux_behavior_anomaly_score: numberOrNull(form.get("smartux_behavior_anomaly_score")),
    smartux_remote_control_score: numberOrNull(form.get("smartux_remote_control_score")),
    smartux_signals: parseList(form.get("smartux_signals")),
    consent_granted: false,
    audio_source: null,
    stt_transcript: "",
    stt_confidence: null,
    voice_reference_source: null,
    voice_verification_status: "not_checked",
    voice_match_score: null,
    voice_match_threshold: null,
    detected_patterns: [],
    llm_scam_type: null,
    llm_confidence: null,
    voice_stress_score: null,
    voice_stress_labels: [],
    face_emotion_score: null,
    face_emotion_labels: [],
    scripted_behavior_score: null,
    scripted_behavior_labels: [],
    coercion_score: null,
    coercion_confidence: null,
    transcript: "",
  };

  if (shieldScenario.value !== "shield-stage-one-challenge-required") {
    payload.ekyc_verification_status = String(form.get("ekyc_verification_status"));
    payload.ekyc_liveness_score = numberOrNull(form.get("ekyc_liveness_score"));
    payload.ekyc_mask_detected = form.get("ekyc_mask_detected") === "on";
    payload.ekyc_face_match_score = numberOrNull(form.get("ekyc_face_match_score"));
    payload.ekyc_injection_risk_score = numberOrNull(form.get("ekyc_injection_risk_score"));
    payload.consent_granted = form.get("consent_granted") === "on";
    payload.audio_source = emptyToNull(form.get("audio_source"));
    payload.stt_transcript = String(form.get("stt_transcript"));
    payload.stt_confidence = numberOrNull(form.get("stt_confidence"));
    payload.voice_reference_source = emptyToNull(form.get("voice_reference_source"));
    payload.voice_verification_status = String(form.get("voice_verification_status"));
    payload.voice_match_score = numberOrNull(form.get("voice_match_score"));
    payload.voice_match_threshold = numberOrNull(form.get("voice_match_threshold"));
    payload.detected_patterns = parseList(form.get("detected_patterns"));
    payload.llm_scam_type = emptyToNull(form.get("llm_scam_type"));
    payload.llm_confidence = numberOrNull(form.get("llm_confidence"));
    payload.voice_stress_score = numberOrNull(form.get("voice_stress_score"));
    payload.voice_stress_labels = parseList(form.get("voice_stress_labels"));
    payload.face_emotion_score = numberOrNull(form.get("face_emotion_score"));
    payload.face_emotion_labels = parseList(form.get("face_emotion_labels"));
    payload.scripted_behavior_score = numberOrNull(form.get("scripted_behavior_score"));
    payload.scripted_behavior_labels = parseList(form.get("scripted_behavior_labels"));
    payload.coercion_score = numberOrNull(form.get("coercion_score"));
    payload.coercion_confidence = numberOrNull(form.get("coercion_confidence"));
    payload.transcript = String(form.get("transcript"));
  }

  return payload;
}

function renderContextResult(result) {
  shieldStepContextBody.innerHTML = renderShieldResult(result, "Stage 1 context analysis");
}

function renderChallengeResult(result) {
  shieldStepChallengeBody.innerHTML = renderShieldResult(result, "Final decision after in-app check");
}

function renderShieldResult(result, heading) {
  const stageTwo =
    result.stage_two_score != null ? ` · stage 2 ${result.stage_two_score}` : "";
  return `
    <div class="grow-stage">
      <h4>${escapeHtml(heading)}</h4>
      <div class="metric-row">
        <span class="pill ${result.risk_level}">Risk ${result.risk_score}/100</span>
        <span class="pill ${result.risk_level}">${escapeHtml(formatValue(result.risk_level))}</span>
        <span class="pill">${escapeHtml(formatValue(result.action))}</span>
      </div>
      <p class="stage-muted">
        ${escapeHtml(formatValue(result.circuit_breaker_stage))}
        · stage 1 ${result.stage_one_score}${stageTwo}
        ${result.challenge_profile ? ` · profile ${escapeHtml(result.challenge_profile)}` : ""}
      </p>
      <p class="grow-summary">${escapeHtml(result.intervention_message)}</p>
      ${renderExplanations(result.explanations)}
    </div>
  `;
}

function setWizardStep(step) {
  currentStep = step;
  updateWizardChrome();

  shieldForm.querySelectorAll(".wizard-panel").forEach((panel) => {
    const panelStep = Number(panel.dataset.step);
    const isActive = panelStep === step;
    panel.classList.toggle("is-active", isActive);
    panel.hidden = !isActive;
  });

  if (step === 1) {
    shieldNext.textContent = WIZARD_STEPS[0].nextLabel;
  } else if (step === 2) {
    shieldNext.textContent = WIZARD_STEPS[1].nextLabel;
  }
}

function updateWizardChrome() {
  const activeWizardStep = currentStep > 2 ? 2 : currentStep;

  shieldWizardSteps.querySelectorAll(".wizard-step").forEach((item) => {
    const itemStep = Number(item.dataset.step);
    item.classList.toggle("is-active", itemStep === activeWizardStep);
    item.classList.toggle("is-complete", itemStep < activeWizardStep && lastAnalyzeResponse != null);
  });

  shieldBack.disabled = activeWizardStep === 1;

  if (currentStep === 3) {
    shieldNext.textContent = WIZARD_STEPS[2].nextLabel;
    shieldBack.disabled = false;
  } else if (currentStep === 2 && !lastAnalyzeResponse?.invasive_check_required) {
    shieldNext.disabled = true;
  } else {
    shieldNext.disabled = false;
  }
}

function clearResultPanels() {
  shieldStepContextBody.innerHTML = "";
  shieldStepChallengeBody.innerHTML = "";
}

function setShieldStatus(message) {
  shieldStatus.textContent = message;
}

function formatApiError(message) {
  try {
    const parsed = JSON.parse(message);
    if (parsed && typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch (_error) {
    // Keep original message.
  }
  return message;
}
