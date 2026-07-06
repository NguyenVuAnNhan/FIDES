package ai.fides.sample.ui.screens

import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import ai.fides.sdk.ShieldTransaction
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.theme.FidesPrimaryGradient
import ai.fides.sample.ui.theme.FidesTeal
import java.text.NumberFormat
import java.util.Locale

@Composable
fun VoiceVerificationScreen(
    transaction: ShieldTransaction,
    cccdFilename: String?,
    cameraReady: Boolean,
    liveCheckStatus: String,
    errorMessage: String?,
    recordingSeconds: Int?,
    liveCheckReady: Boolean,
    verifying: Boolean,
    onClose: () -> Unit,
    onPickCccd: () -> Unit,
    onStartLiveCheck: () -> Unit,
    onVerify: () -> Unit,
    previewViewFactory: () -> PreviewView,
) {
    val phrase = "VD: “Tôi chuyển ${formatVnd(transaction.amount)} cho ${transaction.recipientName} để thanh toán tiền hàng.”"

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .statusBarsPadding()
            .padding(20.dp),
    ) {
        RowHeader(onClose)
        Spacer(modifier = Modifier.height(8.dp))
        FidesPrimaryButton(
            text = if (cccdFilename == null) "Chọn ảnh CCCD" else "CCCD: $cccdFilename",
            onClick = onPickCccd,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFF0F172A)),
            contentAlignment = Alignment.Center,
        ) {
            AndroidView(factory = { previewViewFactory() }, modifier = Modifier.fillMaxSize())
            if (!cameraReady) {
                Text("Đang bật camera...", color = Color.White.copy(alpha = 0.8f))
            }
        }
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            "Hãy nêu rõ lý do chuyển tiền trong ~10 giây:",
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Text(phrase, color = FidesTeal, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
        if (liveCheckStatus.isNotBlank()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(liveCheckStatus, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        }
        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(errorMessage, color = Color(0xFFC62828), style = MaterialTheme.typography.bodySmall)
        }
        if (verifying) {
            Spacer(modifier = Modifier.height(12.dp))
            RowWithProgress("Đang upload và xác minh với FIDES Shield...")
        }
        if (recordingSeconds != null) {
            Text("Đang ghi… ${recordingSeconds}s", color = FidesTeal, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.weight(1f))
        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(FidesPrimaryGradient)
                    .padding(4.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    if (verifying) "..." else if (recordingSeconds != null) "$recordingSeconds" else "Ghi",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        Spacer(modifier = Modifier.height(12.dp))
        if (!liveCheckReady) {
            FidesPrimaryButton(
                text = if (recordingSeconds != null) "Đang ghi..." else "Bắt đầu live check (10s)",
                enabled = cameraReady && cccdFilename != null && recordingSeconds == null && !verifying,
                onClick = onStartLiveCheck,
            )
        } else {
            FidesPrimaryButton(
                text = if (verifying) "Đang xác minh..." else "Xác minh & tiếp tục",
                enabled = !verifying,
                onClick = onVerify,
            )
        }
        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun RowHeader(onClose: () -> Unit) {
    androidx.compose.foundation.layout.Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("Xác minh danh tính", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
        IconButton(onClick = onClose) {
            Icon(Icons.Default.Close, contentDescription = "Đóng")
        }
    }
}

private fun formatVnd(amount: Long): String =
    NumberFormat.getNumberInstance(Locale("vi", "VN")).format(amount) + " VND"

@Composable
private fun RowWithProgress(message: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator(
            modifier = Modifier.size(18.dp),
            color = FidesTeal,
            strokeWidth = 2.dp,
        )
        Spacer(modifier = Modifier.width(10.dp))
        Text(message, color = FidesTeal, style = MaterialTheme.typography.bodySmall)
    }
}
