const shieldForm = document.querySelector("#shield-form");
const shieldSignals = document.querySelector("#shield-signals");
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
  { id: 1, nextLabel: "Confirm transfer" },
  { id: 2, nextLabel: "Verify & continue" },
  { id: 3, nextLabel: "New transfer" },
];

const LIVE_CHECK_SECONDS = 10;
const LIVE_FRAME_COUNT = 3;

const DEFAULT_TRANSFER = {
  transaction_amount: 65000000,
  recipient_name: "Tran Van B",
  recipient_account: "9704 2222 8800",
};

// Background context the mobile SDK would attach silently at transfer time.
const APP_SDK_CONTEXT = {
  active_call: true,
  caller_type: "unknown",
  caller_number: "+84 909 000 555",
  recipient_known: false,
  recipient_phone: "+84 909 000 555",
  vn_social_report_count: 0,
  vn_social_recent_keywords: [],
  simo_status: "not_checked",
  simo_last_checked_at: null,
  graph_risk_score: null,
  graph_pattern: null,
  inbound_sender_count_10m: 0,
  outbound_account_count_10m: 0,
  median_pass_through_minutes: null,
  account_age_days: null,
  shared_device_cluster_size: 0,
  funds_moved_within_minutes: false,
  recipient_risk_level: "unknown",
  remote_control_detected: false,
  native_telemetry_available: true,
  native_telemetry_source: "mock_android_sdk",
  installed_remote_access_app_detected: false,
  accessibility_service_risk: false,
  screen_sharing_detected: false,
  consent_call_monitoring: false,
  consent_transfer_check: false,
  smartux_behavior_anomaly_score: 0.22,
  smartux_remote_control_score: 0.08,
  smartux_signals: [],
};

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
let liveCheckAudioRecorder = null;
let liveCheckChunks = [];
let liveCheckAudioChunks = [];
let liveCheckTimer = null;
let liveCheckVideoBlob = null;
let liveCheckAudioBlob = null;
let liveCheckFrameBlobs = [];

initShieldPage();

function initShieldPage() {
  resetTransferForm();
  renderShieldSignals();
  setWizardStep(1);
  setShieldStatus(
    "Review the transfer and tap Confirm transfer. FIDES will score background signals automatically.",
  );
}

function resetTransferForm() {
  setFieldValue(shieldForm, "transaction_amount", DEFAULT_TRANSFER.transaction_amount);
  setFieldValue(shieldForm, "recipient_name", DEFAULT_TRANSFER.recipient_name);
  setFieldValue(shieldForm, "recipient_account", DEFAULT_TRANSFER.recipient_account);
}

function renderShieldSignals() {
  if (!shieldSignals) {
    return;
  }

  const callerLabel = formatValue(APP_SDK_CONTEXT.caller_type);
  const signals = [
    {
      title: "Active call detected",
      detail: `A phone call is in progress while you are transferring money. Caller: ${APP_SDK_CONTEXT.caller_number} (${callerLabel}).`,
      tone: "warn",
    },
    {
      title: "New recipient",
      detail: "This payee is not in your saved or recent transfer list.",
      tone: "warn",
    },
    {
      title: "Device telemetry attached",
      detail: "The banking app SDK sent session signals for remote-control and navigation checks.",
      tone: "neutral",
    },
  ];

  shieldSignals.innerHTML = signals
    .map(
      (signal) => `
        <div class="shield-signal ${signal.tone === "neutral" ? "is-neutral" : ""}">
          <strong>${escapeHtml(signal.title)}</strong>
          <span>${escapeHtml(signal.detail)}</span>
        </div>
      `,
    )
    .join("");
}

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
if (shieldEkycDocument) {
  shieldEkycDocument.addEventListener("change", () => {
    uploadedLiveCheckArtifacts = null;
    uploadedEkycArtifacts = null;
    updateLiveCheckButtonState();
  });
}

function hasCccdSelected() {
  return Boolean(shieldEkycDocument?.files?.[0]);
}

function updateLiveCheckButtonState() {
  if (!shieldStartLiveCheck) {
    return;
  }

  const recordingActive =
    (liveCheckRecorder && liveCheckRecorder.state !== "inactive") ||
    (liveCheckAudioRecorder && liveCheckAudioRecorder.state !== "inactive");
  if (recordingActive) {
    return;
  }

  const hasCccd = hasCccdSelected();
  const hasCamera = Boolean(cameraStream);
  shieldStartLiveCheck.disabled = !(hasCccd && hasCamera);

  if (liveCheckVideoBlob) {
    return;
  }
  if (!hasCccd && !hasCamera) {
    setLiveCheckStatus("Upload CCCD portrait, then enable the camera.");
  } else if (!hasCccd) {
    setLiveCheckStatus("Upload a CCCD portrait image to unlock the live check.");
  } else if (!hasCamera) {
    setLiveCheckStatus("CCCD ready. Enable the camera to start the live check.");
  } else {
    setLiveCheckStatus("Ready. Start the 10-second live check when you are in frame.");
  }
}

async function runShieldAnalyze() {
  const payload = buildShieldAnalyzePayload(new FormData(shieldForm));
  lastAnalyzePayload = payload;

  shieldNext.disabled = true;
  setShieldStatus("Checking transfer context...");

  try {
    lastAnalyzeResponse = await postJson("/api/shield/analyze", payload);
    renderContextResult(lastAnalyzeResponse);

    if (lastAnalyzeResponse.invasive_check_required) {
      setShieldStatus(
        "Extra verification required. Complete the identity check below.",
      );
      setWizardStep(2);
      await startCameraPreview();
    } else {
      setShieldStatus("Transfer cleared. No identity check needed.");
      setWizardStep(1);
      shieldNext.textContent = "New transfer";
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
  setShieldStatus("Running identity check...");

  try {
    const response = await postJson("/api/shield/challenge", {
      transaction: lastAnalyzePayload,
      ...challengeArtifacts,
      client_session: "shield-path-b-demo",
    });
    lastAnalyzeResponse = response;
    renderChallengeResult(response);
    setShieldStatus("Identity check complete. Review the decision below.");
    shieldNext.textContent = "New transfer";
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
  if (!documentFile) {
    throw new Error("Upload a CCCD portrait image before running the live check.");
  }
  const documentName = documentFile.name;
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
  if (liveCheckAudioBlob && liveCheckAudioBlob.size > 0) {
    formData.append(
      "challenge_audio",
      new File([liveCheckAudioBlob], `live-audio-${Date.now()}.webm`, {
        type: liveCheckAudioBlob.type || "audio/webm",
      }),
    );
  }
  formData.append("document", documentFile);
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
    ekyc_document_ref: uploadResponse.ekyc_document_ref,
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
  resetTransferForm();
  resetChallengeMedia();
  clearResultPanels();
  setWizardStep(1);
  setShieldStatus(
    "Review the transfer and tap Confirm transfer. FIDES will score background signals automatically.",
  );
}

function resetChallengeMedia() {
  uploadedEkycArtifacts = null;
  uploadedAudioArtifacts = null;
  uploadedLiveCheckArtifacts = null;
  liveCheckVideoBlob = null;
  liveCheckAudioBlob = null;
  liveCheckFrameBlobs = [];
  clearLiveCheckTimer();
  stopLiveCheckRecording(true);
  stopCameraStream();
  resetFallbackInputs();
  renderFrameStrip([]);
  setLiveCheckStatus("Upload CCCD portrait, then enable the camera.");
  updateLiveCheckButtonState();
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
    updateLiveCheckButtonState();
    setShieldStatus("Camera enabled. Start the live check in step 2.");
  } catch (error) {
    setShieldStatus(`Camera access failed: ${error.message}`);
    setLiveCheckStatus("Camera permission denied or unavailable.");
    updateLiveCheckButtonState();
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
  updateLiveCheckButtonState();
}

async function startLiveCheckRecording() {
  if (!hasCccdSelected()) {
    setShieldStatus("Upload a CCCD portrait image before starting the live check.");
    setLiveCheckStatus("CCCD portrait is required for VNPT face compare.");
    updateLiveCheckButtonState();
    return;
  }

  if (!cameraStream) {
    await startCameraPreview();
    if (!cameraStream) {
      return;
    }
  }

  uploadedLiveCheckArtifacts = null;
  liveCheckVideoBlob = null;
  liveCheckAudioBlob = null;
  liveCheckFrameBlobs = [];
  liveCheckChunks = [];
  liveCheckAudioChunks = [];

  const mimeType = pickRecorderMimeType();
  const audioMimeType = pickAudioMimeType();
  try {
    liveCheckRecorder = mimeType
      ? new MediaRecorder(cameraStream, { mimeType })
      : new MediaRecorder(cameraStream);
  } catch (error) {
    setShieldStatus(`Live recording failed: ${error.message}`);
    setLiveCheckStatus(`Could not start video recorder: ${error.message}`);
    updateLiveCheckButtonState();
    return;
  }

  liveCheckAudioRecorder = null;
  const audioTracks = cameraStream.getAudioTracks();
  if (audioTracks.length > 0) {
    try {
      const audioStream = new MediaStream(audioTracks);
      liveCheckAudioRecorder = audioMimeType
        ? new MediaRecorder(audioStream, { mimeType: audioMimeType })
        : new MediaRecorder(audioStream);
    } catch (error) {
      console.warn("Parallel audio recorder unavailable; STT will use video audio.", error);
      liveCheckAudioRecorder = null;
    }
  }

  let audioStopPromise = Promise.resolve();
  if (liveCheckAudioRecorder) {
    liveCheckAudioRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        liveCheckAudioChunks.push(event.data);
      }
    });
    audioStopPromise = new Promise((resolve) => {
      liveCheckAudioRecorder.addEventListener(
        "stop",
        () => {
          liveCheckAudioBlob = new Blob(liveCheckAudioChunks, {
            type: liveCheckAudioRecorder.mimeType || audioMimeType || "audio/webm",
          });
          resolve();
        },
        { once: true },
      );
    });
  } else {
    liveCheckAudioBlob = null;
  }

  liveCheckRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) {
      liveCheckChunks.push(event.data);
    }
  });
  liveCheckRecorder.addEventListener("stop", async () => {
    await audioStopPromise;
    const blob = new Blob(liveCheckChunks, {
      type: liveCheckRecorder.mimeType || mimeType || "video/webm",
    });
    await finalizeLiveCheckRecording(blob);
  });

  liveCheckRecorder.start(250);
  if (liveCheckAudioRecorder) {
    try {
      liveCheckAudioRecorder.start(250);
    } catch (error) {
      console.warn("Audio track recording failed; continuing with video only.", error);
      liveCheckAudioRecorder = null;
    }
  }
  if (shieldStartLiveCheck) {
    shieldStartLiveCheck.hidden = true;
    shieldStartLiveCheck.disabled = true;
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
  if (liveCheckAudioRecorder && liveCheckAudioRecorder.state !== "inactive") {
    liveCheckAudioRecorder.stop();
  }
  if (liveCheckRecorder && liveCheckRecorder.state !== "inactive") {
    liveCheckRecorder.stop();
  }
  if (shieldStartLiveCheck) {
    shieldStartLiveCheck.hidden = false;
  }
  if (shieldStopLiveCheck) {
    shieldStopLiveCheck.hidden = true;
  }
  updateLiveCheckButtonState();
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
      `Live check captured (${Math.round(videoBlob.size / 1024)} KB video${
        liveCheckAudioBlob ? `, ${Math.round(liveCheckAudioBlob.size / 1024)} KB audio` : ""
      }, ${liveCheckFrameBlobs.length} frame sample(s)). Tap Verify & continue when ready.`,
    );
    setShieldStatus("Live check ready. Tap Verify & continue.");
    updateLiveCheckButtonState();
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

function pickAudioMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
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
        shieldAudioUploadStatus.textContent = `Recorded ${file.name}. It will upload when you verify.`;
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
  if (!documentFile) {
    throw new Error("Upload a CCCD portrait image for VNPT face compare.");
  }
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
  formData.append("document", documentFile);

  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = "Uploading images to /api/shield/challenge/upload-ekyc...";
  }

  const uploadResponse = await postFormData("/api/shield/challenge/upload-ekyc", formData);
  uploadedEkycArtifacts = {
    ekyc_image_ref: uploadResponse.ekyc_image_ref,
    ekyc_document_ref: uploadResponse.ekyc_document_ref,
    selfieFileName: selfieFile.name,
    documentFileName: documentFile.name,
  };

  if (shieldEkycUploadStatus) {
    shieldEkycUploadStatus.textContent = `Uploaded ${uploadResponse.selfie_filename} + ${uploadResponse.document_filename}.`;
  }

  return {
    ekyc_image_ref: uploadedEkycArtifacts.ekyc_image_ref,
    ekyc_document_ref: uploadedEkycArtifacts.ekyc_document_ref,
  };
}

function buildShieldAnalyzePayload(form) {
  return {
    transaction_amount: Number(form.get("transaction_amount")),
    recipient_name: String(form.get("recipient_name")),
    recipient_account: String(form.get("recipient_account")),
    ...APP_SDK_CONTEXT,
    shield_path: String(form.get("shield_path") || "transfer_monitoring"),
    ekyc_verification_status: "not_checked",
    ekyc_liveness_passed: null,
    ekyc_liveness_score: null,
    ekyc_mask_detected: false,
    ekyc_face_match_score: null,
    ekyc_injection_risk_score: null,
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
}

function renderContextResult(result) {
  shieldStepContextBody.innerHTML = renderShieldResult(result, "Transfer review");
}

function renderChallengeResult(result) {
  shieldStepChallengeBody.innerHTML = renderShieldResult(result, "Final decision");
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
    updateLiveCheckButtonState();
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
