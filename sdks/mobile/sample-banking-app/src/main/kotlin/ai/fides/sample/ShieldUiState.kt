package ai.fides.sample

import ai.fides.sdk.GrowProcessResponse
import ai.fides.sdk.ShieldAnalyzeResponse
import ai.fides.sdk.ShieldTransaction

enum class AppTab { HOME, STATS, LOAN }

enum class AppOverlay { NONE, TRANSFER, WARNING, VOICE, RESULT, GROW }

data class ShieldUiState(
    val tab: AppTab = AppTab.HOME,
    val overlay: AppOverlay = AppOverlay.NONE,
    val loading: Boolean = false,
    val statusMessage: String = "",
    val errorMessage: String? = null,
    val transaction: ShieldTransaction? = null,
    val analyzeResponse: ShieldAnalyzeResponse? = null,
    val finalResponse: ShieldAnalyzeResponse? = null,
    val cccdFilename: String? = null,
    val cameraReady: Boolean = false,
    val liveCheckStatus: String = "",
    val recordingSeconds: Int? = null,
    val liveCheckReady: Boolean = false,
    val loanAmount: Long = 10_000_000,
    val loanTermMonths: Int = 12,
    val growStatusMessage: String = "",
    val growReceiptFilename: String? = null,
    val growResponse: GrowProcessResponse? = null,
)
