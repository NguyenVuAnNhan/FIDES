package ai.fides.sample

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import ai.fides.sample.databinding.ActivityShieldTransferBinding
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

class ShieldTransferActivity : AppCompatActivity() {
    private lateinit var binding: ActivityShieldTransferBinding
    private lateinit var sdk: FidesMobileSdk
    private lateinit var callMonitor: CallStateMonitor
    private lateinit var liveCapture: LiveCheckCapture

    private val consent = FidesConsent(telemetry = true)
    private var currentTransaction: ShieldTransaction? = null
    private var cccdBytes: ByteArray? = null
    private var cccdFilename: String = "cccd.jpg"
    private var captureResult: LiveCheckCaptureResult? = null
    private var identityCheckRequired = false
    private var cameraBound = false

    private enum class FlowStep {
        CONFIRM,
        VERIFY,
        DONE,
    }

    private var flowStep = FlowStep.CONFIRM

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val allGranted = REQUIRED_PERMISSIONS.all { grants[it] == true }
        if (allGranted) {
            onPermissionsReady()
        } else {
            setStatus("Permissions denied. Grant camera, microphone, and phone state to continue.")
        }
    }

    private val cccdPicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri == null) {
            setStatus("CCCD portrait not selected.")
            return@registerForActivityResult
        }
        loadCccd(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityShieldTransferBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)

        sdk = FidesMobileSdk(
            config = FidesConfig(baseUrl = BuildConfig.FIDES_BASE_URL),
            telemetryProvider = DefaultFidesTelemetryProvider(),
            transport = OkHttpFidesTransport(),
        )
        callMonitor = DemoCallStateMonitor(AndroidCallStateMonitor(applicationContext))
        liveCapture = LiveCheckCapture(this, this)

        binding.buttonPrimary.setOnClickListener { onPrimaryAction() }
        binding.buttonPickCccd.setOnClickListener { cccdPicker.launch("image/*") }
        binding.buttonEnableCamera.setOnClickListener { bindCameraPreview() }
        binding.buttonStartLiveCheck.setOnClickListener { startLiveCheck() }

        refreshCallSignal()
        resetFlow()
    }

    override fun onDestroy() {
        liveCapture.release()
        super.onDestroy()
    }

    private fun onPrimaryAction() {
        when (flowStep) {
            FlowStep.CONFIRM -> confirmTransfer()
            FlowStep.VERIFY -> verifyIdentity()
            FlowStep.DONE -> resetFlow()
        }
    }

    private fun confirmTransfer() {
        val transaction = readTransaction()
        currentTransaction = transaction
        setStatus("Checking transfer context...")
        binding.buttonPrimary.isEnabled = false

        ensurePermissions {
            sdk.analyzeShieldWithCall(transaction, consent, callMonitor) { result ->
                runOnUiThread {
                    binding.buttonPrimary.isEnabled = true
                    when (result) {
                        is FidesSdkResult.Failure -> {
                            setStatus("Analyze failed: ${result.message}")
                        }
                        is FidesSdkResult.Success -> {
                            val response = result.value
                            binding.analyzeResultText.visibility = View.VISIBLE
                            binding.analyzeResultText.text = buildString {
                                append("Risk ${response.riskScore}/100 · ${response.action}\n")
                                append(response.interventionMessage)
                            }

                            if (response.requiresIdentityCheck) {
                                identityCheckRequired = true
                                flowStep = FlowStep.VERIFY
                                binding.buttonPrimary.text = getString(R.string.verify_continue)
                                binding.identityCard.visibility = View.VISIBLE
                                setStatus("Extra verification required. Pick CCCD, enable camera, then record.")
                                ensurePermissions { bindCameraPreview() }
                            } else {
                                flowStep = FlowStep.DONE
                                binding.buttonPrimary.text = getString(R.string.new_transfer)
                                setStatus("Transfer cleared without identity check.")
                            }
                        }
                    }
                }
            }
        }
    }

    private fun verifyIdentity() {
        val transaction = currentTransaction ?: return
        val capture = captureResult
        val document = cccdBytes

        if (document == null) {
            setStatus("Pick a CCCD portrait before verifying.")
            return
        }
        if (capture == null) {
            setStatus("Complete the 10-second live check first.")
            return
        }

        setStatus("Uploading live check and running identity verification...")
        binding.buttonPrimary.isEnabled = false

        val uploadInput = capture.toUploadInput(
            documentBytes = document,
            documentFilename = cccdFilename,
        )

        sdk.runIdentityCheck(transaction, consent, uploadInput) { result ->
            runOnUiThread {
                binding.buttonPrimary.isEnabled = true
                when (result) {
                    is FidesSdkResult.Failure -> {
                        setStatus("Identity check failed: ${result.message}")
                    }
                    is FidesSdkResult.Success -> {
                        val response = result.value
                        binding.finalResultText.visibility = View.VISIBLE
                        binding.finalResultText.text = buildString {
                            append("Final decision: ${response.action}\n")
                            append("Risk ${response.riskScore}/100 · ${response.riskLevel}\n")
                            append(response.interventionMessage)
                            response.challengeProfile?.let { append("\nProfile: $it") }
                        }
                        flowStep = FlowStep.DONE
                        binding.buttonPrimary.text = getString(R.string.new_transfer)
                        setStatus("Identity check complete.")
                    }
                }
            }
        }
    }

    private fun bindCameraPreview() {
        if (cameraBound) {
            return
        }
        liveCapture.bindPreview(
            previewView = binding.cameraPreview,
            onReady = {
                runOnUiThread {
                    cameraBound = true
                    binding.buttonEnableCamera.isEnabled = false
                    binding.buttonEnableCamera.text = "Camera ready"
                    updateLiveCheckButtonState()
                    setStatus("Camera ready. Pick CCCD if needed, then start live check.")
                }
            },
            onError = { message ->
                runOnUiThread {
                    setStatus("Camera error: $message")
                }
            },
        )
    }

    private fun startLiveCheck() {
        binding.buttonStartLiveCheck.isEnabled = false
        captureResult = null
        setStatus("Recording live check...")

        liveCapture.startRecording(
            callback = object : LiveCheckCaptureCallback {
                override fun onTick(secondsRemaining: Int) {
                    runOnUiThread {
                        binding.liveCheckStatusText.text = "Recording… ${secondsRemaining}s remaining"
                    }
                }

                override fun onSuccess(result: LiveCheckCaptureResult) {
                    runOnUiThread {
                        captureResult = result
                        binding.liveCheckStatusText.text =
                            "Captured ${result.frames.size} frame(s). Tap Verify & continue."
                        binding.buttonStartLiveCheck.isEnabled = true
                        setStatus("Live check ready.")
                    }
                }

                override fun onFailure(message: String, cause: Throwable?) {
                    runOnUiThread {
                        binding.buttonStartLiveCheck.isEnabled = true
                        binding.liveCheckStatusText.text = message
                        setStatus("Live check failed: $message")
                    }
                }
            },
        )
    }

    private fun loadCccd(uri: Uri) {
        try {
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes == null || bytes.isEmpty()) {
                setStatus("Selected CCCD image is empty.")
                return
            }
            cccdBytes = bytes
            cccdFilename = uri.lastPathSegment?.substringAfterLast('/') ?: "cccd.jpg"
            binding.liveCheckStatusText.text = "CCCD selected: $cccdFilename"
            updateLiveCheckButtonState()
        } catch (error: Throwable) {
            setStatus("Could not read CCCD image: ${error.message}")
        }
    }

    private fun updateLiveCheckButtonState() {
        binding.buttonStartLiveCheck.isEnabled = cameraBound && cccdBytes != null
    }

    private fun readTransaction(): ShieldTransaction =
        ShieldTransaction(
            amount = binding.inputAmount.text?.toString()?.toLongOrNull() ?: 0L,
            recipientName = binding.inputRecipient.text?.toString().orEmpty(),
            recipientAccount = binding.inputAccount.text?.toString().orEmpty(),
            recipientKnown = false,
        )

    private fun refreshCallSignal() {
        val call = callMonitor.snapshot()
        binding.callSignalText.text = if (call.activeCall) {
            "Background signal: active call detected (${call.callerType}, ${call.callerNumber.ifBlank { "number hidden" }})"
        } else {
            "Background signal: no active call detected on this device."
        }
    }

    private fun ensurePermissions(onReady: () -> Unit) {
        val missing = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            onReady()
        } else {
            pendingPermissionAction = onReady
            permissionLauncher.launch(missing.toTypedArray())
        }
    }

    private var pendingPermissionAction: (() -> Unit)? = null

    private fun onPermissionsReady() {
        refreshCallSignal()
        pendingPermissionAction?.invoke()
        pendingPermissionAction = null
    }

    private fun resetFlow() {
        flowStep = FlowStep.CONFIRM
        identityCheckRequired = false
        currentTransaction = null
        cccdBytes = null
        captureResult = null
        cameraBound = false

        binding.analyzeResultText.visibility = View.GONE
        binding.finalResultText.visibility = View.GONE
        binding.identityCard.visibility = View.GONE
        binding.buttonPrimary.text = getString(R.string.confirm_transfer)
        binding.buttonEnableCamera.isEnabled = true
        binding.buttonEnableCamera.text = getString(R.string.enable_camera)
        binding.buttonStartLiveCheck.isEnabled = false
        binding.liveCheckStatusText.text = ""
        binding.inputAmount.setText("65000000")
        binding.inputRecipient.setText("Tran Van B")
        binding.inputAccount.setText("9704 2222 8800")

        liveCapture.release()
        liveCapture = LiveCheckCapture(this, this)

        refreshCallSignal()
        setStatus(getString(R.string.status_idle))
    }

    private fun setStatus(message: String) {
        binding.statusText.text = message
    }

    companion object {
        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_PHONE_STATE,
        )
    }
}

/**
 * Uses real telephony when available; otherwise applies demo Path B call context so the
 * emulator can trigger identity check without an actual phone call.
 */
private class DemoCallStateMonitor(
    private val platformMonitor: AndroidCallStateMonitor,
) : CallStateMonitor {
    override fun snapshot(): CallContext {
        val live = platformMonitor.snapshot()
        if (live.activeCall) {
            return live
        }
        return CallContext(
            activeCall = true,
            callerType = "unknown",
            callerNumber = "+84 909 000 555",
        )
    }
}
