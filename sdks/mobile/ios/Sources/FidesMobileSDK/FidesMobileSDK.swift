import Foundation

public struct FidesConfig {
    public let baseUrl: String
    public let sdkSource: String

    public init(baseUrl: String, sdkSource: String = "fides_mobile_sdk") {
        self.baseUrl = baseUrl
        self.sdkSource = sdkSource
    }
}

public struct FidesConsent {
    public var telemetry: Bool
    public var audio: Bool
    public var partnerDataSharing: Bool

    public init(telemetry: Bool = false, audio: Bool = false, partnerDataSharing: Bool = false) {
        self.telemetry = telemetry
        self.audio = audio
        self.partnerDataSharing = partnerDataSharing
    }
}

public struct ShieldTransaction {
    public var amount: Int
    public var recipientName: String
    public var recipientAccount: String
    public var activeCall: Bool
    public var callerType: String
    public var callerNumber: String
    public var recipientKnown: Bool
    public var recipientPhone: String
    public var transcript: String

    public init(
        amount: Int,
        recipientName: String,
        recipientAccount: String,
        activeCall: Bool = false,
        callerType: String = "unknown",
        callerNumber: String = "",
        recipientKnown: Bool = false,
        recipientPhone: String = "",
        transcript: String = ""
    ) {
        self.amount = amount
        self.recipientName = recipientName
        self.recipientAccount = recipientAccount
        self.activeCall = activeCall
        self.callerType = callerType
        self.callerNumber = callerNumber
        self.recipientKnown = recipientKnown
        self.recipientPhone = recipientPhone
        self.transcript = transcript
    }
}

public struct FidesTelemetrySnapshot {
    public var nativeTelemetryAvailable: Bool
    public var nativeTelemetrySource: String
    public var installedRemoteAccessAppDetected: Bool
    public var accessibilityServiceRisk: Bool
    public var screenSharingDetected: Bool
    public var smartuxBehaviorAnomalyScore: Double?
    public var smartuxRemoteControlScore: Double?
    public var smartuxSignals: [String]
    public var sdkSessionId: String?

    public init(
        nativeTelemetryAvailable: Bool = false,
        nativeTelemetrySource: String = "fides_mobile_sdk",
        installedRemoteAccessAppDetected: Bool = false,
        accessibilityServiceRisk: Bool = false,
        screenSharingDetected: Bool = false,
        smartuxBehaviorAnomalyScore: Double? = nil,
        smartuxRemoteControlScore: Double? = nil,
        smartuxSignals: [String] = [],
        sdkSessionId: String? = nil
    ) {
        self.nativeTelemetryAvailable = nativeTelemetryAvailable
        self.nativeTelemetrySource = nativeTelemetrySource
        self.installedRemoteAccessAppDetected = installedRemoteAccessAppDetected
        self.accessibilityServiceRisk = accessibilityServiceRisk
        self.screenSharingDetected = screenSharingDetected
        self.smartuxBehaviorAnomalyScore = smartuxBehaviorAnomalyScore
        self.smartuxRemoteControlScore = smartuxRemoteControlScore
        self.smartuxSignals = smartuxSignals
        self.sdkSessionId = sdkSessionId
    }

    public func shieldFields() -> [String: Any] {
        [
            "native_telemetry_available": nativeTelemetryAvailable,
            "native_telemetry_source": nativeTelemetrySource,
            "installed_remote_access_app_detected": installedRemoteAccessAppDetected,
            "accessibility_service_risk": accessibilityServiceRisk,
            "screen_sharing_detected": screenSharingDetected,
            "smartux_behavior_anomaly_score": smartuxBehaviorAnomalyScore as Any,
            "smartux_remote_control_score": smartuxRemoteControlScore as Any,
            "smartux_signals": smartuxSignals,
            "smartux_session": [
                "provider": "FIDES Mobile SDK",
                "sdk_session_id": sdkSessionId as Any,
                "sdk_methods": ["snapshot", "buildShieldPayload", "analyzeShield", "challengeShield"]
            ]
        ]
    }
}

public protocol FidesTelemetryProvider {
    func snapshot(consent: FidesConsent) -> FidesTelemetrySnapshot
}

public protocol FidesHttpTransport {
    func postJSON(
        baseUrl: String,
        path: String,
        body: [String: Any],
        completion: @escaping (Result<Data, Error>) -> Void
    )
}

public final class FidesMobileSDK {
    private let config: FidesConfig
    private let telemetryProvider: FidesTelemetryProvider
    private let transport: FidesHttpTransport

    public init(
        config: FidesConfig,
        telemetryProvider: FidesTelemetryProvider,
        transport: FidesHttpTransport
    ) {
        self.config = config
        self.telemetryProvider = telemetryProvider
        self.transport = transport
    }

    public func buildShieldPayload(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: [String: Any] = [:]
    ) -> [String: Any] {
        var payload: [String: Any] = [
            "transaction_amount": transaction.amount,
            "recipient_name": transaction.recipientName,
            "recipient_account": transaction.recipientAccount,
            "active_call": transaction.activeCall,
            "caller_type": transaction.callerType,
            "caller_number": transaction.callerNumber,
            "recipient_known": transaction.recipientKnown,
            "recipient_phone": transaction.recipientPhone,
            "transcript": transaction.transcript,
            "consent_granted": consent.audio
        ]

        telemetryProvider.snapshot(consent: consent).shieldFields().forEach { payload[$0.key] = $0.value }
        overrides.forEach { payload[$0.key] = $0.value }
        return payload
    }

    public func analyzeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: [String: Any] = [:],
        completion: @escaping (Result<Data, Error>) -> Void
    ) {
        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/shield/analyze",
            body: buildShieldPayload(transaction: transaction, consent: consent, overrides: overrides),
            completion: completion
        )
    }

    public func challengeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: [String: Any] = [:],
        ekycImageRef: String,
        sttAudioRef: String = "mock_payload/stt_audio_1",
        completion: @escaping (Result<Data, Error>) -> Void
    ) {
        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/shield/challenge",
            body: [
                "transaction": buildShieldPayload(transaction: transaction, consent: consent, overrides: overrides),
                "ekyc_image_ref": ekycImageRef,
                "stt_audio_ref": sttAudioRef
            ],
            completion: completion
        )
    }

    public func analyzeGrow(
        payload: [String: Any],
        completion: @escaping (Result<Data, Error>) -> Void
    ) {
        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/grow/analyze-invoice",
            body: payload,
            completion: completion
        )
    }
}
