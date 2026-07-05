package ai.fides.sdk

import org.json.JSONArray
import org.json.JSONObject

object GrowJson {
    fun parseUploadResponse(rawJson: String): GrowUploadResponse {
        val json = JSONObject(rawJson)
        return GrowUploadResponse(
            inputSource = json.getString("input_source"),
            filename = json.getString("filename"),
            sizeBytes = json.getInt("size_bytes"),
        )
    }

    fun parseProcessResponse(rawJson: String): GrowProcessResponse {
        val json = JSONObject(rawJson)
        val request = json.getJSONObject("request")
        val analysis = json.getJSONObject("analysis")
        val ocr = request.optJSONObject("ocr")
        val extracted = ocr?.optJSONObject("extracted_fields")

        return GrowProcessResponse(
            inputSource = request.optString("input_source").takeIf { it.isNotBlank() }.orEmpty(),
            businessName = request.optString("business_name", ""),
            customerName = request.optString("customer_name", ""),
            invoiceId = request.optString("invoice_id", ""),
            invoiceTotal = request.optLong("invoice_total", 0),
            ocrProvider = ocr?.optString("provider")?.takeIf { it.isNotBlank() },
            ocrConfidence = ocr?.optDouble("confidence")?.takeIf { ocr.has("confidence") && !ocr.isNull("confidence") },
            extractedFields = extracted?.let { fields ->
                GrowOcrExtractedFields(
                    sellerName = fields.optString("seller_name").takeIf { it.isNotBlank() },
                    buyerName = fields.optString("buyer_name").takeIf { it.isNotBlank() },
                    invoiceId = fields.optString("invoice_id").takeIf { it.isNotBlank() },
                    totalAmount = fields.optLong("total_amount").takeIf { fields.has("total_amount") && !fields.isNull("total_amount") },
                )
            },
            analysis = parseAnalyzeResponse(analysis),
        )
    }

    fun buildProcessInvoicePayload(
        inputSource: String,
        businessId: String = "biz_demo",
        businessName: String = "",
        customerName: String = "",
        invoiceId: String = "",
        invoiceTotal: Long = 0,
    ): Map<String, Any?> = mapOf(
        "business_id" to businessId,
        "business_name" to businessName,
        "input_mode" to "invoice_photo",
        "input_source" to inputSource,
        "invoice_id" to invoiceId,
        "customer_name" to customerName,
        "invoice_total" to invoiceTotal,
        "paid_on_time" to true,
        "items" to emptyList<Any>(),
    )

    private fun parseAnalyzeResponse(json: JSONObject): GrowAnalyzeResponse =
        GrowAnalyzeResponse(
            trustScore = json.getInt("trust_score"),
            creditBand = json.getString("credit_band"),
            monthlyRevenueEstimate = json.getLong("monthly_revenue_estimate"),
            loanReadiness = json.getString("loan_readiness"),
            recommendedAction = json.getString("recommended_action"),
            explanations = parseExplanations(json.optJSONArray("explanations")),
        )

    private fun parseExplanations(array: JSONArray?): List<GrowExplanation> {
        if (array == null) {
            return emptyList()
        }
        return buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    GrowExplanation(
                        label = item.getString("label"),
                        detail = item.getString("detail"),
                    ),
                )
            }
        }
    }
}
