package ai.fides.sample

import android.app.Application
import ai.fides.sdk.DefaultFidesTelemetryProvider
import ai.fides.sdk.FidesConfig
import ai.fides.sdk.FidesConsent
import ai.fides.sdk.FidesMobileSdk
import ai.fides.sdk.OkHttpFidesTransport
import ai.fides.sdk.call.AndroidCallStateMonitor
import ai.fides.sdk.call.CallContext
import ai.fides.sdk.call.CallStateMonitor
import ai.fides.sdk.session.SessionAwareCallStateMonitor
import ai.fides.sdk.session.ShieldSessionMonitor

class FidesSampleApplication : Application() {
    lateinit var sdk: FidesMobileSdk
        private set
    lateinit var callMonitor: SessionAwareCallStateMonitor
        private set
    lateinit var sessionMonitor: ShieldSessionMonitor
        private set

    val sessionConsent = FidesConsent(telemetry = true)

    override fun onCreate() {
        super.onCreate()
        instance = this

        sdk = FidesMobileSdk(
            config = FidesConfig(baseUrl = BuildConfig.FIDES_BASE_URL),
            telemetryProvider = DefaultFidesTelemetryProvider(),
            transport = OkHttpFidesTransport(),
        )
        callMonitor = SessionAwareCallStateMonitor(
            DemoCallStateMonitor(AndroidCallStateMonitor(applicationContext)),
        )
        sessionMonitor = ShieldSessionMonitor(
            sdk = sdk,
            consent = sessionConsent,
            callMonitor = callMonitor,
        )
        sessionMonitor.start()
    }

    companion object {
        lateinit var instance: FidesSampleApplication
            private set
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
