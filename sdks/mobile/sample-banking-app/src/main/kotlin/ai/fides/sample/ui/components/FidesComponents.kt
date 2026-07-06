package ai.fides.sample.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.fides.sample.AppTab
import ai.fides.sample.ui.theme.FidesTeal

@Composable
fun FidesBottomNav(active: AppTab, onNavigate: (AppTab) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            NavItem("Trang chủ", Icons.Default.Home, active == AppTab.HOME) { onNavigate(AppTab.HOME) }
            NavItem("Cuộc gọi", Icons.Default.Call, active == AppTab.CALL) { onNavigate(AppTab.CALL) }
            NavItem("Thống kê", Icons.Default.PieChart, active == AppTab.STATS) { onNavigate(AppTab.STATS) }
            NavItem("Khoản vay", Icons.Default.CreditCard, active == AppTab.LOAN) { onNavigate(AppTab.LOAN) }
        }
        Box(
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .padding(bottom = 8.dp)
                .size(width = 128.dp, height = 4.dp)
                .clip(RoundedCornerShape(50))
                .background(Color.Black.copy(alpha = 0.15f)),
        )
    }
}

@Composable
private fun NavItem(label: String, icon: ImageVector, active: Boolean, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 4.dp),
    ) {
        Icon(icon, contentDescription = label, tint = if (active) FidesTeal else Color.Gray, modifier = Modifier.size(24.dp))
        Text(
            text = label,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
            color = if (active) FidesTeal else Color.Gray,
        )
    }
}

@Composable
fun FidesPrimaryButton(text: String, enabled: Boolean = true, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(
                if (enabled) ai.fides.sample.ui.theme.FidesPrimaryGradient
                else androidx.compose.ui.graphics.Brush.linearGradient(listOf(Color.Gray, Color.Gray)),
            )
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = Color.White, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
fun ShieldIllustration(modifier: Modifier = Modifier) {
    Box(modifier = modifier.size(160.dp), contentAlignment = Alignment.Center) {
        Box(
            modifier = Modifier
                .size(180.dp)
                .clip(RoundedCornerShape(999.dp))
                .background(FidesTeal.copy(alpha = 0.08f)),
        )
        Text("🛡", fontSize = 72.sp)
    }
}
