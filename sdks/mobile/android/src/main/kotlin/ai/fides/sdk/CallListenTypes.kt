package ai.fides.sdk

data class CallListenExplanation(
    val label: String,
    val detail: String,
)

data class CallListenResult(
    val sttTranscript: String,
    val sttConfidence: Double?,
    val isScam: Boolean,
    val scamType: String?,
    val scamTypeLabel: String,
    val confidence: Double?,
    val detectedPatterns: List<String>,
    val riskLevel: String,
    val recommendedAction: String,
    val interventionMessage: String,
    val guardianAlert: Boolean,
    val guardianMessage: String,
    val providerMode: String,
    val explanations: List<CallListenExplanation>,
)
