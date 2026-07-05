package ai.fides.sdk

import ai.fides.sdk.call.CallStateMonitor
import ai.fides.sdk.call.withCallContext

class FidesMobileSdk(
    private val config: FidesConfig,
    private val telemetryProvider: FidesTelemetryProvider,
    private val transport: FidesHttpTransport,
) {
    fun buildShieldPayload(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: Map<String, Any?> = emptyMap(),
    ): Map<String, Any?> {
        val telemetry = telemetryProvider.snapshot(consent)
        return ShieldPayloadBuilder.buildAnalyzePayload(
            transaction = transaction,
            config = config,
            consent = consent,
            telemetry = telemetry,
            overrides = overrides,
        )
    }

    fun buildShieldPayloadWithCall(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        callStateMonitor: CallStateMonitor,
        overrides: Map<String, Any?> = emptyMap(),
    ): Map<String, Any?> =
        buildShieldPayload(
            transaction = transaction.withCallContext(callStateMonitor.snapshot()),
            consent = consent,
            overrides = overrides,
        )

    fun analyzeShieldWithCall(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        callStateMonitor: CallStateMonitor,
        overrides: Map<String, Any?> = emptyMap(),
        completion: (FidesSdkResult<ShieldAnalyzeResponse>) -> Unit,
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/shield/analyze",
            body = buildShieldPayloadWithCall(transaction, consent, callStateMonitor, overrides),
        ) { result ->
            completion(result.mapJson(ShieldJson::parseAnalyzeResponse))
        }
    }

    fun analyzeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        overrides: Map<String, Any?> = emptyMap(),
        completion: (FidesSdkResult<ShieldAnalyzeResponse>) -> Unit,
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/shield/analyze",
            body = buildShieldPayload(transaction, consent, overrides),
        ) { result ->
            completion(result.mapJson(ShieldJson::parseAnalyzeResponse))
        }
    }

    fun uploadLiveCheck(
        input: LiveCheckUploadInput,
        completion: (FidesSdkResult<LiveCheckUploadResponse>) -> Unit,
    ) {
        transport.postMultipart(
            baseUrl = config.baseUrl,
            path = "/api/shield/challenge/upload-live-check",
            parts = ShieldPayloadBuilder.buildLiveCheckMultipart(input),
        ) { result ->
            completion(result.mapJson(ShieldJson::parseLiveCheckUploadResponse))
        }
    }

    fun challengeShield(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        artifacts: ShieldChallengeArtifacts,
        overrides: Map<String, Any?> = emptyMap(),
        clientSession: String = "fides-mobile-session",
        completion: (FidesSdkResult<ShieldAnalyzeResponse>) -> Unit,
    ) {
        require(artifacts.ekycDocumentRef.isNotBlank()) {
            "ekyc_document_ref is required. Upload CCCD via uploadLiveCheck first."
        }

        val transactionPayload = buildShieldPayload(transaction, consent, overrides)
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/shield/challenge",
            body = ShieldPayloadBuilder.buildChallengePayload(
                transactionPayload = transactionPayload,
                artifacts = artifacts,
                clientSession = clientSession,
            ),
        ) { result ->
            completion(result.mapJson(ShieldJson::parseAnalyzeResponse))
        }
    }

    /**
     * Path B step 2: upload live-check media, then run /api/shield/challenge.
     */
    fun runIdentityCheck(
        transaction: ShieldTransaction,
        consent: FidesConsent,
        liveCheckInput: LiveCheckUploadInput,
        overrides: Map<String, Any?> = emptyMap(),
        clientSession: String = "fides-mobile-session",
        completion: (FidesSdkResult<ShieldAnalyzeResponse>) -> Unit,
    ) {
        uploadLiveCheck(liveCheckInput) { uploadResult ->
            when (uploadResult) {
                is FidesSdkResult.Failure -> completion(uploadResult)
                is FidesSdkResult.Success -> {
                    challengeShield(
                        transaction = transaction,
                        consent = consent,
                        artifacts = ShieldJson.toChallengeArtifacts(uploadResult.value),
                        overrides = overrides,
                        clientSession = clientSession,
                        completion = completion,
                    )
                }
            }
        }
    }

    fun analyzeGrow(
        payload: Map<String, Any?>,
        completion: (FidesSdkResult<String>) -> Unit,
    ) {
        transport.postJson(
            baseUrl = config.baseUrl,
            path = "/api/grow/analyze-invoice",
            body = payload,
            completion = completion,
        )
    }

    private inline fun <T> FidesSdkResult<String>.mapJson(parser: (String) -> T): FidesSdkResult<T> =
        when (this) {
            is FidesSdkResult.Failure -> this
            is FidesSdkResult.Success -> {
                try {
                    FidesSdkResult.Success(parser(value))
                } catch (error: Throwable) {
                    FidesSdkResult.Failure("Failed to parse Shield response.", error)
                }
            }
        }
}
