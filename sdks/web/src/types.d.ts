export type FidesConsent = {
  telemetry?: boolean;
  audio?: boolean;
  partnerDataSharing?: boolean;
};

export type FidesWebSdkOptions = {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  sessionId?: string;
  sdkSource?: string;
  consent?: FidesConsent;
};

export type ShieldTransactionInput = {
  transaction_amount?: number;
  amount?: number;
  recipient_name?: string;
  recipientName?: string;
  recipient_account?: string;
  recipientAccount?: string;
  active_call?: boolean;
  caller_type?: string;
  caller_number?: string;
  recipient_known?: boolean;
  recipient_phone?: string;
  transcript?: string;
  consent_granted?: boolean;
};

export type ShieldChallengeOptions = Record<string, unknown> & {
  challenge_profile?: "clear_user" | "coerced_authority" | "deepfake_injection" | "scripted_remote_support";
  spoken_response?: string;
};

export type TelemetrySnapshot = {
  native_telemetry_available: boolean;
  native_telemetry_source: string;
  installed_remote_access_app_detected?: boolean;
  accessibility_service_risk?: boolean;
  screen_sharing_detected?: boolean;
  smartux_behavior_anomaly_score: number | null;
  smartux_remote_control_score: number | null;
  smartux_signals: string[];
  smartux_session?: Record<string, unknown>;
};

export declare function createFidesWebSdk(options?: FidesWebSdkOptions): FidesWebSdk;
export declare function deriveSignals(events: Array<Record<string, unknown>>): string[];
export declare function deriveBehaviorScore(events: Array<Record<string, unknown>>, signals?: string[]): number;
export declare function deriveRemoteControlScore(signals: string[]): number;

export declare class FidesWebSdk {
  constructor(options?: FidesWebSdkOptions);
  setConsent(consent?: FidesConsent): FidesConsent;
  getConsent(): FidesConsent;
  recordEvent(type: string, details?: Record<string, unknown>): Record<string, unknown>;
  attachDefaultListeners(root?: Document): () => void;
  buildTelemetrySnapshot(overrides?: Record<string, unknown>): TelemetrySnapshot;
  buildShieldPayload(transaction: ShieldTransactionInput, overrides?: Record<string, unknown>): Record<string, unknown>;
  analyzeShield(transaction: ShieldTransactionInput, overrides?: Record<string, unknown>): Promise<Record<string, unknown>>;
  challengeShield(transaction: ShieldTransactionInput, options?: ShieldChallengeOptions): Promise<Record<string, unknown>>;
  analyzeGrow(payload: Record<string, unknown>): Promise<Record<string, unknown>>;
  postJson(path: string, payload: Record<string, unknown>): Promise<Record<string, unknown>>;
}
