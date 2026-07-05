package ai.fides.sdk.call

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioManager
import android.os.Build
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat

/**
 * Best-effort call detection for Shield stage-1 scoring.
 *
 * Requires [Manifest.permission.READ_PHONE_STATE] for reliable telephony call state.
 * Caller number is often unavailable on modern Android; the host app may override via
 * [CallStateMonitor] if it has carrier or in-app VoIP metadata.
 */
class AndroidCallStateMonitor(
    private val context: Context,
) : CallStateMonitor {
    override fun snapshot(): CallContext {
        if (!hasPhoneStatePermission()) {
            return CallContext(
                activeCall = isAudioCallActive(),
                callerType = "unknown",
                callerNumber = "",
            )
        }

        val telephony = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        val onTelephonyCall = telephony.callState != TelephonyManager.CALL_STATE_IDLE
        val activeCall = onTelephonyCall || isAudioCallActive()

        if (!activeCall) {
            return CallContext.idle
        }

        return CallContext(
            activeCall = true,
            callerType = inferCallerType(telephony),
            callerNumber = readCallerNumber(telephony),
        )
    }

    private fun hasPhoneStatePermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE) ==
            PackageManager.PERMISSION_GRANTED

    private fun isAudioCallActive(): Boolean {
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return when (audioManager.mode) {
            AudioManager.MODE_IN_CALL,
            AudioManager.MODE_IN_COMMUNICATION,
            -> true
            else -> false
        }
    }

    private fun inferCallerType(telephony: TelephonyManager): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            when (telephony.callState) {
                TelephonyManager.CALL_STATE_RINGING,
                TelephonyManager.CALL_STATE_OFFHOOK,
                -> return "unknown"
            }
        }
        return "unknown"
    }

    private fun readCallerNumber(telephony: TelephonyManager): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            runCatching {
                val number = telephony.line1Number?.trim().orEmpty()
                if (number.isNotEmpty()) {
                    return number
                }
            }
        }
        return ""
    }
}

/**
 * Host app can merge bank-side VoIP metadata (Zalo, in-app softphone, etc.).
 */
class CompositeCallStateMonitor(
    private val platformMonitor: CallStateMonitor,
    private val hostOverride: () -> CallContext?,
) : CallStateMonitor {
    override fun snapshot(): CallContext {
        val override = hostOverride()
        if (override != null) {
            return override
        }
        return platformMonitor.snapshot()
    }
}
