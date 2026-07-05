package ai.fides.sdk

data class FidesConfig(
    val baseUrl: String,
    val sdkSource: String = "fides_mobile_sdk",
    val shieldPath: String = "transfer_monitoring",
)

data class FidesConsent(
    val telemetry: Boolean = false,
    val audio: Boolean = false,
    val partnerDataSharing: Boolean = false,
)

data class ShieldTransaction(
    val amount: Long,
    val recipientName: String,
    val recipientAccount: String,
    val activeCall: Boolean = false,
    val callerType: String = "unknown",
    val callerNumber: String = "",
    val recipientKnown: Boolean = false,
    val recipientPhone: String = "",
    val transcript: String = "",
)

data class FidesTelemetrySnapshot(
    val nativeTelemetryAvailable: Boolean = false,
    val nativeTelemetrySource: String = "fides_mobile_sdk",
    val installedRemoteAccessAppDetected: Boolean = false,
    val accessibilityServiceRisk: Boolean = false,
    val screenSharingDetected: Boolean = false,
    val remoteControlDetected: Boolean = false,
    val smartuxBehaviorAnomalyScore: Double? = null,
    val smartuxRemoteControlScore: Double? = null,
    val smartuxSignals: List<String> = emptyList(),
    val sdkSessionId: String? = null,
) {
    fun toShieldFields(): Map<String, Any?> = mapOf(
        "native_telemetry_available" to nativeTelemetryAvailable,
        "native_telemetry_source" to nativeTelemetrySource,
        "installed_remote_access_app_detected" to installedRemoteAccessAppDetected,
        "accessibility_service_risk" to accessibilityServiceRisk,
        "screen_sharing_detected" to screenSharingDetected,
        "remote_control_detected" to remoteControlDetected,
        "smartux_behavior_anomaly_score" to smartuxBehaviorAnomalyScore,
        "smartux_remote_control_score" to smartuxRemoteControlScore,
        "smartux_signals" to smartuxSignals,
    )
}

data class MultipartPart(
    val fieldName: String,
    val filename: String,
    val contentType: String,
    val bytes: ByteArray,
)

data class LiveCheckFramePart(
    val index: Int,
    val jpegBytes: ByteArray,
    val filename: String = "frame-$index.jpg",
)

data class LiveCheckUploadInput(
    val challengeVideo: ByteArray,
    val challengeVideoFilename: String,
    val challengeVideoContentType: String = "video/webm",
    val document: ByteArray,
    val documentFilename: String,
    val documentContentType: String = "image/jpeg",
    val challengeAudio: ByteArray? = null,
    val challengeAudioFilename: String? = null,
    val challengeAudioContentType: String = "audio/webm",
    val frames: List<LiveCheckFramePart> = emptyList(),
)

data class LiveCheckUploadResponse(
    val ekycImageRef: String,
    val ekycDocumentRef: String,
    val sttAudioRef: String,
    val challengeVideoRef: String,
    val challengeFrameRefs: List<String>,
    val frameCount: Int,
)

data class ShieldChallengeArtifacts(
    val ekycImageRef: String,
    val ekycDocumentRef: String,
    val sttAudioRef: String,
    val challengeVideoRef: String? = null,
    val challengeFrameRefs: List<String> = emptyList(),
)

data class ShieldExplanation(
    val label: String,
    val detail: String,
    val weight: Int,
)

data class ShieldAnalyzeResponse(
    val riskScore: Int,
    val riskLevel: String,
    val action: String,
    val circuitBreakerStage: String,
    val circuitBreakerTriggered: Boolean,
    val invasiveCheckRequired: Boolean,
    val stageOneScore: Int,
    val stageTwoScore: Int?,
    val interventionMessage: String,
    val scamType: String?,
    val challengeProfile: String?,
    val explanations: List<ShieldExplanation>,
) {
    val requiresIdentityCheck: Boolean
        get() = invasiveCheckRequired || action == "require_camera_voice_check"
}

sealed class FidesSdkResult<out T> {
    data class Success<T>(val value: T) : FidesSdkResult<T>()
    data class Failure(val message: String, val cause: Throwable? = null) : FidesSdkResult<Nothing>()
}

interface FidesTelemetryProvider {
    fun snapshot(consent: FidesConsent): FidesTelemetrySnapshot
}

interface FidesHttpTransport {
    fun postJson(
        baseUrl: String,
        path: String,
        body: Map<String, Any?>,
        completion: (FidesSdkResult<String>) -> Unit,
    )

    fun postMultipart(
        baseUrl: String,
        path: String,
        parts: List<MultipartPart>,
        completion: (FidesSdkResult<String>) -> Unit,
    )
}

class DefaultFidesTelemetryProvider(
    private val sdkSource: String = "fides_mobile_sdk",
    private val sessionId: String = "fides-android-${System.currentTimeMillis()}",
) : FidesTelemetryProvider {
    override fun snapshot(consent: FidesConsent): FidesTelemetrySnapshot {
        if (!consent.telemetry) {
            return FidesTelemetrySnapshot(
                nativeTelemetryAvailable = false,
                nativeTelemetrySource = sdkSource,
                sdkSessionId = sessionId,
            )
        }
        return FidesTelemetrySnapshot(
            nativeTelemetryAvailable = true,
            nativeTelemetrySource = sdkSource,
            smartuxBehaviorAnomalyScore = 0.22,
            smartuxRemoteControlScore = 0.08,
            sdkSessionId = sessionId,
        )
    }
}
