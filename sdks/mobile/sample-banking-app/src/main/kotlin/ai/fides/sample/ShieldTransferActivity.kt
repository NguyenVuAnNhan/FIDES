package ai.fides.sample

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import ai.fides.sdk.FidesConsent
import ai.fides.sdk.FidesSdkResult
import ai.fides.sdk.ShieldTransaction
import ai.fides.sdk.capture.LiveCheckCapture
import ai.fides.sdk.capture.LiveCheckCaptureCallback
import ai.fides.sdk.capture.LiveCheckCaptureResult
import ai.fides.sdk.capture.toUploadInput
import ai.fides.sample.ui.FidesApp
import ai.fides.sample.ui.theme.FidesTheme

class ShieldTransferActivity : ComponentActivity() {
    private val app get() = application as FidesSampleApplication
    private lateinit var liveCapture: LiveCheckCapture
    private lateinit var previewView: PreviewView

    private var uiState by mutableStateOf(ShieldUiState())
    private val consent = FidesConsent(telemetry = true)
    private var cccdBytes: ByteArray? = null
    private var captureResult: LiveCheckCaptureResult? = null

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        if (REQUIRED_PERMISSIONS.all { grants[it] == true }) {
            pendingAction?.invoke()
            pendingAction = null
        } else {
            uiState = uiState.copy(errorMessage = "Cần quyền camera, mic và phone state.")
        }
    }

    private val cccdPicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) loadCccd(uri)
    }

    private val growReceiptPicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) loadGrowReceipt(uri)
    }

    private var growReceiptBytes: ByteArray? = null
    private var growReceiptContentType: String = "image/jpeg"
    private var growRequestGeneration = 0

    private var pendingAction: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        liveCapture = LiveCheckCapture(this, this)
        previewView = PreviewView(this)

        setContent {
            FidesTheme {
                FidesApp(
                    state = uiState,
                    onNavigate = { tab -> uiState = uiState.copy(tab = tab, overlay = AppOverlay.NONE) },
                    onCheckTransaction = { openTransfer() },
                    onConfirmTransfer = { confirmTransfer(it) },
                    onWarningBack = { resetShieldFlow() },
                    onWarningContinue = {
                        uiState = uiState.copy(overlay = AppOverlay.VOICE)
                        ensurePermissions { bindCamera() }
                    },
                    onCloseOverlay = { closeOverlay() },
                    onRegisterLoan = { amount, termMonths -> openGrow(amount, termMonths) },
                    onPickGrowReceipt = { growReceiptPicker.launch("image/*") },
                    onAnalyzeGrow = { analyzeGrowReceipt() },
                    onPickCccd = { cccdPicker.launch("image/*") },
                    onStartLiveCheck = { startLiveCheck() },
                    onVerify = { verifyIdentity() },
                    previewViewFactory = { previewView },
                )
            }
        }
    }

    override fun onDestroy() {
        liveCapture.release()
        super.onDestroy()
    }

    private fun openTransfer() {
        uiState = uiState.copy(overlay = AppOverlay.TRANSFER, errorMessage = null)
    }

    private fun openGrow(amount: Long, termMonths: Int) {
        growReceiptBytes = null
        uiState = uiState.copy(
            overlay = AppOverlay.GROW,
            loanAmount = amount,
            loanTermMonths = termMonths,
            loading = false,
            errorMessage = null,
            growStatusMessage = "Chọn ảnh hóa đơn để bắt đầu phân tích Grow.",
            growReceiptFilename = null,
            growResponse = null,
        )
    }

    private fun loadGrowReceipt(uri: Uri) {
        try {
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes == null || bytes.isEmpty()) {
                uiState = uiState.copy(errorMessage = "Ảnh hóa đơn trống.")
                return
            }
            val name = uri.lastPathSegment?.substringAfterLast('/') ?: "receipt.jpg"
            growReceiptBytes = bytes
            growReceiptContentType = contentResolver.getType(uri) ?: guessImageContentType(name)
            uiState = uiState.copy(
                growReceiptFilename = name,
                growResponse = null,
                errorMessage = null,
                growStatusMessage = "Đã chọn $name. Bấm Phân tích tín dụng hoặc đợi upload tự động.",
            )
            uploadGrowReceipt(name, bytes)
        } catch (error: Throwable) {
            uiState = uiState.copy(errorMessage = error.message)
        }
    }

    private fun uploadGrowReceipt(filename: String, bytes: ByteArray) {
        val generation = growRequestGeneration + 1
        growRequestGeneration = generation
        uiState = uiState.copy(loading = true, errorMessage = null, growStatusMessage = "Đang upload hóa đơn...")
        app.sdk.uploadGrowReceipt(bytes, filename, growReceiptContentType) { result ->
            runOnUiThread {
                if (generation != growRequestGeneration) return@runOnUiThread
                when (result) {
                    is FidesSdkResult.Failure -> {
                        uiState = uiState.copy(
                            loading = false,
                            errorMessage = formatApiError(result.message),
                            growStatusMessage = "Upload thất bại.",
                        )
                    }
                    is FidesSdkResult.Success -> {
                        uiState = uiState.copy(
                            loading = false,
                            growStatusMessage = "Upload xong. Đang chạy SmartReader OCR + chấm điểm tín dụng...",
                        )
                        processGrowInvoice(result.value.inputSource, generation)
                    }
                }
            }
        }
    }

    private fun analyzeGrowReceipt() {
        val bytes = growReceiptBytes
        val filename = uiState.growReceiptFilename
        if (bytes == null || filename == null) {
            uiState = uiState.copy(errorMessage = "Chọn ảnh hóa đơn trước.")
            return
        }
        uploadGrowReceipt(filename, bytes)
    }

    private fun processGrowInvoice(inputSource: String, generation: Int = growRequestGeneration) {
        uiState = uiState.copy(loading = true, errorMessage = null)
        app.sdk.processGrowInvoice(inputSource) { result ->
            runOnUiThread {
                if (generation != growRequestGeneration) return@runOnUiThread
                when (result) {
                    is FidesSdkResult.Failure -> {
                        uiState = uiState.copy(
                            loading = false,
                            errorMessage = formatApiError(result.message),
                            growStatusMessage = "Phân tích Grow thất bại.",
                        )
                    }
                    is FidesSdkResult.Success -> {
                        val response = result.value
                        uiState = uiState.copy(
                            loading = false,
                            growResponse = response,
                            growStatusMessage = "Phân tích xong qua ${response.ocrProvider ?: "OCR"}.",
                        )
                    }
                }
            }
        }
    }

    private fun guessImageContentType(filename: String): String =
        when (filename.substringAfterLast('.', "").lowercase()) {
            "png" -> "image/png"
            "webp" -> "image/webp"
            else -> "image/jpeg"
        }

    private fun formatApiError(message: String): String {
        return try {
            val detail = org.json.JSONObject(message).optString("detail")
            detail.ifBlank { message }
        } catch (_: Throwable) {
            message
        }
    }

    private fun confirmTransfer(transaction: ShieldTransaction) {
        uiState = uiState.copy(loading = true, errorMessage = null, transaction = transaction)
        ensurePermissions {
            app.sdk.analyzeShieldWithCall(transaction, consent, app.callMonitor) { result ->
                runOnUiThread {
                    when (result) {
                        is FidesSdkResult.Failure -> {
                            uiState = uiState.copy(loading = false, errorMessage = result.message)
                        }
                        is FidesSdkResult.Success -> {
                            val response = result.value
                            uiState = uiState.copy(
                                loading = false,
                                analyzeResponse = response,
                                overlay = if (response.requiresIdentityCheck) AppOverlay.WARNING else AppOverlay.RESULT,
                                finalResponse = if (response.requiresIdentityCheck) null else response,
                            )
                        }
                    }
                }
            }
        }
    }

    private fun bindCamera() {
        if (uiState.cameraReady) return
        liveCapture.bindPreview(
            previewView = previewView,
            onReady = {
                runOnUiThread {
                    uiState = uiState.copy(cameraReady = true, liveCheckStatus = "Camera sẵn sàng.")
                }
            },
            onError = { message ->
                runOnUiThread {
                    uiState = uiState.copy(errorMessage = message)
                }
            },
        )
    }

    private fun startLiveCheck() {
        if (cccdBytes == null) {
            uiState = uiState.copy(errorMessage = "Chọn ảnh CCCD trước.")
            return
        }
        captureResult = null
        uiState = uiState.copy(liveCheckReady = false, liveCheckStatus = "Đang ghi...")
        liveCapture.startRecording(
            callback = object : LiveCheckCaptureCallback {
                override fun onTick(secondsRemaining: Int) {
                    runOnUiThread {
                        uiState = uiState.copy(recordingSeconds = secondsRemaining)
                    }
                }

                override fun onSuccess(result: LiveCheckCaptureResult) {
                    runOnUiThread {
                        captureResult = result
                        uiState = uiState.copy(
                            recordingSeconds = null,
                            liveCheckReady = true,
                            liveCheckStatus = "Đã ghi ${result.frames.size} frame. Bấm Xác minh.",
                        )
                    }
                }

                override fun onFailure(message: String, cause: Throwable?) {
                    runOnUiThread {
                        uiState = uiState.copy(
                            recordingSeconds = null,
                            errorMessage = message,
                            liveCheckStatus = message,
                        )
                    }
                }
            },
        )
    }

    private fun verifyIdentity() {
        val transaction = uiState.transaction
        if (transaction == null) {
            uiState = uiState.copy(errorMessage = "Thiếu thông tin giao dịch. Quay lại và thử lại.")
            return
        }
        val document = cccdBytes
        if (document == null) {
            uiState = uiState.copy(errorMessage = "Chọn ảnh CCCD trước khi xác minh.")
            return
        }
        val capture = captureResult
        if (capture == null) {
            uiState = uiState.copy(
                errorMessage = "Chưa có video live check. Bấm Bắt đầu live check trước.",
                liveCheckReady = false,
            )
            return
        }

        uiState = uiState.copy(
            loading = true,
            errorMessage = null,
            liveCheckStatus = "Đang upload video, frame và chạy eKYC + voice stress...",
        )
        app.sdk.runIdentityCheck(
            transaction,
            consent,
            capture.toUploadInput(documentBytes = document, documentFilename = uiState.cccdFilename ?: "cccd.jpg"),
            clientSession = app.sdk.sessionId,
        ) { result ->
            runOnUiThread {
                when (result) {
                    is FidesSdkResult.Failure -> {
                        uiState = uiState.copy(
                            loading = false,
                            errorMessage = formatApiError(result.message),
                            liveCheckStatus = "Xác minh thất bại.",
                        )
                    }
                    is FidesSdkResult.Success -> {
                        uiState = uiState.copy(
                            loading = false,
                            finalResponse = result.value,
                            overlay = AppOverlay.RESULT,
                            liveCheckStatus = "",
                        )
                    }
                }
            }
        }
    }

    private fun loadCccd(uri: Uri) {
        try {
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes == null || bytes.isEmpty()) {
                uiState = uiState.copy(errorMessage = "Ảnh CCCD trống.")
                return
            }
            cccdBytes = bytes
            val name = uri.lastPathSegment?.substringAfterLast('/') ?: "cccd.jpg"
            uiState = uiState.copy(cccdFilename = name, liveCheckStatus = "CCCD: $name")
        } catch (error: Throwable) {
            uiState = uiState.copy(errorMessage = error.message)
        }
    }

    private fun closeOverlay() {
        when (uiState.overlay) {
            AppOverlay.GROW -> closeGrowOverlay()
            AppOverlay.TRANSFER -> closeTransferOverlay()
            else -> resetShieldFlow()
        }
    }

    private fun closeGrowOverlay() {
        growRequestGeneration += 1
        growReceiptBytes = null
        uiState = uiState.copy(
            overlay = AppOverlay.NONE,
            loading = false,
            errorMessage = null,
            growStatusMessage = "",
            growReceiptFilename = null,
            growResponse = null,
        )
    }

    private fun closeTransferOverlay() {
        uiState = uiState.copy(
            overlay = AppOverlay.NONE,
            loading = false,
            errorMessage = null,
            transaction = null,
            analyzeResponse = null,
            finalResponse = null,
        )
    }

    private fun resetShieldFlow() {
        growRequestGeneration += 1
        cccdBytes = null
        growReceiptBytes = null
        captureResult = null
        liveCapture.release()
        liveCapture = LiveCheckCapture(this, this)
        previewView = PreviewView(this)
        uiState = uiState.copy(
            overlay = AppOverlay.NONE,
            loading = false,
            errorMessage = null,
            transaction = null,
            analyzeResponse = null,
            finalResponse = null,
            cccdFilename = null,
            cameraReady = false,
            liveCheckStatus = "",
            recordingSeconds = null,
            liveCheckReady = false,
            growStatusMessage = "",
            growReceiptFilename = null,
            growResponse = null,
        )
    }

    private fun ensurePermissions(onReady: () -> Unit) {
        val missing = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            onReady()
        } else {
            pendingAction = onReady
            permissionLauncher.launch(missing.toTypedArray())
        }
    }

    companion object {
        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_PHONE_STATE,
        )
    }
}
