# FIDES SDK Scaffold

## Purpose

FIDES needs two SDK surfaces for the MVP:

- Web SDK for browser banking flows.
- Mobile SDK for Android and iOS banking or wallet apps.

Both SDKs should send normalized FIDES payloads. They should not expose VNPT credentials, partner-bank credentials, raw biometric templates, or raw device identifiers.

## Web SDK

Location: `sdks/web`

The Web SDK can:

- record in-page events,
- derive SmartUX-style signals,
- build Shield payloads,
- call Shield and Grow APIs.

The Web SDK cannot reliably detect:

- active phone calls,
- caller numbers,
- installed remote-control apps,
- screen sharing outside the browser,
- native accessibility-service state.

Those signals must come from mobile apps, bank backend context, telco integration, or scenario mocks.

## Mobile SDK

Location: `sdks/mobile`

The Mobile SDK scaffold provides:

- Android Kotlin interfaces,
- iOS Swift interfaces,
- consent object,
- telemetry provider interface,
- HTTP transport interface,
- Shield payload builder,
- Shield/Grow API methods.

The host app remains responsible for platform permissions and raw telemetry collection.

## Common Payload Boundary

Both SDKs normalize telemetry into existing Shield fields:

- `native_telemetry_available`
- `native_telemetry_source`
- `installed_remote_access_app_detected`
- `accessibility_service_risk`
- `screen_sharing_detected`
- `smartux_behavior_anomaly_score`
- `smartux_remote_control_score`
- `smartux_signals`

Future provider integrations should add provider trace metadata as described in `docs/vnpt_schema_integration_plan.md`.

