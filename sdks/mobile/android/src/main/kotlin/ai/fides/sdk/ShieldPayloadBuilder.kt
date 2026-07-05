package ai.fides.sdk

/**
 * Builds normalized ShieldAnalyzeRequest payloads for Path B transfer monitoring.
 * Matches the web demo defaults in frontend/static/shield.js (APP_SDK_CONTEXT + stage-2 cleared).
 */
object ShieldPayloadBuilder {
    fun buildPathBDefaults(
        config: FidesConfig,
        consent: FidesConsent,
    ): Map<String, Any?> = mapOf(
        "shield_path" to config.shieldPath,
        "consent_call_monitoring" to false,
        "consent_transfer_check" to false,
        "consent_granted" to consent.audio,
        "vn_social_report_count" to 0,
        "vn_social_recent_keywords" to emptyList<String>(),
        "simo_status" to "not_checked",
        "simo_last_checked_at" to null,
        "graph_risk_score" to null,
        "graph_pattern" to null,
        "inbound_sender_count_10m" to 0,
        "outbound_account_count_10m" to 0,
        "median_pass_through_minutes" to null,
        "account_age_days" to null,
        "shared_device_cluster_size" to 0,
        "funds_moved_within_minutes" to false,
        "recipient_risk_level" to "unknown",
        "ekyc_verification_status" to "not_checked",
        "ekyc_liveness_passed" to null,
        "ekyc_liveness_score" to null,
        "ekyc_mask_detected" to false,
        "ekyc_face_match_score" to null,
        "ekyc_injection_risk_score" to null,
        "audio_source" to null,
        "stt_transcript" to "",
        "stt_confidence" to null,
        "voice_reference_source" to null,
        "voice_verification_status" to "not_checked",
        "voice_match_score" to null,
        "voice_match_threshold" to null,
        "detected_patterns" to emptyList<String>(),
        "llm_scam_type" to null,
        "llm_confidence" to null,
        "voice_stress_score" to null,
        "voice_stress_labels" to emptyList<String>(),
        "face_emotion_score" to null,
        "face_emotion_labels" to emptyList<String>(),
        "scripted_behavior_score" to null,
        "scripted_behavior_labels" to emptyList<String>(),
        "coercion_score" to null,
        "coercion_confidence" to null,
        "smartbot_intervention_message" to null,
        "smartbot_recommended_action" to null,
        "smartbot_risk_level" to null,
    )

    fun buildAnalyzePayload(
        transaction: ShieldTransaction,
        config: FidesConfig,
        consent: FidesConsent,
        telemetry: FidesTelemetrySnapshot,
        overrides: Map<String, Any?> = emptyMap(),
    ): Map<String, Any?> {
        val payload = linkedMapOf<String, Any?>(
            "transaction_amount" to transaction.amount,
            "recipient_name" to transaction.recipientName,
            "recipient_account" to transaction.recipientAccount,
            "active_call" to transaction.activeCall,
            "caller_type" to transaction.callerType,
            "caller_number" to transaction.callerNumber,
            "recipient_known" to transaction.recipientKnown,
            "recipient_phone" to transaction.recipientPhone,
            "transcript" to transaction.transcript,
        )
        payload.putAll(buildPathBDefaults(config, consent))
        payload.putAll(telemetry.toShieldFields())
        payload.putAll(overrides)
        return payload
    }

    fun buildChallengePayload(
        transactionPayload: Map<String, Any?>,
        artifacts: ShieldChallengeArtifacts,
        clientSession: String,
    ): Map<String, Any?> = mapOf(
        "transaction" to transactionPayload,
        "ekyc_image_ref" to artifacts.ekycImageRef,
        "ekyc_document_ref" to artifacts.ekycDocumentRef,
        "stt_audio_ref" to artifacts.sttAudioRef,
        "challenge_video_ref" to artifacts.challengeVideoRef,
        "challenge_frame_refs" to artifacts.challengeFrameRefs,
        "client_session" to clientSession,
    )

    fun buildLiveCheckMultipart(input: LiveCheckUploadInput): List<MultipartPart> {
        val parts = mutableListOf(
            MultipartPart(
                fieldName = "challenge_video",
                filename = input.challengeVideoFilename,
                contentType = input.challengeVideoContentType,
                bytes = input.challengeVideo,
            ),
            MultipartPart(
                fieldName = "document",
                filename = input.documentFilename,
                contentType = input.documentContentType,
                bytes = input.document,
            ),
        )

        val audio = input.challengeAudio
        val audioName = input.challengeAudioFilename
        if (audio != null && audioName != null) {
            parts.add(
                MultipartPart(
                    fieldName = "challenge_audio",
                    filename = audioName,
                    contentType = input.challengeAudioContentType,
                    bytes = audio,
                ),
            )
        }

        input.frames
            .sortedBy { it.index }
            .forEach { frame ->
                parts.add(
                    MultipartPart(
                        fieldName = "frame_${frame.index}",
                        filename = frame.filename,
                        contentType = "image/jpeg",
                        bytes = frame.jpegBytes,
                    ),
                )
            }

        return parts
    }
}
