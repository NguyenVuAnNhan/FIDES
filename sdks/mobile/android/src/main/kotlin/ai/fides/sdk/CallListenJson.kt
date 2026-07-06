package ai.fides.sdk

import org.json.JSONArray
import org.json.JSONObject

object CallListenJson {
    fun parseResult(rawJson: String): CallListenResult {
        val json = JSONObject(rawJson)
        return CallListenResult(
            sttTranscript = json.optString("stt_transcript", ""),
            sttConfidence = json.optDoubleOrNull("stt_confidence"),
            isScam = json.optBoolean("is_scam", false),
            scamType = json.optString("scam_type").takeIf { it.isNotBlank() && !json.isNull("scam_type") },
            scamTypeLabel = json.optString("scam_type_label", ""),
            confidence = json.optDoubleOrNull("confidence"),
            detectedPatterns = parseStringList(json.optJSONArray("detected_patterns")),
            riskLevel = json.optString("risk_level", "low"),
            recommendedAction = json.optString("recommended_action", "no_action"),
            interventionMessage = json.optString("intervention_message", ""),
            guardianAlert = json.optBoolean("guardian_alert", false),
            guardianMessage = json.optString("guardian_message", ""),
            providerMode = json.optString("provider_mode", ""),
            explanations = parseExplanations(json.optJSONArray("explanations")),
        )
    }

    private fun JSONObject.optDoubleOrNull(key: String): Double? =
        if (has(key) && !isNull(key)) optDouble(key) else null

    private fun parseStringList(array: JSONArray?): List<String> {
        if (array == null) return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                add(array.getString(index))
            }
        }
    }

    private fun parseExplanations(array: JSONArray?): List<CallListenExplanation> {
        if (array == null) return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    CallListenExplanation(
                        label = item.optString("label", ""),
                        detail = item.optString("detail", ""),
                    ),
                )
            }
        }
    }
}
