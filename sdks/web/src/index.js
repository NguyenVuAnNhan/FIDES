const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

export function createFidesWebSdk(options = {}) {
  return new FidesWebSdk(options);
}

export class FidesWebSdk {
  constructor(options = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl || DEFAULT_BASE_URL);
    this.fetchImpl = options.fetchImpl || globalThis.fetch?.bind(globalThis);
    this.sessionId = options.sessionId || createSessionId();
    this.sdkSource = options.sdkSource || "fides_web_sdk";
    this.consent = {
      telemetry: false,
      audio: false,
      partnerDataSharing: false,
      ...(options.consent || {}),
    };
    this.events = [];

    if (!this.fetchImpl) {
      throw new Error("FIDES Web SDK requires fetch or options.fetchImpl.");
    }
  }

  setConsent(consent = {}) {
    this.consent = { ...this.consent, ...consent };
    return this.getConsent();
  }

  getConsent() {
    return { ...this.consent };
  }

  recordEvent(type, details = {}) {
    const event = {
      type,
      details: { ...details },
      at: new Date().toISOString(),
    };
    this.events.push(event);
    if (this.events.length > 200) {
      this.events.shift();
    }
    return event;
  }

  attachDefaultListeners(root = globalThis.document) {
    if (!root?.addEventListener) {
      return () => {};
    }

    const onPaste = (event) => {
      const name = event.target?.getAttribute?.("name") || "";
      this.recordEvent("paste", { field: name });
    };
    const onFocus = (event) => {
      const name = event.target?.getAttribute?.("name") || "";
      this.recordEvent("focus", { field: name });
    };
    const onBlur = (event) => {
      const name = event.target?.getAttribute?.("name") || "";
      this.recordEvent("blur", { field: name });
    };
    const onPointerMove = () => this.recordEvent("pointer_move");
    const onPointerMoveThrottled = throttle(onPointerMove, 500);
    const onVisibility = () => this.recordEvent("visibility_change", { hidden: root.hidden });

    root.addEventListener("paste", onPaste, true);
    root.addEventListener("focus", onFocus, true);
    root.addEventListener("blur", onBlur, true);
    root.addEventListener("pointermove", onPointerMoveThrottled, true);
    root.addEventListener("visibilitychange", onVisibility, true);

    return () => {
      root.removeEventListener("paste", onPaste, true);
      root.removeEventListener("focus", onFocus, true);
      root.removeEventListener("blur", onBlur, true);
      root.removeEventListener("pointermove", onPointerMoveThrottled, true);
      root.removeEventListener("visibilitychange", onVisibility, true);
    };
  }

  buildTelemetrySnapshot(overrides = {}) {
    if (!this.consent.telemetry) {
      return {
        native_telemetry_available: false,
        native_telemetry_source: this.sdkSource,
        smartux_behavior_anomaly_score: null,
        smartux_remote_control_score: null,
        smartux_signals: [],
        ...overrides,
      };
    }

    const signals = deriveSignals(this.events);
    return {
      native_telemetry_available: true,
      native_telemetry_source: this.sdkSource,
      installed_remote_access_app_detected: false,
      accessibility_service_risk: false,
      screen_sharing_detected: false,
      smartux_behavior_anomaly_score: deriveBehaviorScore(this.events, signals),
      smartux_remote_control_score: deriveRemoteControlScore(signals),
      smartux_signals: signals,
      smartux_session: {
        provider: "FIDES Web SDK",
        sdk_session_id: this.sessionId,
        tracked_event_count: this.events.length,
        last_event_at: this.events.at(-1)?.at || null,
        sdk_methods: ["recordEvent", "attachDefaultListeners", "buildTelemetrySnapshot"],
      },
      ...overrides,
    };
  }

  buildShieldPayload(transaction, overrides = {}) {
    return {
      transaction_amount: Number(transaction.transaction_amount ?? transaction.amount ?? 0),
      recipient_name: String(transaction.recipient_name ?? transaction.recipientName ?? ""),
      recipient_account: String(transaction.recipient_account ?? transaction.recipientAccount ?? ""),
      active_call: Boolean(transaction.active_call ?? false),
      caller_type: String(transaction.caller_type ?? "unknown"),
      caller_number: String(transaction.caller_number ?? ""),
      recipient_known: Boolean(transaction.recipient_known ?? false),
      recipient_phone: String(transaction.recipient_phone ?? ""),
      transcript: String(transaction.transcript ?? ""),
      consent_granted: Boolean(transaction.consent_granted ?? this.consent.audio),
      ...this.buildTelemetrySnapshot(),
      ...overrides,
    };
  }

  async analyzeShield(transaction, overrides = {}) {
    return this.postJson("/api/shield/analyze", this.buildShieldPayload(transaction, overrides));
  }

  async challengeShield(transaction, options = {}) {
    const {
      ekyc_image_ref,
      ekyc_document_ref = null,
      stt_audio_ref,
      client_session = "fides-sdk-session",
      ...payloadOverrides
    } = options;
    if (!ekyc_image_ref) {
      throw new Error("ekyc_image_ref is required. Upload via POST /api/shield/challenge/upload-ekyc first.");
    }
    if (!stt_audio_ref) {
      throw new Error("stt_audio_ref is required. Upload via POST /api/shield/challenge/upload-audio first.");
    }
    return this.postJson("/api/shield/challenge", {
      transaction: this.buildShieldPayload(transaction, payloadOverrides),
      ekyc_image_ref,
      ekyc_document_ref,
      stt_audio_ref,
      client_session,
    });
  }

  async analyzeGrow(payload) {
    return this.postJson("/api/grow/analyze-invoice", payload);
  }

  async postJson(path, payload) {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }
}

export function deriveSignals(events) {
  const recent = events.slice(-50);
  const signals = new Set();
  const pasteFields = recent.filter((event) => event.type === "paste").map((event) => event.details.field);
  const focusEvents = recent.filter((event) => event.type === "focus" || event.type === "blur");
  const pointerMoves = recent.filter((event) => event.type === "pointer_move");
  const visibilityChanges = recent.filter((event) => event.type === "visibility_change");

  if (pasteFields.some((field) => /amount/i.test(field))) {
    signals.add("paste_into_amount_field");
  }
  if (pasteFields.some((field) => /otp|code|pin/i.test(field))) {
    signals.add("paste_into_otp_field");
  }
  if (focusEvents.length >= 12) {
    signals.add("rapid_focus_switching");
  }
  if (pointerMoves.length >= 20) {
    signals.add("rapid_pointer_jumps");
  }
  if (visibilityChanges.length >= 3) {
    signals.add("unusual_navigation_sequence");
  }

  return [...signals];
}

export function deriveBehaviorScore(events, signals = deriveSignals(events)) {
  const base = Math.min(events.length / 80, 0.3);
  const signalWeight = Math.min(signals.length * 0.16, 0.64);
  return round2(Math.min(base + signalWeight, 1));
}

export function deriveRemoteControlScore(signals) {
  const risky = ["rapid_pointer_jumps", "paste_into_amount_field", "rapid_focus_switching"];
  const count = signals.filter((signal) => risky.includes(signal)).length;
  return round2(Math.min(count * 0.26, 1));
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl).replace(/\/$/, "");
}

function createSessionId() {
  const random = Math.random().toString(36).slice(2, 10);
  return `fides-web-${Date.now()}-${random}`;
}

function throttle(fn, waitMs) {
  let last = 0;
  return (...args) => {
    const now = Date.now();
    if (now - last >= waitMs) {
      last = now;
      fn(...args);
    }
  };
}

function round2(value) {
  return Math.round(value * 100) / 100;
}
