package ai.fides.sample.ui

import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import ai.fides.sample.AppOverlay
import ai.fides.sample.AppTab
import ai.fides.sample.ShieldUiState
import ai.fides.sample.ui.components.FidesBottomNav
import ai.fides.sample.ui.screens.HomeScreen
import ai.fides.sample.ui.screens.LoanScreen
import ai.fides.sample.ui.screens.ResultScreen
import ai.fides.sample.ui.screens.StatisticsScreen
import ai.fides.sample.ui.screens.TransferScreen
import ai.fides.sample.ui.screens.VoiceVerificationScreen
import ai.fides.sample.ui.screens.WarningOverlay
import ai.fides.sdk.ShieldTransaction

@Composable
fun FidesApp(
    state: ShieldUiState,
    onNavigate: (AppTab) -> Unit,
    onCheckTransaction: () -> Unit,
    onConfirmTransfer: (ShieldTransaction) -> Unit,
    onWarningBack: () -> Unit,
    onWarningContinue: () -> Unit,
    onCloseOverlay: () -> Unit,
    onPickCccd: () -> Unit,
    onStartLiveCheck: () -> Unit,
    onVerify: () -> Unit,
    previewViewFactory: () -> PreviewView,
) {
    Column(modifier = Modifier.fillMaxSize().background(Color.White)) {
        Box(modifier = Modifier.weight(1f)) {
            when (state.tab) {
                AppTab.HOME -> if (state.overlay == AppOverlay.NONE || state.overlay == AppOverlay.WARNING) {
                    HomeScreen(onCheckTransaction = onCheckTransaction)
                }
                AppTab.STATS -> StatisticsScreen()
                AppTab.LOAN -> LoanScreen(onRegister = onCheckTransaction)
            }

            when (state.overlay) {
                AppOverlay.TRANSFER -> TransferScreen(
                    loading = state.loading,
                    error = state.errorMessage,
                    onClose = onCloseOverlay,
                    onConfirm = onConfirmTransfer,
                )
                AppOverlay.WARNING -> state.analyzeResponse?.let { response ->
                    WarningOverlay(
                        message = response.interventionMessage,
                        riskScore = response.riskScore,
                        onBack = onWarningBack,
                        onContinue = onWarningContinue,
                    )
                }
                AppOverlay.VOICE -> state.transaction?.let { transaction ->
                    VoiceVerificationScreen(
                        transaction = transaction,
                        cccdFilename = state.cccdFilename,
                        cameraReady = state.cameraReady,
                        liveCheckStatus = state.liveCheckStatus,
                        recordingSeconds = state.recordingSeconds,
                        liveCheckReady = state.liveCheckReady,
                        verifying = state.loading,
                        onClose = onCloseOverlay,
                        onPickCccd = onPickCccd,
                        onStartLiveCheck = onStartLiveCheck,
                        onVerify = onVerify,
                        previewViewFactory = previewViewFactory,
                    )
                }
                AppOverlay.RESULT -> {
                    val result = state.finalResponse ?: state.analyzeResponse
                    if (result != null) {
                        val success = result.action == "allow_with_notice" || result.action == "allow_after_challenge"
                        ResultScreen(
                            title = when {
                                success -> "Giao dịch được phép"
                                result.action.contains("withhold") -> "Giao dịch bị tạm giữ"
                                else -> "Cần xem xét thêm"
                            },
                            message = result.interventionMessage,
                            action = result.action,
                            riskScore = result.riskScore,
                            onClose = onCloseOverlay,
                        )
                    }
                }
                AppOverlay.NONE -> Unit
            }
        }

        if (state.overlay == AppOverlay.NONE) {
            FidesBottomNav(active = state.tab, onNavigate = onNavigate)
        }
    }
}
