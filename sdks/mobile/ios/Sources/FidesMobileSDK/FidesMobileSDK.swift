import Foundation

public struct FidesConfig {
    public let baseUrl: String
    public let sdkSource: String
    public let shieldPath: String

    public init(
        baseUrl: String,
        sdkSource: String = "fides_mobile_sdk",
        shieldPath: String = "transfer_monitoring"
    ) {
        self.baseUrl = baseUrl
        self.sdkSource = sdkSource
        self.shieldPath = shieldPath
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
    public var remoteControlDetected: Bool
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
        remoteControlDetected: Bool = false,
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
        self.remoteControlDetected = remoteControlDetected
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
            "remote_control_detected": remoteControlDetected,
            "smartux_behavior_anomaly_score": smartuxBehaviorAnomalyScore as Any,
            "smartux_remote_control_score": smartuxRemoteControlScore as Any,
            "smartux_signals": smartuxSignals,
        ]
    }
}

public struct MultipartPart {
    public let fieldName: String
    public let filename: String
    public let contentType: String
    public let data: Data

    public init(fieldName: String, filename: String, contentType: String, data: Data) {
        self.fieldName = fieldName
        self.filename = filename
        self.contentType = contentType
        self.data = data
    }
}

public struct LiveCheckFramePart {
    public let index: Int
    public let jpegData: Data
    public let filename: String

    public init(index: Int, jpegData: Data, filename: String? = nil) {
        self.index = index
        self.jpegData = jpegData
        self.filename = filename ?? "frame-\(index).jpg"
    }
}

public struct LiveCheckUploadInput {
    public let challengeVideo: Data
    public let challengeVideoFilename: String
    public let challengeVideoContentType: String
    public let document: Data
    public let documentFilename: String
    public let documentContentType: String
    public let challengeAudio: Data?
    public let challengeAudioFilename: String?
    public let challengeAudioContentType: String
    public let frames: [LiveCheckFramePart]

    public init(
        challengeVideo: Data,
        challengeVideoFilename: String,
        challengeVideoContentType: String = "video/webm",
        document: Data,
        documentFilename: String,
        documentContentType: String = "image/jpeg",
        challengeAudio: Data? = nil,
        challengeAudioFilename: String? = nil,
        challengeAudioContentType: String = "audio/webm",
        frames: [LiveCheckFramePart] = []
    ) {
        self.challengeVideo = challengeVideo
        self.challengeVideoFilename = challengeVideoFilename
        self.challengeVideoContentType = challengeVideoContentType
        self.document = document
        self.documentFilename = documentFilename
        self.documentContentType = documentContentType
        self.challengeAudio = challengeAudio
        self.challengeAudioFilename = challengeAudioFilename
        self.challengeAudioContentType = challengeAudioContentType
        self.frames = frames
    }
}

public struct LiveCheckUploadResponse {
    public let ekycImageRef: String
    public let ekycDocumentRef: String
    public let sttAudioRef: String
    public let challengeVideoRef: String
    public let challengeFrameRefs: [String]
    public let frameCount: Int
}

public struct ShieldChallengeArtifacts {
    public let ekycImageRef: String
    public let ekycDocumentRef: String
    public let sttAudioRef: String
    public let challengeVideoRef: String?
    public let challengeFrameRefs: [String]

    public init(
        ekycImageRef: String,
        ekycDocumentRef: String,
        sttAudioRef: String,
        challengeVideoRef: String? = nil,
        challengeFrameRefs: [String] = []
    ) {
        self.ekycImageRef = ekycImageRef
        self.ekycDocumentRef = ekycDocumentRef
        self.sttAudioRef = sttAudioRef
        self.challengeVideoRef = challengeVideoRef
        self.challengeFrameRefs = challengeFrameRefs
    }
}

public struct ShieldExplanation {
    public let label: String
    public let detail: String
    public let weight: Int
}

public struct ShieldAnalyzeResponse {
    public let riskScore: Int
    public let riskLevel: String
    public let action: String
    public let circuitBreakerStage: String
    public let circuitBreakerTriggered: Bool
    public let invasiveCheckRequired: Bool
    public let stageOneScore: Int
    public let stageTwoScore: Int?
    public let interventionMessage: String
    public let scamType: String?
    public let challengeProfile: String?
    public let explanations: [ShieldExplanation]

    public var requiresIdentityCheck: Bool {
        invasiveCheckRequired || action == "require_camera_voice_check"
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

    func postMultipart(
        baseUrl: String,
        path: String,
        parts: [MultipartPart],
        completion: @escaping (Result<Data, Error>) -> Void
    )
}

public final class DefaultFidesTelemetryProvider: FidesTelemetryProvider {
    private let sdkSource: String
    private let sessionId: String

    public init(sdkSource: String = "fides_mobile_sdk", sessionId: String? = nil) {
        self.sdkSource = sdkSource
        self.sessionId = sessionId ?? "fides-ios-\(Int(Date().timeIntervalSince1970 * 1000))"
    }

    public func snapshot(consent: FidesConsent) -> FidesTelemetrySnapshot {
        guard consent.telemetry else {
            return FidesTelemetrySnapshot(
                nativeTelemetryAvailable: false,
                nativeTelemetrySource: sdkSource,
                sdkSessionId: sessionId
            )
        }
        return FidesTelemetrySnapshot(
            nativeTelemetryAvailable: true,
            nativeTelemetrySource: sdkSource,
            smartuxBehaviorAnomalyScore: 0.22,
            smartuxRemoteControlScore: 0.08,
            sdkSessionId: sessionId
        )
    }
}

public enum ShieldPayloadBuilder {
    public static func pathBDefaults(config: FidesConfig, consent: FidesConsent) -> [String: Any] {
        [
            "shield_path": config.shieldPath,
            "consent_call_monitoring": false,
            "consent_transfer_check": false,
            "consent_granted": consent.audio,
            "vn_social_report_count": 0,
            "vn_social_recent_keywords": [] as [String],
            "simo_status": "not_checked",
            "simo_last_checked_at": NSNull(),
            "graph_risk_score": NSNull(),
            "graph_pattern": NSNull(),
            "inbound_sender_count_10m": 0,
            "outbound_account_count_10m": 0,
            "median_pass_through_minutes": NSNull(),
            "account_age_days": NSNull(),
            "shared_device_cluster_size": 0,
            "funds_moved_within_minutes": false,
            "recipient_risk_level": "unknown",
            "ekyc_verification_status": "not_checked",
            "ekyc_liveness_passed": NSNull(),
            "ekyc_liveness_score": NSNull(),
            "ekyc_mask_detected": false,
            "ekyc_face_match_score": NSNull(),
            "ekyc_injection_risk_score": NSNull(),
            "audio_source": NSNull(),
            "stt_transcript": "",
            "stt_confidence": NSNull(),
            "detected_patterns": [] as [String],
            "llm_scam_type": NSNull(),
            "llm_confidence": NSNull(),
            "voice_stress_score": NSNull(),
            "voice_stress_labels": [] as [String],
            "face_emotion_score": NSNull(),
            "face_emotion_labels": [] as [String],
            "scripted_behavior_score": NSNull(),
            "scripted_behavior_labels": [] as [String],
            "coercion_score": NSNull(),
            "coercion_confidence": NSNull(),
            "transcript": "",
        ]
    }

    public static func buildAnalyzePayload(
        transaction: ShieldTransaction,
        config: FidesConfig,
        consent: FidesConsent,
        telemetry: FidesTelemetrySnapshot,
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
        ]
        pathBDefaults(config: config, consent: consent).forEach { payload[$0.key] = $0.value }
        telemetry.shieldFields().forEach { payload[$0.key] = $0.value }
        overrides.forEach { payload[$0.key] = $0.value }
        return payload
    }

    public static func buildChallengePayload(
        transactionPayload: [String: Any],
        artifacts: ShieldChallengeArtifacts,
        clientSession: String
    ) -> [String: Any] {
        [
            "transaction": transactionPayload,
            "ekyc_image_ref": artifacts.ekycImageRef,
            "ekyc_document_ref": artifacts.ekycDocumentRef,
            "stt_audio_ref": artifacts.sttAudioRef,
            "challenge_video_ref": artifacts.challengeVideoRef as Any,
            "challenge_frame_refs": artifacts.challengeFrameRefs,
            "client_session": clientSession,
        ]
    }

    public static func buildLiveCheckMultipart(input: LiveCheckUploadInput) -> [MultipartPart] {
        var parts = [
            MultipartPart(
                fieldName: "challenge_video",
                filename: input.challengeVideoFilename,
                contentType: input.challengeVideoContentType,
                data: input.challengeVideo
            ),
            MultipartPart(
                fieldName: "document",
                filename: input.documentFilename,
                contentType: input.documentContentType,
                data: input.document
            ),
        ]
        if let audio = input.challengeAudio, let audioName = input.challengeAudioFilename {
            parts.append(
                MultipartPart(
                    fieldName: "challenge_audio",
                    filename: audioName,
                    contentType: input.challengeAudioContentType,
                    data: audio
                )
            )
        }
        for frame in input.frames.sorted(by: { $0.index < $1.index }) {
            parts.append(
                MultipartPart(
                    fieldName: "frame_\(frame.index)",
                    filename: frame.filename,
                    contentType: "image/jpeg",
                    data: frame.jpegData
                )
            )
        }
        return parts
    }
}

public enum ShieldJSON {
    public static func parseAnalyzeResponse(_ data: Data) throws -> ShieldAnalyzeResponse {
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        let explanations = (json["explanations"] as? [[String: Any]] ?? []).map { item in
            ShieldExplanation(
                label: item["label"] as? String ?? "",
                detail: item["detail"] as? String ?? "",
                weight: item["weight"] as? Int ?? 0
            )
        }
        return ShieldAnalyzeResponse(
            riskScore: json["risk_score"] as? Int ?? 0,
            riskLevel: json["risk_level"] as? String ?? "unknown",
            action: json["action"] as? String ?? "unknown",
            circuitBreakerStage: json["circuit_breaker_stage"] as? String ?? "outer_context",
            circuitBreakerTriggered: json["circuit_breaker_triggered"] as? Bool ?? false,
            invasiveCheckRequired: json["invasive_check_required"] as? Bool ?? false,
            stageOneScore: json["stage_one_score"] as? Int ?? 0,
            stageTwoScore: json["stage_two_score"] as? Int,
            interventionMessage: json["intervention_message"] as? String ?? "",
            scamType: json["scam_type"] as? String,
            challengeProfile: json["challenge_profile"] as? String,
            explanations: explanations
        )
    }

    public static func parseLiveCheckUploadResponse(_ data: Data) throws -> LiveCheckUploadResponse {
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return LiveCheckUploadResponse(
            ekycImageRef: json["ekyc_image_ref"] as? String ?? "",
            ekycDocumentRef: json["ekyc_document_ref"] as? String ?? "",
            sttAudioRef: json["stt_audio_ref"] as? String ?? "",
            challengeVideoRef: json["challenge_video_ref"] as? String ?? "",
            challengeFrameRefs: json["challenge_frame_refs"] as? [String] ?? [],
            frameCount: json["frame_count"] as? Int ?? 0
        )
    }

    public static func toChallengeArtifacts(_ upload: LiveCheckUploadResponse) -> ShieldChallengeArtifacts {
        ShieldChallengeArtifacts(
            ekycImageRef: upload.ekycImageRef,
            ekycDocumentRef: upload.ekycDocumentRef,
            sttAudioRef: upload.sttAudioRef,
            challengeVideoRef: upload.challengeVideoRef,
            challengeFrameRefs: upload.challengeFrameRefs
        )
    }
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
        ShieldPayloadBuilder.buildAnalyzePayload(
            transaction: transaction,
            config: config,
            consent: consent,
            telemetry: telemetryProvider.snapshot(consent: consent),
            overrides: overrides
        )
    }

    public func buildShieldPayloadWithCall(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        callStateMonitor: CallStateMonitor,
        overrides: [String: Any] = [:]
    ) -> [String: Any] {
        buildShieldPayload(
            transaction: transaction.withCallContext(callStateMonitor.snapshot()),
            consent: consent,
            overrides: overrides
        )
    }

    public func analyzeShieldWithCall(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        callStateMonitor: CallStateMonitor,
        overrides: [String: Any] = [:],
        completion: @escaping (Result<ShieldAnalyzeResponse, Error>) -> Void
    ) {
        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/shield/analyze",
            body: buildShieldPayloadWithCall(
                transaction: transaction,
                consent: consent,
                callStateMonitor: callStateMonitor,
                overrides: overrides
            )
        ) { result in
            completion(result.flatMap { data in
                Result { try ShieldJSON.parseAnalyzeResponse(data) }
            })
        }
    }

    public func analyzeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: [String: Any] = [:],
        completion: @escaping (Result<ShieldAnalyzeResponse, Error>) -> Void
    ) {
        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/shield/analyze",
            body: buildShieldPayload(transaction: transaction, consent: consent, overrides: overrides)
        ) { result in
            completion(result.flatMap { data in
                Result { try ShieldJSON.parseAnalyzeResponse(data) }
            })
        }
    }

    public func uploadLiveCheck(
        input: LiveCheckUploadInput,
        completion: @escaping (Result<LiveCheckUploadResponse, Error>) -> Void
    ) {
        transport.postMultipart(
            baseUrl: config.baseUrl,
            path: "/api/shield/challenge/upload-live-check",
            parts: ShieldPayloadBuilder.buildLiveCheckMultipart(input: input)
        ) { result in
            completion(result.flatMap { data in
                Result { try ShieldJSON.parseLiveCheckUploadResponse(data) }
            })
        }
    }

    public func challengeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        artifacts: ShieldChallengeArtifacts,
        overrides: [String: Any] = [:],
        clientSession: String = "fides-mobile-session",
        completion: @escaping (Result<ShieldAnalyzeResponse, Error>) -> Void
    ) {
        guard !artifacts.ekycDocumentRef.isEmpty else {
            completion(.failure(NSError(domain: "FidesMobileSDK", code: 422, userInfo: [
                NSLocalizedDescriptionKey: "ekyc_document_ref is required.",
            ])))
            return
        }

        transport.postJSON(
            baseUrl: config.baseUrl,
            path: "/api/shield/challenge",
            body: ShieldPayloadBuilder.buildChallengePayload(
                transactionPayload: buildShieldPayload(transaction: transaction, consent: consent, overrides: overrides),
                artifacts: artifacts,
                clientSession: clientSession
            ),
            completion: { result in
                completion(result.flatMap { data in
                    Result { try ShieldJSON.parseAnalyzeResponse(data) }
                })
            }
        )
    }

    public func runIdentityCheck(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        liveCheckInput: LiveCheckUploadInput,
        overrides: [String: Any] = [:],
        clientSession: String = "fides-mobile-session",
        completion: @escaping (Result<ShieldAnalyzeResponse, Error>) -> Void
    ) {
        uploadLiveCheck(input: liveCheckInput) { uploadResult in
            switch uploadResult {
            case .failure(let error):
                completion(.failure(error))
            case .success(let upload):
                self.challengeShield(
                    transaction: transaction,
                    consent: consent,
                    artifacts: ShieldJSON.toChallengeArtifacts(upload),
                    overrides: overrides,
                    clientSession: clientSession,
                    completion: completion
                )
            }
        }
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
