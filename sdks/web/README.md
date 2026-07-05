# FIDES Web SDK

Browser SDK scaffold for FIDES Shield and Grow.

## Responsibilities

- Capture in-page behavioral events with consent.
- Derive SmartUX-style summary signals.
- Build normalized Shield request payloads.
- Call FIDES backend APIs.
- Avoid raw device inspection claims.
- Keep VNPT credentials and partner credentials server-side.

## Quick Start

```html
<script type="module">
  import { createFidesWebSdk } from "./src/index.js";

  const fides = createFidesWebSdk({
    baseUrl: "http://127.0.0.1:8000",
    consent: { telemetry: true }
  });

  const detach = fides.attachDefaultListeners(document);

  const result = await fides.analyzeShield({
    transaction_amount: 75000000,
    recipient_name: "Nguyen Van A",
    recipient_account: "9704 0000 1234",
    active_call: true,
    caller_type: "unknown",
    caller_number: "+882 13 456 789",
    recipient_known: false
  });

  console.log(result);

  if (result.action === "require_camera_voice_check") {
    const challengeResult = await fides.challengeShield({
      transaction_amount: 75000000,
      recipient_name: "Nguyen Van A",
      recipient_account: "9704 0000 1234",
      active_call: true,
      caller_type: "unknown",
      caller_number: "+882 13 456 789",
      recipient_known: false
    }, {
      ekyc_image_ref: "uploads/ekyc/selfie-example.jpg",
      stt_audio_ref: "uploads/smartvoice/challenge-example.wav"
    });

    console.log(challengeResult);
  }

  detach();
</script>
```

## Boundary

The web SDK can only observe behavior inside the page. It cannot reliably detect active phone calls, installed remote-control apps, or screen sharing outside the browser. Those signals must come from mobile SDKs, bank backend context, or explicit scenario mocks.
