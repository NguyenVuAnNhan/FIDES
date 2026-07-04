package ai.fides.sdk

data class FidesConfig(
    val baseUrl: String,
    val sdkSource: String = "fides_mobile_sdk"
)

data class FidesConsent(
    val telemetry: Boolean = false,
    val audio: Boolean = false,
    val partnerDataSharing: Boolean = false
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
    val transcript: String = ""
)

data class FidesTelemetrySnapshot(
    val nativeTelemetryAvailable: Boolean = false,
    val nativeTelemetrySource: String = "fides_mobile_sdk",
    val installedRemoteAccessAppDetected: Boolean = false,
    val accessibilityServiceRisk: Boolean = false,
    val screenSharingDetected: Boolean = false,
    val smartuxBehaviorAnomalyScore: Double? = null,
    val smartuxRemoteControlScore: Double? = null,
    val smartuxSignals: List<String> = emptyList(),
    val sdkSessionId: String? = null
) {
    fun toShieldFields(): Map<String, Any?> = mapOf(
        "native_telemetry_available" to nativeTelemetryAvailable,
        "native_telemetry_source" to nativeTelemetrySource,
        "installed_remote_access_app_detected" to installedRemoteAccessAppDetected,
        "accessibility_service_risk" to accessibilityServiceRisk,
        "screen_sharing_detected" to screenSharingDetected,
        "smartux_behavior_anomaly_score" to smartuxBehaviorAnomalyScore,
        "smartux_remote_control_score" to smartuxRemoteControlScore,
        "smartux_signals" to smartuxSignals,
        "smartux_session" to mapOf(
            "provider" to "FIDES Mobile SDK",
            "sdk_session_id" to sdkSessionId,
            "sdk_methods" to listOf("snapshot", "buildShieldPayload", "analyzeShield", "challengeShield")
        )
    )
}

interface FidesTelemetryProvider {
    fun snapshot(consent: FidesConsent): FidesTelemetrySnapshot
}

interface FidesHttpTransport {
    fun postJson(
        baseUrl: String,
        path: String,
        body: Map<String, Any?>,
        completion: (FidesSdkResult<String>) -> Unit
    )
}

sealed class FidesSdkResult<out T> {
    data class Success<T>(val value: T) : FidesSdkResult<T>()
    data class Failure(val message: String, val cause: Throwable? = null) : FidesSdkResult<Nothing>()
}

class FidesMobileSdk(
    private val config: FidesConfig,
    private val telemetryProvider: FidesTelemetryProvider,
    private val transport: FidesHttpTransport
) {
    fun buildShieldPayload(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: Map<String, Any?> = emptyMap()
    ): Map<String, Any?> {
        val telemetry = telemetryProvider.snapshot(consent).toShieldFields()
        return mapOf(
            "transaction_amount" to transaction.amount,
            "recipient_name" to transaction.recipientName,
            "recipient_account" to transaction.recipientAccount,
            "active_call" to transaction.activeCall,
            "caller_type" to transaction.callerType,
            "caller_number" to transaction.callerNumber,
            "recipient_known" to transaction.recipientKnown,
            "recipient_phone" to transaction.recipientPhone,
            "transcript" to transaction.transcript,
            "consent_granted" to consent.audio
        ) + telemetry + overrides
    }

    fun analyzeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: Map<String, Any?> = emptyMap(),
        completion: (FidesSdkResult<String>) -> Unit
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/shield/analyze",
            body = buildShieldPayload(transaction, consent, overrides),
            completion = completion
        )
    }

    fun challengeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: Map<String, Any?> = emptyMap(),
        challengeProfile: String = "clear_user",
        spokenResponse: String = "",
        completion: (FidesSdkResult<String>) -> Unit
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/shield/challenge",
            body = mapOf(
                "transaction" to buildShieldPayload(transaction, consent, overrides),
                "challenge_profile" to challengeProfile,
                "spoken_response" to spokenResponse
            ),
            completion = completion
        )
    }

    fun analyzeGrow(
        payload: Map<String, Any?>,
        completion: (FidesSdkResult<String>) -> Unit
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/grow/analyze-invoice",
            body = payload,
            completion = completion
        )
    }
}
