# Label Capture Flutter — Validation Flow

The Validation Flow is the **recommended default UX** for Label Capture. Quoting the docs: *"An always-present checklist shows users exactly which fields have been captured and which are still missing, making the scanning process transparent and efficient."* The customer's app gets one final callback once every required field has been confirmed (scanned or manually entered) — no per-field reconciliation logic needed.

Use the basic overlay (or the advanced overlay) only when:
- You need a live AR overlay drawn on top of the camera (use `LabelCaptureAdvancedOverlay`), or
- You need a very custom UI that the Validation Flow's fixed layout cannot produce.

Validation Flow is designed to be **rendered full-screen**. Do not embed it inside a small widget, card, or partial-screen container — the layout assumes full-screen height for the field checklist, manual-entry sheet, and keyboard interaction.

> **Single label definition only.** The Validation Flow overlay only works with `LabelCaptureSettings` containing **exactly one** `LabelDefinition`. If the customer needs to capture multiple distinct label shapes, they cannot use the Validation Flow for both — use the basic / advanced overlay path, or run separate scan screens.

> **PriceCapture pre-made label is not VF-compatible.** `LabelDefinition.priceCaptureDefinitionWithName(name)` is **explicitly documented as incompatible with the Validation Flow** — using it inside VF "may result in incorrect data being captured." For price labels, either (a) build a custom definition out of `CustomBarcode` + `TotalPriceText`/`UnitPriceText`/`WeightText` to use with VF, or (b) keep the PriceCapture pre-made label but use the basic overlay path.

> **Standby behavior.** If no scan succeeds within 10 seconds the Validation Flow pauses ("Scanning paused to conserve battery") to save the device's battery — the user has to tap to resume. This is not configurable.

## Listener interfaces — base vs Extended (Flutter-specific)

Flutter is the only framework where the Validation Flow listener is split in two:

- `LabelCaptureValidationFlowListener` — base abstract class. Declares only `didCaptureLabelWithFields(fields)`. Implement this if all you need is the final result.
- `LabelCaptureValidationFlowExtendedListener` — extends the base. Adds:
  - `didSubmitManualInputForField(field, oldValue, newValue)` (8.2+)
  - `didUpdateValidationFlowResult(type, asyncId, fields, getFrameData)` (8.4+) — async, returns `Future<void>`

The Dart compiler enforces this: if you `implements LabelCaptureValidationFlowExtendedListener`, you must implement both new methods. Use empty bodies if you don't need them.

> RN / Capacitor / Cordova have a single 3-method interface with no Extended variant. Do not copy that pattern into Flutter code, and vice-versa.

```dart
class _ScanScreenState extends State<ScanScreen>
    implements LabelCaptureValidationFlowExtendedListener {
  @override
  void didCaptureLabelWithFields(List<LabelField> fields) {
    // Final result for one label — fires once all required fields are confirmed.
  }

  @override
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue) {
    // Fires whenever the user manually enters or corrects a field value.
  }

  @override
  Future<void> didUpdateValidationFlowResult(
    LabelResultUpdateType type,
    int asyncId,
    List<LabelField> fields,
    Future<FrameData?> Function() getFrameData,
  ) async {
    // Fires multiple times during capture as fields accumulate.
    // Call `await getFrameData()` here to retrieve the camera frame
    // that produced the partial result (useful for image upload / auditing).
  }
}
```

`LabelResultUpdateType` values: `AsyncStarted`, `AsyncFinished`, `Sync`.

## What's customizable, and what isn't

The Validation Flow exposes **text strings only**. No colors, fonts, layout, brushes, button shapes, sheet position, animation, or icons are customizable. If a customer needs visual changes, they must drop down to `LabelCaptureBasicOverlay` (brushes) or `LabelCaptureAdvancedOverlay` (fully custom widgets) — see `references/customization.md`.

```dart
final settings = LabelCaptureValidationFlowSettings.create();

settings.standbyHintText = 'No label detected';
settings.validationHintText = 'data fields collected';  // rendered as "X/Y fields collected"
settings.validationErrorText = 'Incorrect format.';

settings.finishButtonText = 'Finish';       // default: "Finish"
settings.restartButtonText = 'Clear All';   // default: "Clear All" (not "Restart")
settings.pauseButtonText = 'Pause';         // default: "Pause"

settings.scanningText = 'Scan in progress';
settings.adaptiveScanningText = 'Processing';   // shown while ARE is processing

// Per-field placeholder text shown in the manual-entry input.
// Pass `null` to clear a previously-set placeholder.
settings.setPlaceholderTextForLabelDefinition('Expiry Date', 'MM/DD/YYYY');

// Android-only: let the overlay manage IME (keyboard) insets internally.
// Default is true on Flutter. Set to false if your app already manages insets.
overlay.shouldHandleKeyboardInsetsInternally = true;

await overlay.applySettings(settings);
```

**Removing a button.** The docs state that the restart, pause, and finish buttons *"can be customized or removed entirely"*. To hide a button, set its text to an empty string (`settings.restartButtonText = '';`).

**Localization.** Text customization is the supported path for translating the Validation Flow UI. The Scandit docs show worked examples in English, Spanish, and French — assign the translated strings yourself and call `overlay.applySettings(settings)` whenever the user's locale changes.

**Deprecated properties** — marked `@Deprecated` in Dart. Do not use:

- `missingFieldsHintText`
- `requiredFieldErrorText`
- `manualInputButtonText` ("no longer used")

## When the customer asks "can we change X?"

| Question | Answer |
|---|---|
| Can we change a button label / hint text? | Yes — see the settings table above. |
| Can we change colors / theme? | No, not via Validation Flow. Use `LabelCaptureBasicOverlay` (brushes) or `LabelCaptureAdvancedOverlay` (custom widgets). |
| Can we change the layout / sheet position / list order? | No. The Validation Flow is fixed-layout by design. |
| Can we embed it in a non-full-screen widget? | Not recommended. The layout assumes full-screen height. |
| Can we react to manual edits? | Yes — implement `LabelCaptureValidationFlowExtendedListener` and override `didSubmitManualInputForField`. |
| Can we get the camera frame that produced a result? | Yes — call `await getFrameData()` inside `didUpdateValidationFlowResult`. |
| Can we react to each partial capture before the final result? | Yes — `didUpdateValidationFlowResult` fires multiple times. |

## When to fall back to the basic / advanced overlay

If the user explicitly needs a live AR overlay rendered on the camera preview, or a UI radically different from the Validation Flow's checklist, switch to `LabelCaptureBasicOverlay` (with brushes for visual feedback) or `LabelCaptureAdvancedOverlay` (arbitrary widgets anchored to captured fields). See `references/customization.md` for both. Both options require you to build the validation/correction UX yourself — Validation Flow is the only path that ships that UX for you.
