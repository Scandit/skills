# Label Capture React Native — Validation Flow

The Validation Flow is the **recommended default UX** for Label Capture. Quoting the docs: *"An always-present checklist shows users exactly which fields have been captured and which are still missing, making the scanning process transparent and efficient."* The customer's app gets one final callback once every required field has been confirmed (scanned or manually entered) — no per-field reconciliation logic needed.

Use the basic overlay (or the advanced overlay) only when:
- You need a live AR overlay drawn on top of the camera (use `LabelCaptureAdvancedOverlay`), or
- You need a very custom UI that the Validation Flow's fixed layout cannot produce.

Validation Flow is designed to be **rendered full-screen**. Do not embed it inside a small widget, card, or partial-screen container — the layout assumes full-screen height for the field checklist, manual-entry sheet, and keyboard interaction.

> **Single label definition only.** The Validation Flow overlay only works with `LabelCaptureSettings` containing **exactly one** `LabelDefinition`. If the customer needs to capture multiple distinct label shapes, they cannot use the Validation Flow for both — use the basic / advanced overlay path, or run separate scan screens.

> **PriceCapture pre-made label is not VF-compatible.** `LabelDefinition.createPriceCaptureDefinition(name)` is **explicitly documented as incompatible with the Validation Flow** — using it inside VF "may result in incorrect data being captured." For price labels, either (a) build a custom definition out of `CustomBarcode` + `TotalPriceText`/`UnitPriceText`/`WeightText` to use with VF, or (b) keep the PriceCapture pre-made label but use the basic overlay path.

> **Standby behavior.** If no scan succeeds within 10 seconds the Validation Flow pauses ("Scanning paused to conserve battery") to save the device's battery — the user has to tap to resume. This is not configurable.

## Listener interface — all three methods are required (RN)

`LabelCaptureValidationFlowListener` on React Native is a **single interface with three required methods**. There is no base/Extended split on RN (that split exists only on Flutter). Even if you don't care about a method, you must provide an empty implementation — calling it on an undefined member throws at runtime.

```typescript
import type {
  LabelCaptureValidationFlowListener,
  LabelField,
  LabelResultUpdateType,
} from 'scandit-react-native-datacapture-label';
import type { FrameData } from 'scandit-react-native-datacapture-core';

const listener: LabelCaptureValidationFlowListener = {
  didCaptureLabelWithFields(fields: LabelField[]) {
    // Final result for one label — fires once all required fields are confirmed.
  },

  didSubmitManualInputForField(field: LabelField, oldValue: string | null, newValue: string) {
    // Fires every time the user types or corrects a field value.
    // Leave the body empty if you don't need it.
  },

  async didUpdateValidationFlowResult(
    type: LabelResultUpdateType,
    asyncId: number,
    fields: LabelField[],
    getFrameData: () => Promise<FrameData | null>,
  ): Promise<void> {
    // Fires multiple times during capture as fields accumulate.
    // Leave the body empty if you don't need progress feedback.
    // Call `await getFrameData()` here to retrieve the camera frame
    // that produced the partial result (useful for image upload / auditing).
  },
};
```

`LabelResultUpdateType` values: `AsyncStarted`, `AsyncFinished`, `Sync`.

## What's customizable, and what isn't

The Validation Flow exposes **text strings only**. No colors, fonts, layout, brushes, button shapes, sheet position, animation, or icons are customizable. If a customer needs visual changes, they must drop down to `LabelCaptureBasicOverlay` (brushes) or `LabelCaptureAdvancedOverlay` (fully custom views) — see `references/customization.md`.

```typescript
import { LabelCaptureValidationFlowSettings, LabelCaptureValidationFlowOverlay } from 'scandit-react-native-datacapture-label';

const settings = new LabelCaptureValidationFlowSettings();

// Hint shown when the camera is paused / no label detected.
settings.standbyHintText = 'No label detected';

// Hint while capturing — typically rendered as "X/Y fields collected".
settings.validationHintText = 'data fields collected';

// Error text shown when a value doesn't match the expected regex.
settings.validationErrorText = 'Incorrect format.';

// Button labels.
settings.finishButtonText = 'Finish';     // default: "Finish"
settings.restartButtonText = 'Clear All'; // default: "Clear All" (not "Restart")
settings.pauseButtonText = 'Pause';       // default: "Pause"

// Status texts during scanning.
settings.scanningText = 'Scan in progress';
settings.adaptiveScanningText = 'Processing';   // shown while ARE is processing

// Per-field placeholder text shown in the manual-entry input.
// Pass `null` to clear a previously-set placeholder.
settings.setPlaceholderTextForLabelDefinition('Expiry Date', 'MM/DD/YYYY');

// Android-only: let the overlay manage IME (keyboard) insets internally.
// Default is true on JS frameworks. Set to false if your app already manages insets.
overlay.shouldHandleKeyboardInsetsInternally = true;

overlay.applySettings(settings);
```

**Removing a button.** The docs state that the restart, pause, and finish buttons *"can be customized or removed entirely"*. To hide a button, set its text to an empty string (`settings.restartButtonText = '';`).

**Localization.** Text customization is the supported path for translating the Validation Flow UI. The Scandit docs show worked examples in English, Spanish, and French — assign the translated strings yourself and call `applySettings(settings)` whenever the user's locale changes.

**Deprecated properties** — accept assignments but log a warning and have no effect. Do not use:

- `missingFieldsHintText`
- `requiredFieldErrorText`
- `manualInputButtonText`

## When the customer asks "can we change X?"

| Question | Answer |
|---|---|
| Can we change a button label / hint text? | Yes — see the settings table above. |
| Can we change colors / theme? | No, not via Validation Flow. Use `LabelCaptureBasicOverlay` (brushes) or `LabelCaptureAdvancedOverlay` (custom views). |
| Can we change the layout / sheet position / list order? | No. The Validation Flow is fixed-layout by design. |
| Can we embed it in a non-full-screen widget? | Not recommended. The layout assumes full-screen height. |
| Can we react to manual edits? | Yes — implement `didSubmitManualInputForField`. |
| Can we get the camera frame that produced a result? | Yes — call `await getFrameData()` inside `didUpdateValidationFlowResult`. |
| Can we react to each partial capture before the final result? | Yes — `didUpdateValidationFlowResult` fires multiple times. |

## When to fall back to the basic overlay

If the user explicitly needs a live AR overlay rendered on the camera preview, or a UI radically different from the Validation Flow's checklist, switch to `LabelCaptureBasicOverlay` (with brushes for visual feedback) or `LabelCaptureAdvancedOverlay` (arbitrary views anchored to captured fields). See `references/customization.md` for both. Both options require you to build the validation/correction UX yourself — Validation Flow is the only path that ships that UX for you.
