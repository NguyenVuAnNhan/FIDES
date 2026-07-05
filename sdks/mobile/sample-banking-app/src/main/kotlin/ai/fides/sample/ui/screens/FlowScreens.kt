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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import ai.fides.sdk.ShieldTransaction
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.theme.FidesTeal

@Composable
fun TransferScreen(
    loading: Boolean,
    error: String?,
    onClose: () -> Unit,
    onConfirm: (ShieldTransaction) -> Unit,
) {
    var amount by remember { mutableStateOf("65000000") }
    var recipient by remember { mutableStateOf("Tran Van B") }
    var account by remember { mutableStateOf("9704 2222 8800") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Xác nhận chuyển khoản", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
            IconButton(onClick = onClose) {
                Icon(Icons.Default.Close, contentDescription = "Đóng")
            }
        }
        Text(
            "FIDES kiểm tra cuộc gọi và thiết bị ở background trước khi cho phép giao dịch.",
            color = Color.Gray,
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(modifier = Modifier.height(16.dp))
        OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text("Số tiền (VND)") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = recipient, onValueChange = { recipient = it }, label = { Text("Tên người nhận") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = account, onValueChange = { account = it }, label = { Text("Số tài khoản") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(12.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFFFFF7ED))
                .padding(12.dp),
        ) {
            Text("Đang có cuộc gọi · Người nhận chưa lưu · Số tiền lớn", color = Color(0xFF9A3412), style = MaterialTheme.typography.bodySmall)
        }
        if (error != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(error, color = Color.Red, style = MaterialTheme.typography.bodySmall)
        }
        Spacer(modifier = Modifier.height(24.dp))
        FidesPrimaryButton(
            text = if (loading) "Đang kiểm tra..." else "Xác nhận chuyển khoản",
            enabled = !loading,
            onClick = {
                onConfirm(
                    ShieldTransaction(
                        amount = amount.toLongOrNull() ?: 0L,
                        recipientName = recipient.trim(),
                        recipientAccount = account.trim(),
                        recipientKnown = false,
                    ),
                )
            },
        )
    }
}

@Composable
fun WarningOverlay(
    message: String,
    riskScore: Int,
    onBack: () -> Unit,
    onContinue: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        Box(modifier = Modifier.fillMaxSize().background(Color.White.copy(alpha = 0.35f)))
        Column(
            modifier = Modifier
                .align(Alignment.Center)
                .padding(horizontal = 20.dp)
                .clip(RoundedCornerShape(24.dp))
                .background(Color.White)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Thông báo can thiệp từ FIDES", color = Color.Gray, style = MaterialTheme.typography.labelMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Text("⚠", style = MaterialTheme.typography.displayMedium)
            Text("Cảnh báo!", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.headlineMedium)
            Text("Risk $riskScore/100", color = FidesTeal, fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(8.dp))
            Text(message, color = Color.DarkGray, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(16.dp))
            FidesPrimaryButton(text = "Tôi hiểu rủi ro, tiếp tục", onClick = onContinue)
            Spacer(modifier = Modifier.height(8.dp))
            FidesPrimaryButton(text = "Quay lại", onClick = onBack)
        }
    }
}

@Composable
fun ResultScreen(
    title: String,
    message: String,
    action: String,
    riskScore: Int,
    onClose: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("✓", style = MaterialTheme.typography.displayLarge, color = FidesTeal)
        Text(title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(8.dp))
        Text(message, color = Color.Gray, style = MaterialTheme.typography.bodyMedium)
        Spacer(modifier = Modifier.height(16.dp))
        Text("Risk $riskScore/100 · ${action.replace('_', ' ')}", color = Color.DarkGray, style = MaterialTheme.typography.bodySmall)
        Spacer(modifier = Modifier.height(24.dp))
        FidesPrimaryButton(text = "Về trang chủ", onClick = onClose)
    }
}
