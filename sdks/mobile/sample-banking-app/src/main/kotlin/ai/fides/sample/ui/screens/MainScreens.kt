package ai.fides.sample.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ai.fides.sample.ui.components.FidesPrimaryButton
import ai.fides.sample.ui.components.ShieldIllustration
import ai.fides.sample.ui.theme.FidesTeal
import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.pow

private data class TxItem(val amount: String, val name: String, val time: String, val date: String, val income: Boolean)

private val demoTransactions = listOf(
    TxItem("+ 500.000 VND", "Tran Binh Minh chuyen khoan", "13:45", "13/06/26", true),
    TxItem("- 1.200.000 VND", "Nguyen Van An thanh toan", "11:20", "13/06/26", false),
    TxItem("+ 2.000.000 VND", "Le Thi Hoa chuyen tien", "09:05", "12/06/26", true),
)

@Composable
fun HomeScreen(
    sessionRiskScore: Int?,
    sessionRiskLevel: String?,
    sessionMonitoringMessage: String?,
    sessionEarlyWarning: Boolean,
    onCheckTransaction: () -> Unit,
) {
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

        if (sessionRiskScore != null) {
            Spacer(modifier = Modifier.height(12.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(if (sessionEarlyWarning) Color(0xFFFFF3E0) else Color(0xFFE8F5F4))
                    .padding(14.dp),
            ) {
                Text(
                    "Shield đang theo dõi phiên app",
                    fontWeight = FontWeight.SemiBold,
                    color = if (sessionEarlyWarning) Color(0xFFE65100) else FidesTeal,
                )
                Text(
                    "Session risk ${sessionRiskScore}/100 · ${sessionRiskLevel ?: "unknown"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.DarkGray,
                )
                if (!sessionMonitoringMessage.isNullOrBlank()) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(sessionMonitoringMessage, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                }
            }
        }

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
fun LoanScreen(
    initialAmount: Long = 10_000_000,
    initialTermMonths: Int = 12,
    onRegister: (amount: Long, termMonths: Int) -> Unit,
) {
    var amount by remember { mutableLongStateOf(initialAmount) }
    var selectedTerm by remember { mutableIntStateOf(initialTermMonths) }
    var showBreakdown by remember { mutableStateOf(false) }

    val monthly = calcMonthlyPayment(amount, selectedTerm)
    val total = monthly * selectedTerm
    val startDate = LocalDate.now().plusMonths(1)
    val startDateStr = startDate.format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp),
    ) {
        Spacer(modifier = Modifier.height(12.dp))
        Text("Khoản vay", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(16.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Brush.linearGradient(listOf(Color(0xFFE0F7FA), Color(0xFFB2EBF2))))
                .padding(16.dp),
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Text("Chọn khoản vay", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                Text("Bạn muốn vay:", color = Color.Gray, style = MaterialTheme.typography.labelSmall)
                Text(
                    formatVnd(amount),
                    color = FidesTeal,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.headlineSmall,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Slider(
                    value = amount.toFloat(),
                    onValueChange = { amount = (it / 500_000f).toLong() * 500_000 },
                    valueRange = 1_000_000f..100_000_000f,
                    steps = ((100_000_000 - 1_000_000) / 500_000) - 1,
                    colors = SliderDefaults.colors(
                        thumbColor = FidesTeal,
                        activeTrackColor = FidesTeal,
                        inactiveTrackColor = Color(0xFFB2EBF2),
                    ),
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            LOAN_TERMS.forEach { term ->
                val selected = term == selectedTerm
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(
                            if (selected) {
                                Brush.linearGradient(listOf(Color(0xFF26C6DA), Color(0xFF00ACC1)))
                            } else {
                                Brush.linearGradient(listOf(Color.White, Color.White))
                            },
                        )
                        .clickable { selectedTerm = term }
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                ) {
                    Text(
                        "$term tháng",
                        color = if (selected) Color.White else Color.Gray,
                        fontWeight = FontWeight.Medium,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color.White)
                .padding(20.dp),
        ) {
            Text(
                "Ước tính số tiền phải trả hàng tháng:",
                color = Color.Gray,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
            Text(
                formatVnd(monthly),
                color = FidesTeal,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )
            Spacer(modifier = Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                LoanInfoCell("Số tiền thực nhận", formatVnd(amount), modifier = Modifier.weight(1f))
                LoanInfoCell("Ngày bắt đầu trả", startDateStr, modifier = Modifier.weight(1f))
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .clickable { showBreakdown = !showBreakdown }
                .padding(horizontal = 16.dp, vertical = 14.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Tổng dự kiến phải trả:", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(formatVnd(total), fontWeight = FontWeight.Bold)
                    androidx.compose.material3.Icon(
                        Icons.Default.KeyboardArrowDown,
                        contentDescription = null,
                        tint = Color.Gray,
                        modifier = Modifier.rotate(if (showBreakdown) 180f else 0f),
                    )
                }
            }
            if (showBreakdown) {
                Spacer(modifier = Modifier.height(12.dp))
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFF8FAFC))
                        .padding(12.dp),
                ) {
                    LoanBreakdownRow("Gốc vay", formatVnd(amount))
                    LoanBreakdownRow("Lãi dự kiến", formatVnd(total - amount))
                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = Color(0xFFE5E7EB))
                    LoanBreakdownRow("Tổng cộng", formatVnd(total), highlight = true)
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))
        Text(
            "Thông tin Đăng ký vay nhanh sẽ được chuyển về ngân hàng và xử lý trong vòng 2h sau khi đăng ký!",
            color = Color.Gray,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.align(Alignment.CenterHorizontally),
        )
        Spacer(modifier = Modifier.height(20.dp))
        FidesPrimaryButton(text = "Đăng ký ngay", onClick = { onRegister(amount, selectedTerm) })
        Spacer(modifier = Modifier.height(24.dp))
    }
}

private val LOAN_TERMS = listOf(9, 12, 15, 18, 20, 24)
private const val LOAN_INTEREST_RATE = 0.009

private fun calcMonthlyPayment(principal: Long, months: Int): Long {
    val rate = LOAN_INTEREST_RATE
    val factor = (1 + rate).pow(months.toDouble())
    return kotlin.math.round((principal * rate * factor) / (factor - 1)).toLong()
}

private fun formatVnd(amount: Long): String =
    NumberFormat.getNumberInstance(Locale("vi", "VN")).format(amount) + " đ"

@Composable
private fun LoanInfoCell(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFFF8FAFC))
            .padding(12.dp),
    ) {
        Text(label, color = Color.Gray, style = MaterialTheme.typography.labelSmall)
        Text(value, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun LoanBreakdownRow(label: String, value: String, highlight: Boolean = false) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = if (highlight) Color.DarkGray else Color.Gray, style = MaterialTheme.typography.bodySmall)
        Text(
            value,
            fontWeight = if (highlight) FontWeight.Bold else FontWeight.Medium,
            color = if (highlight) FidesTeal else Color.Black,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
