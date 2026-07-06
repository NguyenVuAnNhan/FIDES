const callAudioInput = document.querySelector("#call-audio");
const callAnalyzeButton = document.querySelector("#call-analyze");
const callStatus = document.querySelector("#call-status");
const callResult = document.querySelector("#call-result");
const callGuardian = document.querySelector("#call-guardian");
const callUploadLabel = document.querySelector("#call-upload-label");

if (callAudioInput) {
  callAudioInput.addEventListener("change", () => {
    const file = callAudioInput.files?.[0];
    if (callUploadLabel) {
      callUploadLabel.textContent = file
        ? `Đã chọn: ${file.name} (${Math.round(file.size / 1024)} KB)`
        : "Chưa chọn file audio.";
    }
  });
}

const SCAM_PATTERN_LABELS = {
  fake_authority: "Giả danh cơ quan",
  otp_theft: "Lấy cắp OTP",
  investment: "Dụ đầu tư",
  remote_support: "Điều khiển từ xa",
};

// Smartbot returns free-form pattern codes (e.g. `otp_or_password_request`),
// so translate by keyword to keep the chip consistent with the headline.
function patternLabel(raw) {
  const code = String(raw || "").toLowerCase();
  if (/otp|password|mat.?khau|ma.?xac.?thuc|pin/.test(code)) return "Lấy cắp OTP/mật khẩu";
  if (/remote|screen|man.?hinh|dieu.?khien|teamviewer|anydesk|ultraview/.test(code))
    return "Điều khiển màn hình từ xa";
  if (/invest|loi.?nhuan|dau.?tu/.test(code)) return "Dụ đầu tư lợi nhuận cao";
  if (/authority|cong.?an|police|vien.?kiem.?sat|co.?quan|toa.?an/.test(code))
    return "Giả danh cơ quan chức năng";
  return SCAM_PATTERN_LABELS[code] || raw.replace(/_/g, " ");
}

const RISK_PILL_CLASS = {
  high: "critical",
  medium: "elevated",
  low: "low",
};

const RISK_LABELS = {
  high: "Nguy cơ cao",
  medium: "Nguy cơ trung bình",
  low: "An toàn",
};

if (callAnalyzeButton) {
  callAnalyzeButton.addEventListener("click", analyzeCall);
}

async function analyzeCall() {
  const file = callAudioInput?.files?.[0];
  if (!file) {
    callStatus.textContent = "Chọn một file audio cuộc gọi trước.";
    return;
  }

  callStatus.textContent = "Đang chạy SmartVoice STT + SmartBot phân loại...";
  callAnalyzeButton.disabled = true;
  callGuardian.innerHTML = "";
  resetResult(callResult, "Đang phân tích...");

  try {
    const formData = new FormData();
    formData.append("call_audio", file);
    formData.append("client_session", `web-call-${Date.now()}`);
    const response = await postFormData("/api/shield/call-listen", formData);
    renderResult(response);
    callStatus.textContent = response.is_scam
      ? "Phát hiện dấu hiệu lừa đảo."
      : "Đã phân tích xong.";
  } catch (error) {
    resetResult(callResult, "");
    callResult.classList.remove("empty");
    callResult.innerHTML = `<p style="color:#dc2626;font-weight:600;">Lỗi phân tích</p><p class="stage-muted">${escapeHtml(
      String(error.message || error),
    )}</p>`;
    callStatus.textContent = "Phân tích thất bại.";
  } finally {
    callAnalyzeButton.disabled = false;
  }
}

function renderResult(res) {
  callResult.classList.remove("empty");

  const scam = res.is_scam;
  const heroClass = scam ? "thin_file" : "strong";
  const ringValue = scam
    ? res.confidence != null
      ? `${Math.round(res.confidence * 100)}%`
      : "!"
    : "OK";
  const ringLabel = scam ? "Nguy cơ" : "An toàn";
  const headline = scam ? "Phát hiện dấu hiệu lừa đảo" : "Không thấy dấu hiệu lừa đảo";

  const riskPill = `<span class="pill ${RISK_PILL_CLASS[res.risk_level] || "low"}">${
    RISK_LABELS[res.risk_level] || res.risk_level
  }</span>`;
  const confidencePill =
    res.confidence != null
      ? `<span class="pill">Độ tin cậy ${Math.round(res.confidence * 100)}%</span>`
      : "";
  const typePill = scam
    ? `<span class="pill critical">${escapeHtml(res.scam_type_label || "Lừa đảo")}</span>`
    : "";

  const transcriptStage = res.stt_transcript
    ? `<div class="grow-stage">
         <h4>Nội dung nghe được · SmartVoice STT</h4>
         <div class="stage-card wide-stage">
           <span>“${escapeHtml(res.stt_transcript)}”</span>
         </div>
         ${
           (res.detected_patterns || []).length
             ? `<div class="metric-row" style="margin-top:12px;">${res.detected_patterns
                 .map((p) => `<span class="pill critical">${escapeHtml(patternLabel(p))}</span>`)
                 .join("")}</div>`
             : ""
         }
       </div>`
    : "";

  callResult.innerHTML = `
    <div class="score-hero ${heroClass}">
      <div class="score-ring">
        <span class="score-value">${ringValue}</span>
        <span class="score-label">${ringLabel}</span>
      </div>
      <div class="score-meta">
        <p class="grow-summary" style="font-weight:800;font-size:17px;color:var(--ink);">${headline}</p>
        <div class="metric-row">${riskPill}${confidencePill}${typePill}</div>
        <p class="grow-summary">${escapeHtml(res.intervention_message || "")}</p>
      </div>
    </div>
    ${transcriptStage}
    ${renderExplanations(res.explanations || [])}
    <p class="stage-muted" style="margin-top:10px;font-size:12px;">Provider: ${escapeHtml(res.provider_mode || "")}</p>
  `;

  if (res.guardian_alert) {
    renderGuardian(res);
  }
}

function renderGuardian(res) {
  callGuardian.innerHTML = `
    <div class="score-hero emerging" style="margin-top:18px;">
      <div class="score-ring"><span class="score-value">SOS</span><span class="score-label">Giám hộ</span></div>
      <div class="score-meta">
        <p class="grow-summary" style="font-weight:800;color:#92400e;">Đã gửi cảnh báo cho người giám hộ</p>
        <p class="grow-summary">${escapeHtml(res.guardian_message || "")}</p>
        <p class="stage-muted" style="font-size:12px;">Mô phỏng: thông báo push/SMS tới người thân đã đăng ký.</p>
        <div class="wizard-inline-actions" id="call-guardian-actions">
          <button type="button" class="wizard-next" id="guardian-approve">Xác nhận an toàn</button>
          <button type="button" class="wizard-secondary" id="guardian-reject">Chặn &amp; khoá giao dịch</button>
        </div>
        <p id="call-guardian-outcome" style="margin:0;font-weight:700;"></p>
      </div>
    </div>
  `;

  const outcome = document.querySelector("#call-guardian-outcome");
  const actions = document.querySelector("#call-guardian-actions");
  document.querySelector("#guardian-approve")?.addEventListener("click", () => {
    actions.hidden = true;
    outcome.style.color = "#059669";
    outcome.textContent = "✓ Người giám hộ đã xác nhận đây là giao dịch hợp lệ. Cảnh báo được gỡ.";
  });
  document.querySelector("#guardian-reject")?.addEventListener("click", () => {
    actions.hidden = true;
    outcome.style.color = "#dc2626";
    outcome.textContent =
      "⛔ Người giám hộ đã chặn. Giao dịch bị khoá 24h và FIDES đã báo bộ phận chống lừa đảo của ngân hàng.";
  });
}
