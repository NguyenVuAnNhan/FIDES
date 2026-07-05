package ai.fides.sdk

data class GrowUploadResponse(
    val inputSource: String,
    val filename: String,
    val sizeBytes: Int,
)

data class GrowExplanation(
    val label: String,
    val detail: String,
)

data class GrowAnalyzeResponse(
    val trustScore: Int,
    val creditBand: String,
    val monthlyRevenueEstimate: Long,
    val loanReadiness: String,
    val recommendedAction: String,
    val explanations: List<GrowExplanation>,
)

data class GrowOcrExtractedFields(
    val sellerName: String?,
    val buyerName: String?,
    val invoiceId: String?,
    val totalAmount: Long?,
)

data class GrowProcessResponse(
    val inputSource: String,
    val businessName: String,
    val customerName: String,
    val invoiceId: String,
    val invoiceTotal: Long,
    val ocrProvider: String?,
    val ocrConfidence: Double?,
    val extractedFields: GrowOcrExtractedFields?,
    val analysis: GrowAnalyzeResponse,
)
