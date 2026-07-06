package ai.fides.sample.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ai.fides.sdk.CallListenResult
import ai.fides.sample.GuardianDecision
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.theme.FidesTeal

private val DangerRed = Color(0xFFC62828)
private val DangerBg = Color(0xFFFDECEA)
private val SafeGreen = Color(0xFF2E7D32)
private val SafeBg = Color(0xFFE8F5E9)

@Composable
fun CallListenScreen(
    filename: String?,
    statusMessage: String,
    loading: Boolean,
    errorMessage: String?,
    result: CallListenResult?,
    guardianDecision: GuardianDecision,
    onPickAudio: () -> Unit,
    onGuardianDecision: (Boolean) -> Unit,
    onReset: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .statusBarsPadding()
            .padding(horizontal = 20.dp),
    ) {
        Spacer(modifier = Modifier.height(12.dp))
        Text("Giám sát cuộc gọi", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(
            "FIDES nghe đoạn hội thoại và dùng AI (SmartVoice + SmartBot) phát hiện dấu hiệu lừa đảo, cảnh báo và báo người giám hộ.",
            color = Color.Gray,
            style = MaterialTheme.typography.bodySmall,
        )

        Spacer(modifier = Modifier.height(16.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFE8F5F4))
                .padding(16.dp),
        ) {
            Text("Cuộc gọi đến nghi ngờ?", fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                "Tải lên file ghi âm cuộc gọi (WAV/MP3/M4A…). FIDES sẽ chuyển giọng nói thành văn bản và phân tích lừa đảo.",
                color = Color.DarkGray,
                style = MaterialTheme.typography.bodySmall,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        if (filename != null) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(bottom = 8.dp)) {
                Text("File đã chọn: ", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                Text(filename, color = Color.DarkGray, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodySmall)
            }
        }
        FidesPrimaryButton(
            text = if (filename == null) "Chọn file audio cuộc gọi" else "Chọn file khác",
            enabled = !loading,
            onClick = onPickAudio,
        )

        if (statusMessage.isNotBlank()) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(statusMessage, color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
        }
        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(errorMessage, color = DangerRed, style = MaterialTheme.typography.bodySmall)
        }
        if (loading) {
            Spacer(modifier = Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(color = FidesTeal, modifier = Modifier.padding(end = 12.dp))
                Text("Đang phân tích hội thoại...", color = Color.Gray)
            }
        }

        result?.let { res ->
            Spacer(modifier = Modifier.height(20.dp))
            CallResultCard(res)
            if (res.guardianAlert) {
                Spacer(modifier = Modifier.height(12.dp))
                GuardianCard(res, guardianDecision, onGuardianDecision)
            }
            CallTechnicalDetail(res)
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                "Phân tích cuộc gọi khác",
                color = FidesTeal,
                fontWeight = FontWeight.Medium,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onReset() }
                    .padding(vertical = 10.dp),
            )
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun CallResultCard(res: CallListenResult) {
    val scam = res.isScam
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(if (scam) DangerBg else SafeBg)
            .padding(16.dp),
    ) {
        Text(
            if (scam) "⚠ Phát hiện dấu hiệu lừa đảo" else "✓ Không thấy dấu hiệu lừa đảo",
            color = if (scam) DangerRed else SafeGreen,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(res.scamTypeLabel, color = Color.DarkGray, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CallPill(riskLabel(res.riskLevel))
            res.confidence?.let { CallPill("Độ tin cậy ${(it * 100).toInt()}%") }
        }
        if (res.interventionMessage.isNotBlank()) {
            Spacer(modifier = Modifier.height(10.dp))
            Text(res.interventionMessage, color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
        }
    }

    if (res.sttTranscript.isNotBlank()) {
        Spacer(modifier = Modifier.height(12.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFF8FAFC))
                .padding(16.dp),
        ) {
            Text("Nội dung nghe được (SmartVoice STT)", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodySmall)
            Spacer(modifier = Modifier.height(6.dp))
            Text("“${res.sttTranscript}”", color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
            if (res.detectedPatterns.isNotEmpty()) {
                Spacer(modifier = Modifier.height(10.dp))
                Text("Dấu hiệu:", color = Color.Gray, style = MaterialTheme.typography.labelSmall)
                Spacer(modifier = Modifier.height(4.dp))
                PatternChips(res.detectedPatterns)
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PatternChips(patterns: List<String>) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        patterns.forEach { pattern ->
            Box(
                modifier = Modifier
                    .padding(vertical = 2.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(DangerBg)
                    .padding(horizontal = 10.dp, vertical = 4.dp),
            ) {
                Text(patternLabel(pattern), color = DangerRed, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun GuardianCard(
    res: CallListenResult,
    decision: GuardianDecision,
    onDecision: (Boolean) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFFFFF8E1))
            .padding(16.dp),
    ) {
        Text("Đã gửi cảnh báo cho người giám hộ", fontWeight = FontWeight.Bold, color = Color(0xFF8D6E00))
        Spacer(modifier = Modifier.height(6.dp))
        Text(res.guardianMessage, color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
        Spacer(modifier = Modifier.height(4.dp))
        Text("(Mô phỏng: thông báo push/SMS tới người thân đã đăng ký)", color = Color.Gray, style = MaterialTheme.typography.labelSmall)
        Spacer(modifier = Modifier.height(12.dp))

        when (decision) {
            GuardianDecision.PENDING -> {
                FidesPrimaryButton(text = "Người giám hộ: Xác nhận an toàn", onClick = { onDecision(true) })
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(DangerRed)
                        .clickable { onDecision(false) },
                    contentAlignment = Alignment.Center,
                ) {
                    Text("Người giám hộ: Chặn & khoá giao dịch", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }
            GuardianDecision.APPROVED -> {
                Text(
                    "✓ Người giám hộ đã xác nhận đây là giao dịch hợp lệ. Cảnh báo được gỡ.",
                    color = SafeGreen,
                    fontWeight = FontWeight.Medium,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            GuardianDecision.REJECTED -> {
                Text(
                    "⛔ Người giám hộ đã chặn. Giao dịch bị khoá 24h và FIDES đã báo bộ phận chống lừa đảo của ngân hàng.",
                    color = DangerRed,
                    fontWeight = FontWeight.Medium,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun CallTechnicalDetail(res: CallListenResult) {
    if (res.explanations.isEmpty()) return
    var show by remember { mutableStateOf(false) }
    Spacer(modifier = Modifier.height(12.dp))
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White)
            .padding(horizontal = 16.dp),
    ) {
        Text(
            if (show) "Ẩn chi tiết kỹ thuật ▲" else "Chi tiết kỹ thuật ▾",
            color = FidesTeal,
            fontWeight = FontWeight.Medium,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier
                .fillMaxWidth()
                .clickable { show = !show }
                .padding(vertical = 10.dp),
        )
        if (show) {
            Text("Provider: ${res.providerMode}", color = Color.Gray, style = MaterialTheme.typography.labelSmall)
            res.explanations.forEach { ex ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(ex.label, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodySmall)
                Text(ex.detail, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                HorizontalDivider(modifier = Modifier.padding(top = 8.dp), color = Color(0xFFF3F4F6))
            }
        }
    }
}

@Composable
private fun CallPill(text: String) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Color.White.copy(alpha = 0.85f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    ) {
        Text(text, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium)
    }
}

private fun riskLabel(level: String): String =
    when (level) {
        "high" -> "Nguy cơ cao"
        "medium" -> "Nguy cơ trung bình"
        else -> "An toàn"
    }

private fun patternLabel(pattern: String): String =
    when (pattern) {
        "fake_authority" -> "Giả danh cơ quan"
        "otp_theft" -> "Lấy cắp OTP"
        "investment" -> "Dụ đầu tư"
        "remote_support" -> "Điều khiển từ xa"
        else -> pattern
    }
