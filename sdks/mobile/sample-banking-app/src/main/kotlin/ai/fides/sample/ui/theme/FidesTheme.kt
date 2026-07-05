package ai.fides.sample.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

val FidesTeal = Color(0xFF00ACC1)
val FidesTealDark = Color(0xFF0097A7)
val FidesTealLight = Color(0xFF26C6DA)
val FidesSurface = Color(0xFFF0FAFB)
val FidesGradientStart = Color(0xFF26C6DA)
val FidesGradientEnd = Color(0xFF0097A7)

val FidesPrimaryGradient = Brush.horizontalGradient(listOf(FidesGradientStart, FidesGradientEnd))

private val LightColors = lightColorScheme(
    primary = FidesTeal,
    onPrimary = Color.White,
    secondary = FidesTealLight,
    background = Color.White,
    surface = Color.White,
)

@Composable
fun FidesTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = LightColors, content = content)
}
