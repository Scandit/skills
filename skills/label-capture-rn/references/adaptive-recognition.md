# Label Capture React Native — Adaptive Recognition Engine (Cloud Fallback)

> **The Adaptive Recognition Engine is in beta** and may change in future SDK versions. To enable it on a customer's subscription, **contact `support@scandit.com`**. There is no client-side license-key flag — access is granted server-side per Scandit subscription.

The **Adaptive Recognition Engine (ARE)** — also referred to as the **Cloud Fallback** by some developers — is a cloud-based fallback for Label Capture's on-device model. When the on-device model fails to capture a field on a particular frame, the SDK automatically forwards the frame to the cloud model and merges the result back into the capture session. The customer-facing wording from the docs: *"helps making Smart Label Capture more robust and scalable thanks to its larger, more capable model hosted in the cloud. Whenever Smart Label Capture's on-device model fails, the SDK will automatically trigger the Adaptive Recognition Engine."*

ARE has **two distinct activation paths** — pick one based on the use case.

## Path 1 — Inline ARE on any label definition (most common)

Set the mode on the `LabelDefinition`. Works with custom definitions, pre-made fields, and pre-made labels (except where noted in `references/validation-flow.md`). Available 8.3+ on RN.

```typescript
import {
  AdaptiveRecognitionMode,
  LabelDefinition,
} from 'scandit-react-native-datacapture-label';

const label = new LabelDefinition('Perishable Product');
label.fields = [/* …your fields… */];
label.adaptiveRecognitionMode = AdaptiveRecognitionMode.Auto;
```

`AdaptiveRecognitionMode` values:

| Value | Behavior |
|---|---|
| `Off` (default) | On-device only — no cloud calls. |
| `Auto` | System chooses the best mix of on-device and cloud based on conditions. **Use this as the default.** |
| `On` (8.4+) | Prioritizes on-device but uses cloud whenever possible, even in cases `Auto` would skip. Costs more cloud calls. |

While ARE is processing inside the Validation Flow, the placeholder shown in the manual-entry field is `LabelCaptureValidationFlowSettings.adaptiveScanningText` ("Processing, tap to type manually" by default) — see `references/validation-flow.md`.

## Path 2 — Standalone receipt scanning (different product)

`LabelCaptureAdaptiveRecognitionOverlay` is a **separate overlay** for end-to-end receipt scanning — the customer points the camera at a full receipt, the cloud returns a structured `ReceiptScanningResult` (store name/address, date, line items, tax, total). This is its own UX and is **not** the same as turning on `adaptiveRecognitionMode` for a normal label.

Today only `AdaptiveRecognitionResultType.Receipt` is supported (8.2+ on RN).

```typescript
import {
  AdaptiveRecognitionResultType,
  LabelCaptureAdaptiveRecognitionOverlay,
  LabelCaptureAdaptiveRecognitionSettings,
  type LabelCaptureAdaptiveRecognitionListener,
  type ReceiptScanningResult,
} from 'scandit-react-native-datacapture-label';

const settings = new LabelCaptureAdaptiveRecognitionSettings(AdaptiveRecognitionResultType.Receipt);
settings.processingHintText = 'Reading receipt…';

const overlay = new LabelCaptureAdaptiveRecognitionOverlay(labelCapture);
const listener: LabelCaptureAdaptiveRecognitionListener = {
  didRecognize(result) {
    const receipt = result as ReceiptScanningResult;
    // receipt.storeName, receipt.storeAddress, receipt.date,
    // receipt.lineItems, receipt.paymentTotal, receipt.paymentTax, …
  },
  didFail() {
    // Cloud call failed or no receipt was recognized.
  },
};
overlay.listener = listener;

await overlay.applySettings(settings);
view.addOverlay(overlay);
```

Use Path 2 only when the customer's goal is **receipts specifically**. For general "scan this label, improve accuracy with the cloud", use Path 1.

## Decision tree

- Customer wants ARE to back up a normal Label Capture flow → **Path 1**.
- Customer wants to scan a full receipt and get itemized line items → **Path 2**.
- Customer is in trial / proof-of-concept → either path works without extra config beyond an active SDK license.
- Customer is going to production → **contact `support@scandit.com`** to enable ARE on the subscription. The skill should not promise production access without this step.

## What to surface to the customer

Always include these three things when proposing ARE:
1. It's a **beta API** and may change between SDK versions.
2. Production use requires Scandit Support to enable it on the subscription (`support@scandit.com`).
3. Cloud calls are billed differently from on-device captures — confirm with the account manager before shipping `On`.
