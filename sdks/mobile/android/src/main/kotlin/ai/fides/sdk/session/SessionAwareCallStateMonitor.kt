package ai.fides.sdk.session

import ai.fides.sdk.call.CallContext
import ai.fides.sdk.call.CallStateMonitor

/**
 * Tracks call context accumulated since app/session start, not only at transfer confirm.
 */
class SessionAwareCallStateMonitor(
    private val delegate: CallStateMonitor,
) : CallStateMonitor {
    @Volatile
    private var callActiveDuringSession: Boolean = false

    @Volatile
    private var peakContext: CallContext = CallContext.idle

    override fun snapshot(): CallContext {
        val current = delegate.snapshot()
        if (current.activeCall) {
            callActiveDuringSession = true
            peakContext = current
            return current
        }
        if (callActiveDuringSession) {
            return peakContext.copy(activeCall = true)
        }
        return CallContext.idle
    }

    fun callActiveDuringSession(): Boolean = callActiveDuringSession || delegate.snapshot().activeCall

    fun refresh(): CallContext = snapshot()
}
