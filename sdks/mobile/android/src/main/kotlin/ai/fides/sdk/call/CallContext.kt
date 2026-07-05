package ai.fides.sdk.call

import ai.fides.sdk.ShieldTransaction

data class CallContext(
    val activeCall: Boolean,
    val callerType: String = "unknown",
    val callerNumber: String = "",
) {
    companion object {
        val idle = CallContext(activeCall = false)
    }
}

interface CallStateMonitor {
    fun snapshot(): CallContext
}

fun ShieldTransaction.withCallContext(context: CallContext): ShieldTransaction =
    copy(
        activeCall = context.activeCall,
        callerType = context.callerType,
        callerNumber = context.callerNumber,
    )
