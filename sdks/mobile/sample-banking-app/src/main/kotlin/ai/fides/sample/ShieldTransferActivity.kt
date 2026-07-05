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
import ai.fides.sdk.DefaultFidesTelemetryProvider
import ai.fides.sdk.FidesConfig
import ai.fides.sdk.FidesConsent
import ai.fides.sdk.FidesMobileSdk
import ai.fides.sdk.FidesSdkResult
import ai.fides.sdk.OkHttpFidesTransport
import ai.fides.sdk.ShieldTransaction
import ai.fides.sdk.call.AndroidCallStateMonitor
import ai.fides.sdk.call.CallContext
import ai.fides.sdk.call.CallStateMonitor
import ai.fides.sdk.capture.LiveCheckCapture
import ai.fides.sdk.capture.LiveCheckCaptureCallback
import ai.fides.sdk.capture.LiveCheckCaptureResult
import ai.fides.sdk.capture.toUploadInput
import ai.fides.sample.ui.FidesApp
import ai.fides.sample.ui.theme.FidesTheme

class ShieldTransferActivity : ComponentActivity() {
    private lateinit var sdk: FidesMobileSdk
    private lateinit var callMonitor: CallStateMonitor
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

    private var pendingAction: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sdk = FidesMobileSdk(
            config = FidesConfig(baseUrl = BuildConfig.FIDES_BASE_URL),
            telemetryProvider = DefaultFidesTelemetryProvider(),
            transport = OkHttpFidesTransport(),
        )
        callMonitor = DemoCallStateMonitor(AndroidCallStateMonitor(applicationContext))
        liveCapture = LiveCheckCapture(this, this)
        previewView = PreviewView(this)

        setContent {
            FidesTheme {
                FidesApp(
                    state = uiState,
                    onNavigate = { tab -> uiState = uiState.copy(tab = tab, overlay = AppOverlay.NONE) },
                    onCheckTransaction = { openTransfer() },
                    onConfirmTransfer = { confirmTransfer(it) },
                    onWarningBack = { resetFlow() },
                    onWarningContinue = {
                        uiState = uiState.copy(overlay = AppOverlay.VOICE)
                        ensurePermissions { bindCamera() }
                    },
                    onCloseOverlay = { resetFlow() },
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

    private fun confirmTransfer(transaction: ShieldTransaction) {
        uiState = uiState.copy(loading = true, errorMessage = null, transaction = transaction)
        ensurePermissions {
            sdk.analyzeShieldWithCall(transaction, consent, callMonitor) { result ->
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
        val transaction = uiState.transaction ?: return
        val document = cccdBytes ?: return
        val capture = captureResult ?: return

        uiState = uiState.copy(loading = true)
        sdk.runIdentityCheck(
            transaction,
            consent,
            capture.toUploadInput(documentBytes = document, documentFilename = uiState.cccdFilename ?: "cccd.jpg"),
        ) { result ->
            runOnUiThread {
                when (result) {
                    is FidesSdkResult.Failure -> {
                        uiState = uiState.copy(loading = false, errorMessage = result.message)
                    }
                    is FidesSdkResult.Success -> {
                        uiState = uiState.copy(
                            loading = false,
                            finalResponse = result.value,
                            overlay = AppOverlay.RESULT,
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

    private fun resetFlow() {
        cccdBytes = null
        captureResult = null
        liveCapture.release()
        liveCapture = LiveCheckCapture(this, this)
        previewView = PreviewView(this)
        uiState = ShieldUiState()
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

private class DemoCallStateMonitor(
    private val platformMonitor: AndroidCallStateMonitor,
) : CallStateMonitor {
    override fun snapshot(): CallContext {
        val live = platformMonitor.snapshot()
        if (live.activeCall) return live
        return CallContext(activeCall = true, callerType = "unknown", callerNumber = "+84 909 000 555")
    }
}
