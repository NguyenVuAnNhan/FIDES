package ai.fides.sample.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.components.ShieldIllustration
import ai.fides.sample.ui.theme.FidesTeal

private data class TxItem(val amount: String, val name: String, val time: String, val date: String, val income: Boolean)

private val demoTransactions = listOf(
    TxItem("+ 500.000 VND", "Tran Binh Minh chuyen khoan", "13:45", "13/06/26", true),
    TxItem("- 1.200.000 VND", "Nguyen Van An thanh toan", "11:20", "13/06/26", false),
    TxItem("+ 2.000.000 VND", "Le Thi Hoa chuyen tien", "09:05", "12/06/26", true),
)

@Composable
fun HomeScreen(onCheckTransaction: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
    ) {
        Spacer(modifier = Modifier.height(12.dp))
        Text("Xin chào,", style = MaterialTheme.typography.bodyLarge, color = Color.Gray)
        Text("Jay Nguyễn!", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("FIDES – Bảo vệ tài chính của bạn.", color = Color.Gray, style = MaterialTheme.typography.bodySmall)

        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            ShieldIllustration()
        }

        FidesPrimaryButton(text = "Kiểm tra giao dịch", onClick = onCheckTransaction)
        Spacer(modifier = Modifier.height(20.dp))

        Row(verticalAlignment = Alignment.CenterVertically) {
            HorizontalDivider(modifier = Modifier.weight(1f))
            Text("  KẾT QUẢ  ", fontWeight = FontWeight.Bold, color = Color.Gray, style = MaterialTheme.typography.labelSmall)
            HorizontalDivider(modifier = Modifier.weight(1f))
        }
        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(999.dp))
                .background(Color(0xFFF3F4F6))
                .padding(4.dp),
        ) {
            listOf("Tất cả", "Mới", "Nguy cơ").forEachIndexed { index, tab ->
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(if (index == 1) Color.White else Color.Transparent)
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                ) {
                    Text(tab, fontSize = MaterialTheme.typography.bodySmall.fontSize, color = if (index == 1) Color.Black else Color.Gray)
                }
            }
        }

        demoTransactions.forEach { tx ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { }
                    .padding(vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(tx.amount, fontWeight = FontWeight.SemiBold, color = if (tx.income) FidesTeal else Color.DarkGray)
                    Text(tx.name, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(tx.time, color = Color.DarkGray)
                    Text(tx.date, color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                }
            }
            HorizontalDivider(color = Color(0xFFF3F4F6))
        }
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
fun StatisticsScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Thống kê", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Bao gồm các giao dịch gần đây và chi tiết", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
        Spacer(modifier = Modifier.height(16.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFF8FAFC)),
            contentAlignment = Alignment.Center,
        ) {
            Text("Biểu đồ giao dịch 7 ngày", color = Color.Gray)
        }
        Spacer(modifier = Modifier.height(16.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFF0FAFB))
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Bạn đã giao dịch:", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
            Text("13.140.000 đ", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(12.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatCell("38", "Giao dịch")
                StatCell("24", "Đối tác")
                StatCell("0", "Nguy cơ")
            }
        }
    }
}

@Composable
private fun StatCell(value: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.headlineSmall)
        Text(label, color = Color.Gray, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
fun LoanScreen(onRegister: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("Khoản vay", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(16.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFE0F7FA))
                .padding(16.dp),
        ) {
            Column {
                Text("Chọn khoản vay", color = Color.Gray)
                Text("10.000.000 đ", color = FidesTeal, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.headlineSmall)
            }
        }
        Spacer(modifier = Modifier.height(16.dp))
        Text("Ước tính trả hàng tháng: 920.000 đ", color = Color.Gray)
        Spacer(modifier = Modifier.height(24.dp))
        FidesPrimaryButton(text = "Đăng ký ngay", onClick = onRegister)
    }
}
