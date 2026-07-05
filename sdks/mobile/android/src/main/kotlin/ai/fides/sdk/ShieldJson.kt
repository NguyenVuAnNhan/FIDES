package ai.fides.sdk

import org.json.JSONArray
import org.json.JSONObject

object ShieldJson {
    fun parseAnalyzeResponse(rawJson: String): ShieldAnalyzeResponse {
        val json = JSONObject(rawJson)
        return ShieldAnalyzeResponse(
            riskScore = json.getInt("risk_score"),
            riskLevel = json.getString("risk_level"),
            action = json.getString("action"),
            circuitBreakerStage = json.optString("circuit_breaker_stage", "outer_context"),
            circuitBreakerTriggered = json.optBoolean("circuit_breaker_triggered", false),
            invasiveCheckRequired = json.optBoolean("invasive_check_required", false),
            stageOneScore = json.optInt("stage_one_score", 0),
            stageTwoScore = json.optInt("stage_two_score").takeIf { json.has("stage_two_score") && !json.isNull("stage_two_score") },
            interventionMessage = json.optString("intervention_message", ""),
            scamType = json.optString("scam_type").takeIf { json.has("scam_type") && !json.isNull("scam_type") },
            challengeProfile = json.optString("challenge_profile").takeIf { json.has("challenge_profile") && !json.isNull("challenge_profile") },
            explanations = parseExplanations(json.optJSONArray("explanations")),
        )
    }

    fun parseLiveCheckUploadResponse(rawJson: String): LiveCheckUploadResponse {
        val json = JSONObject(rawJson)
        val frameRefs = json.optJSONArray("challenge_frame_refs")?.let { array ->
            buildList {
                for (index in 0 until array.length()) {
                    add(array.getString(index))
                }
            }
        } ?: emptyList()

        return LiveCheckUploadResponse(
            ekycImageRef = json.getString("ekyc_image_ref"),
            ekycDocumentRef = json.getString("ekyc_document_ref"),
            sttAudioRef = json.getString("stt_audio_ref"),
            challengeVideoRef = json.getString("challenge_video_ref"),
            challengeFrameRefs = frameRefs,
            frameCount = json.optInt("frame_count", frameRefs.size),
        )
    }

    fun toChallengeArtifacts(upload: LiveCheckUploadResponse): ShieldChallengeArtifacts =
        ShieldChallengeArtifacts(
            ekycImageRef = upload.ekycImageRef,
            ekycDocumentRef = upload.ekycDocumentRef,
            sttAudioRef = upload.sttAudioRef,
            challengeVideoRef = upload.challengeVideoRef,
            challengeFrameRefs = upload.challengeFrameRefs,
        )

    private fun parseExplanations(array: JSONArray?): List<ShieldExplanation> {
        if (array == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    ShieldExplanation(
                        label = item.getString("label"),
                        detail = item.getString("detail"),
                        weight = item.optInt("weight", 0),
                    ),
                )
            }
        }
    }
}
