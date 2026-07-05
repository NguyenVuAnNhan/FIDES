const shieldForm = document.querySelector("#shield-form");
const shieldScenario = document.querySelector("#shield-scenario");
const shieldWizardSteps = document.querySelector("#shield-wizard-steps");
const shieldBack = document.querySelector("#shield-back");
const shieldNext = document.querySelector("#shield-next");
const shieldStatus = document.querySelector("#shield-status");
const shieldStepContextBody = document.querySelector("#shield-step-context-body");
const shieldStepChallengeBody = document.querySelector("#shield-step-challenge-body");
const shieldEkycSelfie = document.querySelector("#shield-ekyc-selfie");
const shieldEkycDocument = document.querySelector("#shield-ekyc-document");
const shieldEkycUploadStatus = document.querySelector("#shield-ekyc-upload-status");
const shieldSttAudio = document.querySelector("#shield-stt-audio");
const shieldAudioUploadStatus = document.querySelector("#shield-audio-upload-status");
const shieldRecordAudio = document.querySelector("#shield-record-audio");
const shieldStopRecordAudio = document.querySelector("#shield-stop-record-audio");
const shieldCameraPreview = document.querySelector("#shield-camera-preview");
const shieldCameraPlaceholder = document.querySelector("#shield-camera-placeholder");
const shieldStartCamera = document.querySelector("#shield-start-camera");
const shieldStartLiveCheck = document.querySelector("#shield-start-live-check");
const shieldStopLiveCheck = document.querySelector("#shield-stop-live-check");
const shieldLiveCheckStatus = document.querySelector("#shield-live-check-status");
const shieldFrameStrip = document.querySelector("#shield-frame-strip");

const WIZARD_STEPS = [
  { id: 1, nextLabel: "Analyze transfer" },
  { id: 2, nextLabel: "Run in-app check" },
  { id: 3, nextLabel: "Start new case" },
];

const LIVE_CHECK_SECONDS = 4;
const LIVE_FRAME_COUNT = 3;

let currentStep = 1;
let lastAnalyzeResponse = null;
let lastAnalyzePayload = null;
let uploadedEkycArtifacts = null;
let uploadedAudioArtifacts = null;
let uploadedLiveCheckArtifacts = null;
let audioRecorder = null;
let audioRecordChunks = [];
let cameraStream = null;
let liveCheckRecorder = null;
let liveCheckChunks = [];
let liveCheckTimer = null;
let liveCheckVideoBlob = null;
let liveCheckFrameBlobs = [];

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
    setShieldStatus(
      "Path B: analyze transfer context first. Step 2 records live camera + voice for VNPT checks.",
    );
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
    resetChallengeMedia();
    clearResultPanels();
    setWizardStep(1);
    setShieldStatus("Scenario loaded. Click Analyze transfer.");
  }
});

shieldBack.addEventListener("click", () => {
  if (currentStep > 1) {
    if (currentStep === 2) {
      stopCameraStream();
    }
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

if (shieldRecordAudio) {
  shieldRecordAudio.addEventListener("click", startAudioRecording);
}
if (shieldStopRecordAudio) {
  shieldStopRecordAudio.addEventListener("click", stopAudioRecording);
}
if (shieldStartCamera) {
  shieldStartCamera.addEventListener("click", startCameraPreview);
}
if (shieldStartLiveCheck) {
  shieldStartLiveCheck.addEventListener("click", startLiveCheckRecording);
}
if (shieldStopLiveCheck) {
  shieldStopLiveCheck.addEventListener("click", stopLiveCheckRecording);
}

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
        "Circuit breaker tripped. Enable camera, run the 4-second live check, then run in-app check.",
      );
      setWizardStep(2);
      await startCameraPreview();
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

  let challengeArtifacts;
  try {
    challengeArtifacts = await resolveChallengeArtifacts();
  } catch (error) {
    setShieldStatus(`Upload failed: ${formatApiError(error.message)}`);
    return;
  }

  shieldNext.disabled = true;
  setShieldStatus("Running in-app check via /api/shield/challenge...");

  try {
    const response = await postJson("/api/shield/challenge", {
      transaction: lastAnalyzePayload,
      ...challengeArtifacts,
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

async function resolveChallengeArtifacts() {
  if (liveCheckVideoBlob && liveCheckFrameBlobs.length > 0) {
    return resolveLiveCheckArtifacts();
  }

  const ekycArtifacts = await resolveEkycArtifacts();
  const audioArtifacts = await resolveAudioArtifacts();
  return {
    ...ekycArtifacts,
    ...audioArtifacts,
    challenge_video_ref: null,
    challenge_frame_refs: [],
  };
}

async function resolveLiveCheckArtifacts() {
  const documentFile = shieldEkycDocument?.files?.[0];
  const documentName = documentFile?.name || null;
  const cacheKey = [
    liveCheckVideoBlob.size,
    liveCheckFrameBlobs.length,
    documentName,
  ].join(":");

  if (uploadedLiveCheckArtifacts?.cacheKey === cacheKey) {
    return uploadedLiveCheckArtifacts.payload;
  }

  const formData = new FormData();
  const videoFile = new File([liveCheckVideoBlob], `live-check-${Date.now()}.webm`, {
    type: liveCheckVideoBlob.type || "video/webm",
  });
  formData.append("challenge_video", videoFile);
  if (documentFile) {
    formData.append("document", documentFile);
  }
  liveCheckFrameBlobs.forEach((frameBlob, index) => {
    formData.append(
      `frame_${index}`,
      new File([frameBlob], `frame-${index}.jpg`, { type: "image/jpeg" }),
    );
  });

  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = "Uploading live check to /api/shield/challenge/upload-live-check...";
  }
  if (shieldAudioUploadStatus) {
    shieldAudioUploadStatus.textContent = "Uploading live video + sampled frames...";
  }

  const uploadResponse = await postFormData("/api/shield/challenge/upload-live-check", formData);
  const payload = {
    ekyc_image_ref: uploadResponse.ekyc_image_ref,
    ekyc_document_ref: uploadResponse.ekyc_document_ref || null,
    stt_audio_ref: uploadResponse.stt_audio_ref,
    challenge_video_ref: uploadResponse.challenge_video_ref,
    challenge_frame_refs: uploadResponse.challenge_frame_refs || [],
  };

  uploadedLiveCheckArtifacts = { cacheKey, payload };
  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = `Live check uploaded (${uploadResponse.frame_count} frame(s), primary ${uploadResponse.primary_selfie_filename}).`;
  }
  if (shieldAudioUploadStatus) {
    shieldAudioUploadStatus.textContent = `Video ${uploadResponse.challenge_video_filename} · audio ref ${uploadResponse.stt_audio_ref}.`;
  }
  return payload;
}

function resetShieldCase() {
  lastAnalyzeResponse = null;
  lastAnalyzePayload = null;
  resetChallengeMedia();
  clearResultPanels();
  shieldScenario.dispatchEvent(new Event("change"));
  setWizardStep(1);
  setShieldStatus(
    "Path B: analyze transfer context first. Step 2 records live camera + voice for VNPT checks.",
  );
}

function resetChallengeMedia() {
  uploadedEkycArtifacts = null;
  uploadedAudioArtifacts = null;
  uploadedLiveCheckArtifacts = null;
  liveCheckVideoBlob = null;
  liveCheckFrameBlobs = [];
  clearLiveCheckTimer();
  stopLiveCheckRecording(true);
  stopCameraStream();
  resetFallbackInputs();
  renderFrameStrip([]);
  setLiveCheckStatus("Enable the camera, then start the live check.");
}

function resetFallbackInputs() {
  if (shieldEkycSelfie) {
    shieldEkycSelfie.value = "";
  }
  if (shieldEkycDocument) {
    shieldEkycDocument.value = "";
  }
  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = "";
  }
  if (shieldSttAudio) {
    shieldSttAudio.value = "";
  }
  if (shieldAudioUploadStatus) {
    shieldAudioUploadStatus.textContent = "";
  }
  if (shieldRecordAudio) {
    shieldRecordAudio.hidden = false;
  }
  if (shieldStopRecordAudio) {
    shieldStopRecordAudio.hidden = true;
  }
}

async function startCameraPreview() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setShieldStatus("This browser does not support live camera capture.");
    return;
  }

  try {
    stopCameraStream();
    cameraStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });

    if (shieldCameraPreview) {
      shieldCameraPreview.srcObject = cameraStream;
      shieldCameraPreview.hidden = false;
    }
    if (shieldCameraPlaceholder) {
      shieldCameraPlaceholder.hidden = true;
    }
    if (shieldStartCamera) {
      shieldStartCamera.textContent = "Restart camera";
    }
    if (shieldStartLiveCheck) {
      shieldStartLiveCheck.disabled = false;
    }
    setLiveCheckStatus("Camera ready. Start the 4-second live check when you are in frame.");
    setShieldStatus("Camera enabled. Start the live check in step 2.");
  } catch (error) {
    setShieldStatus(`Camera access failed: ${error.message}`);
    setLiveCheckStatus("Camera permission denied or unavailable.");
  }
}

function stopCameraStream() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  if (shieldCameraPreview) {
    shieldCameraPreview.srcObject = null;
    shieldCameraPreview.hidden = true;
  }
  if (shieldCameraPlaceholder) {
    shieldCameraPlaceholder.hidden = false;
  }
  if (shieldStartLiveCheck) {
    shieldStartLiveCheck.disabled = true;
  }
}

async function startLiveCheckRecording() {
  if (!cameraStream) {
    await startCameraPreview();
    if (!cameraStream) {
      return;
    }
  }

  uploadedLiveCheckArtifacts = null;
  liveCheckVideoBlob = null;
  liveCheckFrameBlobs = [];
  liveCheckChunks = [];

  const mimeType = pickRecorderMimeType();
  try {
    liveCheckRecorder = mimeType
      ? new MediaRecorder(cameraStream, { mimeType })
      : new MediaRecorder(cameraStream);
  } catch (error) {
    setShieldStatus(`Live recording failed: ${error.message}`);
    return;
  }

  liveCheckRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) {
      liveCheckChunks.push(event.data);
    }
  });
  liveCheckRecorder.addEventListener("stop", async () => {
    const blob = new Blob(liveCheckChunks, {
      type: liveCheckRecorder.mimeType || mimeType || "video/webm",
    });
    await finalizeLiveCheckRecording(blob);
  });

  liveCheckRecorder.start(250);
  if (shieldStartLiveCheck) {
    shieldStartLiveCheck.hidden = true;
  }
  if (shieldStopLiveCheck) {
    shieldStopLiveCheck.hidden = false;
  }
  clearLiveCheckTimer();
  let remaining = LIVE_CHECK_SECONDS;
  setLiveCheckStatus(`Recording live check… ${remaining}s remaining`);
  liveCheckTimer = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      stopLiveCheckRecording();
      return;
    }
    setLiveCheckStatus(`Recording live check… ${remaining}s remaining`);
  }, 1000);

  window.setTimeout(() => {
    if (liveCheckRecorder && liveCheckRecorder.state !== "inactive") {
      stopLiveCheckRecording();
    }
  }, LIVE_CHECK_SECONDS * 1000);
}

function stopLiveCheckRecording(silent = false) {
  clearLiveCheckTimer();
  if (liveCheckRecorder && liveCheckRecorder.state !== "inactive") {
    liveCheckRecorder.stop();
  }
  if (shieldStartLiveCheck) {
    shieldStartLiveCheck.hidden = false;
  }
  if (shieldStopLiveCheck) {
    shieldStopLiveCheck.hidden = true;
  }
  if (!silent && !liveCheckVideoBlob) {
    setLiveCheckStatus("Processing recorded clip…");
  }
}

function clearLiveCheckTimer() {
  if (liveCheckTimer) {
    window.clearInterval(liveCheckTimer);
    liveCheckTimer = null;
  }
}

async function finalizeLiveCheckRecording(videoBlob) {
  liveCheckVideoBlob = videoBlob;
  try {
    liveCheckFrameBlobs = await extractFramesFromVideoBlob(videoBlob, LIVE_FRAME_COUNT);
    renderFrameStrip(liveCheckFrameBlobs);
    setLiveCheckStatus(
      `Live check captured (${Math.round(videoBlob.size / 1024)} KB video, ${liveCheckFrameBlobs.length} frame sample(s)). Run in-app check when ready.`,
    );
    setShieldStatus("Live check ready. Click Run in-app check.");
  } catch (error) {
    liveCheckFrameBlobs = [];
    renderFrameStrip([]);
    setLiveCheckStatus(`Could not sample frames from the recording: ${error.message}`);
    setShieldStatus("Live check failed during frame sampling. Try again or use fallback uploads.");
  }
}

function pickRecorderMimeType() {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
    "video/mp4",
  ];
  if (!window.MediaRecorder?.isTypeSupported) {
    return "";
  }
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || "";
}

async function extractFramesFromVideoBlob(videoBlob, frameCount) {
  const url = URL.createObjectURL(videoBlob);
  const video = document.createElement("video");
  video.src = url;
  video.muted = true;
  video.playsInline = true;

  await new Promise((resolve, reject) => {
    video.addEventListener("loadedmetadata", resolve, { once: true });
    video.addEventListener("error", () => reject(new Error("Could not decode live-check video.")), {
      once: true,
    });
  });

  const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : LIVE_CHECK_SECONDS;
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const context = canvas.getContext("2d");
  if (!context) {
    URL.revokeObjectURL(url);
    throw new Error("Canvas is unavailable for frame sampling.");
  }

  const frames = [];
  for (let index = 0; index < frameCount; index += 1) {
    const timestamp = duration * (index + 1) / (frameCount + 1);
    await seekVideo(video, timestamp);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const frameBlob = await canvasToBlob(canvas, "image/jpeg", 0.9);
    frames.push(frameBlob);
  }

  URL.revokeObjectURL(url);
  return frames;
}

function seekVideo(video, timestamp) {
  return new Promise((resolve) => {
    const handleSeeked = () => {
      video.removeEventListener("seeked", handleSeeked);
      resolve();
    };
    video.addEventListener("seeked", handleSeeked);
    video.currentTime = Math.max(0, timestamp);
  });
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
          return;
        }
        reject(new Error("Failed to encode frame JPEG."));
      },
      type,
      quality,
    );
  });
}

function renderFrameStrip(frameBlobs) {
  if (!shieldFrameStrip) {
    return;
  }
  if (!frameBlobs.length) {
    shieldFrameStrip.hidden = true;
    shieldFrameStrip.innerHTML = "";
    return;
  }

  shieldFrameStrip.hidden = false;
  shieldFrameStrip.innerHTML = frameBlobs
    .map(
      (blob, index) =>
        `<img class="shield-frame-thumb" alt="Sampled frame ${index + 1}" src="${URL.createObjectURL(blob)}" />`,
    )
    .join("");
}

function setLiveCheckStatus(message) {
  if (shieldLiveCheckStatus) {
    shieldLiveCheckStatus.textContent = message;
  }
}

async function resolveAudioArtifacts() {
  const challengeFile = shieldSttAudio?.files?.[0];
  if (!challengeFile) {
    throw new Error("Record a live check or choose fallback challenge audio for VNPT SmartVoice.");
  }

  const challengeChanged = uploadedAudioArtifacts?.challengeFileName !== challengeFile.name;
  if (uploadedAudioArtifacts && !challengeChanged) {
    return {
      stt_audio_ref: uploadedAudioArtifacts.stt_audio_ref,
    };
  }

  const formData = new FormData();
  formData.append("challenge_audio", challengeFile);

  if (shieldAudioUploadStatus) {
    shieldAudioUploadStatus.textContent = "Uploading audio to /api/shield/challenge/upload-audio...";
  }

  const uploadResponse = await postFormData("/api/shield/challenge/upload-audio", formData);
  uploadedAudioArtifacts = {
    stt_audio_ref: uploadResponse.stt_audio_ref,
    challengeFileName: challengeFile.name,
  };

  if (shieldAudioUploadStatus) {
    shieldAudioUploadStatus.textContent = `Uploaded ${uploadResponse.challenge_filename}.`;
  }

  return {
    stt_audio_ref: uploadedAudioArtifacts.stt_audio_ref,
  };
}

async function startAudioRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setShieldStatus("This browser does not support microphone recording.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioRecordChunks = [];
    audioRecorder = new MediaRecorder(stream);
    audioRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        audioRecordChunks.push(event.data);
      }
    });
    audioRecorder.addEventListener("stop", () => {
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(audioRecordChunks, { type: audioRecorder.mimeType || "audio/webm" });
      const file = new File([blob], `challenge-recording-${Date.now()}.webm`, {
        type: blob.type || "audio/webm",
      });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      if (shieldSttAudio) {
        shieldSttAudio.files = transfer.files;
      }
      uploadedAudioArtifacts = null;
      if (shieldAudioUploadStatus) {
        shieldAudioUploadStatus.textContent = `Recorded ${file.name}. It will upload when you run the in-app check.`;
      }
      if (shieldRecordAudio) {
        shieldRecordAudio.hidden = false;
      }
      if (shieldStopRecordAudio) {
        shieldStopRecordAudio.hidden = true;
      }
    });
    audioRecorder.start();
    if (shieldRecordAudio) {
      shieldRecordAudio.hidden = true;
    }
    if (shieldStopRecordAudio) {
      shieldStopRecordAudio.hidden = false;
    }
    setShieldStatus("Recording fallback challenge audio. Stop when finished speaking.");
  } catch (error) {
    setShieldStatus(`Microphone access failed: ${error.message}`);
  }
}

function stopAudioRecording() {
  if (audioRecorder && audioRecorder.state !== "inactive") {
    audioRecorder.stop();
  }
}

async function resolveEkycArtifacts() {
  const selfieFile = shieldEkycSelfie?.files?.[0];
  if (!selfieFile) {
    throw new Error("Record a live check or choose a fallback selfie for VNPT eKYC.");
  }

  const documentFile = shieldEkycDocument?.files?.[0];
  const selfieChanged = uploadedEkycArtifacts?.selfieFileName !== selfieFile.name;
  const documentChanged = (uploadedEkycArtifacts?.documentFileName || null) !== (documentFile?.name || null);
  if (uploadedEkycArtifacts && !selfieChanged && !documentChanged) {
    return {
      ekyc_image_ref: uploadedEkycArtifacts.ekyc_image_ref,
      ekyc_document_ref: uploadedEkycArtifacts.ekyc_document_ref,
    };
  }

  const formData = new FormData();
  formData.append("selfie", selfieFile);
  if (documentFile) {
    formData.append("document", documentFile);
  }

  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = "Uploading images to /api/shield/challenge/upload-ekyc...";
  }

  const uploadResponse = await postFormData("/api/shield/challenge/upload-ekyc", formData);
  uploadedEkycArtifacts = {
    ekyc_image_ref: uploadResponse.ekyc_image_ref,
    ekyc_document_ref: uploadResponse.ekyc_document_ref || null,
    selfieFileName: selfieFile.name,
    documentFileName: documentFile?.name || null,
  };

  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = `Uploaded ${uploadResponse.selfie_filename}${
      uploadResponse.document_filename ? ` + ${uploadResponse.document_filename}` : ""
    }.`;
  }

  return {
    ekyc_image_ref: uploadedEkycArtifacts.ekyc_image_ref,
    ekyc_document_ref: uploadedEkycArtifacts.ekyc_document_ref,
  };
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
    payload.detected_patterns = parseList(form.get("detected_patterns"));
    payload.llm_scam_type = emptyToNull(form.get("llm_scam_type"));
    payload.llm_confidence = numberOrNull(form.get("llm_confidence"));
    payload.voice_stress_score = numberOrNull(form.get("voice_stress_score"));
    payload.voice_stress_labels = parseList(form.get("voice_stress_labels"));
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
    stopCameraStream();
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
