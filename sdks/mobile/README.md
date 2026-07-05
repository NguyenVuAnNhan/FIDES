# FIDES Mobile SDK

Native mobile SDK for Android and iOS banking or wallet apps.

## Responsibilities

- Accept consent state from the host app.
- Collect derived telemetry and call context through provider interfaces.
- Build normalized Path B Shield payloads (`ShieldPayloadBuilder`).
- Capture live identity checks (`LiveCheckCapture` on Android).
- Upload live-check media and run `/api/shield/challenge`.
- Call FIDES backend APIs through an injected HTTP transport.

VNPT credentials stay on the FIDES backend — never embed them in the mobile SDK.

## Android modules

| Module | Package | Role |
| --- | --- | --- |
| Core | `ai.fides.sdk` | Payload builder, HTTP client, analyze/challenge |
| Call | `ai.fides.sdk.call` | `AndroidCallStateMonitor`, `CallContext` |
| Capture | `ai.fides.sdk.capture` | CameraX live check + frame sampling |

## Permissions (Android host app)

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
```

Request at runtime before transfer analysis / identity check.

## End-to-end (Android)

```kotlin
val sdk = FidesMobileSdk(
    config = FidesConfig(baseUrl = "https://fides.bank.internal"),
    telemetryProvider = DefaultFidesTelemetryProvider(),
    transport = OkHttpFidesTransport { "Bearer $bankJwt" },
)
val callMonitor = AndroidCallStateMonitor(context)

val transaction = ShieldTransaction(
    amount = 65_000_000,
    recipientName = "Tran Van B",
    recipientAccount = "9704 2222 8800",
    recipientKnown = false,
)
val consent = FidesConsent(telemetry = true)

// Step 1 — confirm transfer (call state attached automatically)
sdk.analyzeShieldWithCall(transaction, consent, callMonitor) { result ->
    when (result) {
        is FidesSdkResult.Success -> {
            if (result.value.requiresIdentityCheck) {
                // open identity check screen
            }
        }
        is FidesSdkResult.Failure -> { /* ... */ }
    }
}

// Step 2 — live camera check
val capture = LiveCheckCapture(context, lifecycleOwner)
capture.bindPreview(previewView, onReady = { /* enable record button */ }, onError = { /* ... */ })

capture.startRecording(object : LiveCheckCaptureCallback {
    override fun onTick(secondsRemaining: Int) { /* update UI */ }

    override fun onSuccess(result: LiveCheckCaptureResult) {
        val uploadInput = result.toUploadInput(
            documentBytes = cccdBytes,
            documentFilename = "cccd.jpg",
        )
        sdk.runIdentityCheck(transaction, consent, uploadInput) { decision ->
            // allow / withhold from decision.value.action
        }
    }

    override fun onFailure(message: String, cause: Throwable?) { /* ... */ }
})
```

## VoIP / in-app softphone override

When the bank app knows call metadata that Android telephony cannot expose:

```kotlin
val callMonitor = CompositeCallStateMonitor(
    platformMonitor = AndroidCallStateMonitor(context),
    hostOverride = {
        if (softPhone.isInCall()) {
            CallContext(
                activeCall = true,
                callerType = "voip",
                callerNumber = softPhone.remoteNumber(),
            )
        } else {
            null
        }
    },
)
```

## iOS (Phase 2 partial)

- `IosCallStateMonitor` — CallKit active call detection (no caller number)
- `LiveCheckCapture.extractJpegFrames(fromVideoAt:)` — frame sampling helper
- Full AVCaptureSession recorder — host app or next iteration

## Dependencies (Android)

- OkHttp 4.x
- CameraX 1.3.x
- AndroidX Lifecycle

## One-time machine setup (macOS + Homebrew)

Already run on this machine:

```bash
brew install --cask android-commandlinetools android-platform-tools
source sdks/mobile/env.sh   # or open a new terminal (added to ~/.zshrc)
./sdks/mobile/setup_android.sh
```

Creates `sdks/mobile/local.properties`, installs SDK 35 + build-tools, builds the debug APK.

### Emulator (optional)

```bash
source sdks/mobile/env.sh
echo no | avdmanager create avd -n fides_demo -k "system-images;android-35;google_apis;arm64-v8a" -d pixel_6
emulator -avd fides_demo -gpu host &
adb install -r sdks/mobile/sample-banking-app/build/outputs/apk/debug/sample-banking-app-debug.apk
```

## Sample banking app

Path B end-to-end demo with `PreviewView`, permissions, CCCD picker, and live check.

```bash
cd sdks/mobile
./gradlew :sample-banking-app:assembleDebug
./gradlew :sample-banking-app:installDebug   # device/emulator connected
```

1. Start FIDES backend on the host: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
2. Emulator uses `http://10.0.2.2:8000` (configured in `BuildConfig.FIDES_BASE_URL`).
3. Physical device: change `FIDES_BASE_URL` in `sample-banking-app/build.gradle.kts` to your LAN IP.
4. Open **FIDES Sample Bank** → Confirm transfer → identity check when risk is high.

The sample uses [DemoCallStateMonitor](sample-banking-app/src/main/kotlin/ai/fides/sample/ShieldTransferActivity.kt) to simulate an active call on emulators without telephony.

## Next

- Parallel audio-only track for higher STT quality (optional)
- Prebuilt reusable `ShieldIdentityCheckFragment` extracted from the sample app
