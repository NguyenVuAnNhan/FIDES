package ai.fides.sdk.session

import android.os.Handler
import android.os.Looper
import ai.fides.sdk.FidesConsent
import ai.fides.sdk.FidesMobileSdk
import ai.fides.sdk.FidesSdkResult
import ai.fides.sdk.ShieldSessionHeartbeatResponse
import ai.fides.sdk.call.CallStateMonitor

/**
 * Sends periodic Shield session heartbeats from app entry so backend can score context early.
 */
class ShieldSessionMonitor(
    private val sdk: FidesMobileSdk,
    private val consent: FidesConsent,
    private val callMonitor: CallStateMonitor,
    private val intervalMs: Long = 15_000L,
) {
    private val handler = Handler(Looper.getMainLooper())
    private var running = false
    private var latestResponse: ShieldSessionHeartbeatResponse? = null
    private var listener: ((ShieldSessionHeartbeatResponse) -> Unit)? = null

    private val tickRunnable = object : Runnable {
        override fun run() {
            if (!running) return
            sdk.sendSessionHeartbeat(consent, callMonitor) { result ->
                if (result is FidesSdkResult.Success) {
                    latestResponse = result.value
                    listener?.invoke(result.value)
                }
                if (running) {
                    handler.postDelayed(this, intervalMs)
                }
            }
        }
    }

    fun start(onUpdate: ((ShieldSessionHeartbeatResponse) -> Unit)? = null) {
        if (onUpdate != null) {
            listener = onUpdate
            latestResponse?.let { onUpdate.invoke(it) }
        }
        if (running) return
        running = true
        handler.post(tickRunnable)
    }

    fun setListener(onUpdate: ((ShieldSessionHeartbeatResponse) -> Unit)?) {
        listener = onUpdate
        latestResponse?.let { response -> onUpdate?.invoke(response) }
    }

    fun stop() {
        running = false
        handler.removeCallbacks(tickRunnable)
    }

    fun latestResponse(): ShieldSessionHeartbeatResponse? = latestResponse
}
