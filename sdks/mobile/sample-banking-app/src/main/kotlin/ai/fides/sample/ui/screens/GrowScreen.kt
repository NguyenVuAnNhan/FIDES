package ai.fides.sample.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ai.fides.sdk.GrowProcessResponse
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.theme.FidesTeal
import java.text.NumberFormat
import java.util.Locale

@Composable
fun GrowScreen(
    loanAmount: Long,
    loanTermMonths: Int,
    loading: Boolean,
    statusMessage: String,
    errorMessage: String?,
    receiptFilename: String?,
    growResponse: GrowProcessResponse?,
    onClose: () -> Unit,
    onPickReceipt: () -> Unit,
    onAnalyze: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .statusBarsPadding(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "Phân tích Grow",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(start = 8.dp),
            )
            IconButton(onClick = onClose) {
                Icon(Icons.Default.Close, contentDescription = "Đóng", tint = Color.Gray)
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
        ) {
        Spacer(modifier = Modifier.height(4.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFE8F5F4))
                .padding(16.dp),
        ) {
            Text("Khoản vay quan tâm", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
            Text(
                "${formatVnd(loanAmount)} · $loanTermMonths tháng",
                color = FidesTeal,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleLarge,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "Một hóa đơn chỉ là phân tích sơ bộ — chưa phải hồ sơ vay đầy đủ. Upload biên lai để Grow chạy SmartReader OCR + LightGBM.",
                color = Color.DarkGray,
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "Cần thêm 2–3 hóa đơn (cùng doanh nghiệp) trước khi đề xuất hạn mức vay.",
                color = FidesTeal,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Medium,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFF8FAFC))
                .padding(16.dp),
        ) {
            Text("Hóa đơn / biên lai", fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                receiptFilename ?: "Chưa chọn ảnh hóa đơn",
                color = if (receiptFilename != null) Color.DarkGray else Color.Gray,
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(modifier = Modifier.height(12.dp))
            FidesPrimaryButton(
                text = if (receiptFilename == null) "Chọn ảnh hóa đơn" else "Chọn ảnh khác",
                enabled = !loading,
                onClick = onPickReceipt,
            )
        }

        if (statusMessage.isNotBlank()) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(statusMessage, color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
        }

        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(errorMessage, color = Color(0xFFC62828), style = MaterialTheme.typography.bodySmall)
        }

        if (loading) {
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CircularProgressIndicator(color = FidesTeal, modifier = Modifier.padding(end = 12.dp))
                Text("Đang phân tích...", color = Color.Gray)
            }
        }

        if (receiptFilename != null && growResponse == null && !loading) {
            Spacer(modifier = Modifier.height(16.dp))
            FidesPrimaryButton(text = "Phân tích tín dụng sơ bộ", onClick = onAnalyze)
        }

        growResponse?.let { response ->
            Spacer(modifier = Modifier.height(20.dp))
            GrowResultPanel(response)
        }

        Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun GrowResultPanel(response: GrowProcessResponse) {
    val analysis = response.analysis
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(
                Brush.linearGradient(listOf(Color(0xFFE0F7FA), Color(0xFFB2EBF2))),
            )
            .padding(16.dp),
    ) {
        Text("Kết quả phân tích sơ bộ", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Một hóa đơn không mô tả toàn bộ doanh nghiệp. Trust score bên dưới chỉ là tín hiệu ban đầu.",
            color = Color.DarkGray,
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            GrowPill("Trust ${analysis.trustScore}/100")
            GrowPill(formatLoanReadiness(analysis.loanReadiness))
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            "Doanh thu ước tính (thô): ${formatVnd(analysis.monthlyRevenueEstimate)}/tháng",
            fontWeight = FontWeight.SemiBold,
            color = Color.Gray,
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            formatRecommendedAction(analysis),
            color = Color.DarkGray,
            style = MaterialTheme.typography.bodyMedium,
        )
    }

    Spacer(modifier = Modifier.height(12.dp))
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFFF8FAFC))
            .padding(16.dp),
    ) {
        Text("OCR hóa đơn", fontWeight = FontWeight.SemiBold)
        response.ocrProvider?.let {
            Text("Provider: $it", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        }
        response.ocrConfidence?.let {
            Text("Confidence: ${(it * 100).toInt()}%", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        }
        Spacer(modifier = Modifier.height(8.dp))
        GrowFactRow("Người bán", response.businessName.ifBlank { response.extractedFields?.sellerName })
        GrowFactRow("Khách hàng", response.customerName.ifBlank { response.extractedFields?.buyerName })
        GrowFactRow("Mã HĐ", response.invoiceId.ifBlank { response.extractedFields?.invoiceId })
        GrowFactRow(
            "Tổng tiền",
            (response.invoiceTotal.takeIf { it > 0 } ?: response.extractedFields?.totalAmount)?.let { formatVnd(it) },
        )
    }

    if (analysis.explanations.isNotEmpty()) {
        Spacer(modifier = Modifier.height(12.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color.White)
                .padding(16.dp),
        ) {
            Text("Giải thích", fontWeight = FontWeight.SemiBold)
            analysis.explanations.take(4).forEach { explanation ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(explanation.label, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodySmall)
                Text(explanation.detail, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                HorizontalDivider(modifier = Modifier.padding(top = 8.dp), color = Color(0xFFF3F4F6))
            }
        }
    }
}

@Composable
private fun GrowPill(text: String) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Color.White.copy(alpha = 0.85f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    ) {
        Text(text, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun GrowFactRow(label: String, value: String?) {
    if (value.isNullOrBlank()) return
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        Text(value, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodySmall)
    }
}

private fun formatVnd(amount: Long): String =
    NumberFormat.getNumberInstance(Locale("vi", "VN")).format(amount) + " đ"

private fun formatLoanReadiness(readiness: String): String =
    when {
        readiness.contains("not_ready") -> "Chưa đủ hồ sơ"
        readiness.contains("needs_more") -> "Cần thêm hóa đơn"
        readiness.contains("ready") -> "Tín hiệu tích cực"
        else -> readiness.replace('_', ' ')
    }

private fun formatRecommendedAction(analysis: ai.fides.sdk.GrowAnalyzeResponse): String {
    val action = analysis.recommendedAction
    if (action.contains("2") || action.contains("more invoice", ignoreCase = true)) {
        return when {
            analysis.trustScore >= 75 ->
                "Hóa đơn này qua ngưỡng sơ bộ. Cần thêm 2–3 hóa đơn (hoặc sao kê) trước khi đề xuất hạn mức vay."
            analysis.trustScore >= 55 ->
                "Phân tích sơ bộ từ một biên lai. Thêm 2–3 hóa đơn để dựng lịch sử dòng tiền và đề xuất hạn mức."
            else ->
                "Một hóa đơn chưa đủ mô tả doanh nghiệp. Thu thêm hóa đơn trước khi gợi ý tín dụng."
        }
    }
    return action
}
