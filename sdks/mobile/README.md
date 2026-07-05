# FIDES Mobile SDK

Native mobile SDK scaffold for Android and iOS banking or wallet apps.

## Responsibilities

- Accept consent state from the host app.
- Ask the host app for native telemetry through a provider interface.
- Normalize telemetry into FIDES Shield fields.
- Call FIDES backend APIs through an injected HTTP transport.
- Keep platform permissions and raw device collection under the host app's control.

## Included Stubs

- `android/src/main/kotlin/ai/fides/sdk/FidesMobileSdk.kt`
- `ios/Sources/FidesMobileSDK/FidesMobileSDK.swift`

The stubs avoid hard dependencies on a specific networking library. The host app injects an HTTP transport and a telemetry provider.

## Platform Boundary

Android can provide more telemetry when permissions and OS policy allow it. iOS is more restricted. Both platforms should send derived risk signals, not raw biometric templates or long-lived device identifiers.

