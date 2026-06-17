# Label Capture iOS — Validation Flow

The Validation Flow gives users a guided scanning experience: a persistent checklist shows which fields have been captured and which are still missing, and users can manually type a value when OCR fails. It handles partial captures across multiple package surfaces and confirms the result before returning it to the app. Reach for it when the user explicitly wants manual-entry fallback, a confirmation step, or a multi-step workflow.

This guide assumes you already have the minimal Label Capture integration in place (DataCaptureContext, camera, settings, `LabelCapture` mode, `DataCaptureView`). If not, start from `integration.md` first — the Validation Flow is a *swap-in* for the Basic Overlay, not a from-scratch flow.

> **PriceCapture and VIN pre-made labels are not intended for the VF.** `LabelDefinition.priceCapture(withName:)` and `LabelDefinition.vinLabelDefinition(withName:)` each carry an explicit API-reference `@warning`: they are **"not intended for use in the Validation Flow"** — using them there "may result in incorrect data being captured for the label fields." For price labels or VIN scanning, either build a custom definition out of custom barcode and text fields to use with VF, or keep the pre-made label but use the basic overlay path instead.

## Key classes

| Class | Purpose |
| --- | --- |
| `LabelCaptureValidationFlowOverlay` | The overlay itself; created with `init(labelCapture:view:)` and attached to the `DataCaptureView`. |
| `LabelCaptureValidationFlowDelegate` | Callback protocol; the only required method is `labelCaptureValidationFlowOverlay(_:didCaptureLabelWith:)`. |
| `LabelCaptureValidationFlowSettings` | Customisation settings; created with `init()`, applied with `overlay.apply(_:)`. |

## Full-screen requirement

> **The Validation Flow must be implemented full screen.** The `DataCaptureView` that hosts the Validation Flow overlay must cover the full viewport. Do not embed the Validation Flow inside a card, popover, sheet, or partial-screen container — it will not work correctly. Push the scanning view controller onto the navigation stack, present it modally full-screen, or otherwise dedicate the whole screen to it for the duration of the capture.

If a user asks how to embed the VF in a partial-screen widget, refuse and recommend a full-screen presentation pattern instead.

## Standby / auto-pause on idle

> **The Validation Flow pauses itself when no label is detected for a while.** After an idle period with no successful scan, the VF enters a standby state: scanning halts and the `standbyHintText` toast is shown until the user taps to resume. This is built-in battery-saving behaviour and is **not configurable** — only the hint *text* can be changed (via `standbyHintText`), not the timeout or the pause itself.

If a user reports "the camera stops / freezes after a few seconds in the Validation Flow," this is expected standby, not a bug — tell them to tap to resume. (Distinct from the `labelCapture.isEnabled` toggle footgun in **Setup** below, which prevents scanning from resuming at all.)

## One label definition per flow

> **The Validation Flow drives a single `LabelDefinition` — the *first* one in your `LabelCaptureSettings`.** The iOS overlay starts the flow without naming a label, so the engine defaults to `labelDefinitions[0]`. Additional definitions are **not rejected** (no crash, no error), but they won't drive the flow — if the engine detects a label of a *different* type mid-flow, the VF pauses rather than switching to it.

This is a soft behaviour, not an enforced constraint — don't tell the user the VF "requires exactly one" definition (it doesn't). But if they pass several definitions and wonder why only one is being validated, this is why. To validate multiple distinct label shapes, use the Basic/Advanced overlay or separate scan screens instead of the VF.

## Setup

Replace the `LabelCaptureBasicOverlay` line in your minimal integration with the Validation Flow overlay, and adopt the `LabelCaptureValidationFlowDelegate` instead of `LabelCaptureListener`. Do NOT also add a `LabelCaptureListener` — the Validation Flow overlay manages the capture lifecycle internally.

> **Drop the `labelCapture.isEnabled = true/false` toggles from `viewWillAppear` / `viewWillDisappear` when you swap to the VF.** The overlay enables and disables capture on its own as the flow progresses; the manual toggles fight that and can prevent scanning from resuming after a partial result. Keep the `camera?.switch(toDesiredState:)` lifecycle calls — the overlay does not own the camera.

```swift
import ScanditLabelCapture

// In setupRecognition(), after creating captureView, replace the basicOverlay block with:
let validationFlowOverlay = LabelCaptureValidationFlowOverlay(
    labelCapture: labelCapture,
    view: captureView
)

let validationFlowSettings = LabelCaptureValidationFlowSettings()
// Optional: per-field placeholder text for manual entry (v8.2+)
validationFlowSettings.setPlaceholderText("MM/DD/YYYY", forLabelDefinition: "Expiry Date")
validationFlowOverlay.apply(validationFlowSettings)

validationFlowOverlay.delegate = self
```

## Delegate methods

Adopt the delegate. `didCaptureLabelWith:` is required; `didSubmitManualInputFor:replacingValue:withValue:` (added in v8.1) and `didUpdateResult:asyncId:fields:frameData:` (added in v8.2) are optional — implement them only if the user needs to react to manual entry or partial-result updates.

```swift
extension ScanViewController: LabelCaptureValidationFlowDelegate {
    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didCaptureLabelWith fields: [LabelField]
    ) {
        let barcodeData = fields.first(where: { $0.name == "Barcode" })?.barcode?.data
        let expiryDate: LabelDateResult? = fields.first(where: { $0.name == "Expiry Date" })?.asDate()
        // All required fields are confirmed — process results on the main thread.
        // expiryDate is a LabelDateResult (day/month/year: Int?, dayString/monthString/yearString: String),
        // NOT a Foundation.Date. See `integration.md` "asDate() returns LabelDateResult?" for the
        // conversion helper before passing to DateFormatter.
    }

    // Optional (v8.1+) — fires when the user manually submits a value through the VF UI
    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didSubmitManualInputFor field: LabelField,
        replacingValue oldValue: String?,
        withValue newValue: String
    ) {
        // User manually entered or corrected a value for `field`.
    }

    // Optional (v8.2+) — fires when the validation-flow result is updated during capture
    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didUpdateResult type: LabelResultUpdateType,
        asyncId: Int,
        fields: [LabelField],
        frameData: FrameData?
    ) {
        // Progressive update — useful for live progress UI or capturing the frame image.
    }
}
```

### SDK version awareness

Before writing Validation Flow code, prefer reading the project's `Package.resolved` for the resolved `datacapture-spm` version. If that is unreadable or missing, ask: "Which version of the Scandit iOS SDK are you on?" Then handle the optional delegate methods per version:

- **v8.0.x** — implement only `didCaptureLabelWith:`. Neither optional method exists yet, and `setPlaceholderText(_:forLabelDefinition:)` is not available either. Do not mention these APIs as available — they're not.
- **v8.1.x** — `didSubmitManualInputFor:replacingValue:withValue:` is available; `didUpdateResult:` and `setPlaceholderText` are not. Surface `didSubmitManualInputFor` as an optional opt-in (see below); do not mention v8.2+ APIs.
- **v8.2+** — both optional methods are available, and `setPlaceholderText(_:forLabelDefinition:)` works.

**Surfacing optional methods when the user hasn't asked for them.** When generating a fresh Validation Flow integration on a version that supports the optional methods, **always surface those methods to the user** even if you don't implement them — either by:

1. Including the method stubs in the generated `LabelCaptureValidationFlowDelegate` extension with `// optional — implement if you need …` comments, OR
2. Adding a short note in the response that calls out the available optional methods (with their full signatures) so the user can opt in.

Don't silently omit them — the user paid for the SDK upgrade and should know what new capabilities are available. The signatures are non-obvious enough that copy-pasting them from your response is more useful than pointing the user at the docs.

## Customisation

The Validation Flow is a **fully managed UI component**. Scandit owns the layout, colors, button styles, fonts, and branding. This is intentional — the VF provides a battle-tested, accessible scanning experience without requiring the integrator to design or maintain the UI. The product reasoning: customers who try to build their own scanning UI from scratch consistently miss critical UX details (live progress feedback, manual-entry fallback, accessibility), which leads to lower scan completion rates in the field. The managed VF removes that risk.

**Why was it built this way and not as a more configurable component?** Two reasons:

1. **Consistency and support cost.** Every customisation knob is a surface the support team has to reason about when a customer reports a bug. Locking down the visual surface lets us iterate on the VF (add new components like adaptive recognition hints, improve accessibility, fix layout bugs) without breaking customer apps.
2. **Empirical UX wins.** The current layout is the result of in-field testing — users complete more scans and make fewer manual-entry errors with this layout than with the more open earlier designs. Loosening colours or fonts often degrades that.

**What you CAN customise** (via `LabelCaptureValidationFlowSettings`):

| What | API |
|---|---|
| Per-field placeholder text shown inside the manual-entry input (e.g. expected format hint) | `setPlaceholderText(_:forLabelDefinition:)` (v8.2+) |
| Restart-button text | `restartButtonText` |
| Pause-button text | `pauseButtonText` |
| Finish-button text | `finishButtonText` |
| Toast shown when no label is detected | `standbyHintText` |
| Hint shown alongside the field counter (e.g. "data fields collected") | `validationHintText` |
| Error message shown when manual input doesn't match the field regex | `validationErrorText` |
| Text shown while scanning is in progress | `scanningText` |
| Text shown while ARE is processing a frame | `adaptiveScanningText` |

Apply with `validationFlowOverlay.apply(validationFlowSettings)`.

**What you CANNOT customise**: colours, button styles, layout, fonts, spacing, branding, icons, or any visual aspect of the VF panel. If a customer asks to change these, explain that the VF is a managed component and these are not exposed. If they need full visual control, point them at `LabelCaptureAdvancedOverlay` — but that comes with significantly more implementation cost and the team takes on full ownership of the scanning UX.

## Required vs optional in the Validation Flow

Mandatory/optional means something subtly different in the VF than it does in the underlying capture mode.

| In the capture mode (without VF, via `LabelCaptureListener`) | In the Validation Flow |
|---|---|
| Required = `session.capturedLabels` is populated only when every required field on a label has matched. `didUpdate` itself still fires on every frame. | Required = the user cannot tap *Finish* until this field is either scanned or manually typed. |
| Optional = absence does not block `capturedLabels` from being populated. | Optional = absence does not block *Finish*; the field is shown in the checklist but its row is greyed out / skippable. |

The API is the same in both modes — call `.optional(true)` on the field builder to mark it optional; required is the default. When advising on required vs optional, frame it as "what should block completion?" — required fields block, optional fields don't.

## Customising field highlighting on the camera feed (brushes)

Even when using the Validation Flow, you can add a `LabelCaptureBasicOverlay` alongside it to control how detected fields are highlighted in the live camera view. The VF manages the panel UI; the Basic Overlay manages the AR highlight brushes. Add both:

```swift
let basicOverlay = LabelCaptureBasicOverlay(labelCapture: labelCapture)
captureView.addOverlay(basicOverlay)

let validationFlowOverlay = LabelCaptureValidationFlowOverlay(
    labelCapture: labelCapture,
    view: captureView
)
validationFlowOverlay.delegate = self
```

Then attach a `LabelCaptureBasicOverlayDelegate` to the basic overlay to customise brushes per field and per label (see the **Basic Overlay** section in `integration.md` for the brush delegate methods).

## Capturing the scanned frame image

If users want to store or display the image of the frame alongside the VF result, the approach depends on the SDK version.

**With Validation Flow (v8.2+)** — implement the optional `didUpdateResult:asyncId:fields:frameData:` delegate method. It fires on every partial result update during the flow and receives an optional `FrameData`:

```swift
extension ScanViewController: LabelCaptureValidationFlowDelegate {
    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didCaptureLabelWith fields: [LabelField]
    ) {
        // Hand the final field set + the most recently cached JPEG back to the UI
    }

    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didUpdateResult type: LabelResultUpdateType,
        asyncId: Int,
        fields: [LabelField],
        frameData: FrameData?
    ) {
        guard let frameData,
              let image = frameData.imageBuffers.first?.image,
              let jpeg = image.jpegData(compressionQuality: 0.3)
        else { return }
        cacheLatestFrame(jpeg)
    }
}
```

`didUpdateResult` fires frequently during the flow, so cache the latest JPEG and use it when `didCaptureLabelWith:` confirms the final result. **JPEG is the fastest encoding** — `.jpegData(compressionQuality: 0.3)` is a good default (small file, low CPU). Avoid PNG here unless the customer specifically needs a lossless image.

**With Validation Flow (pre-v8.2)** — older SDKs don't have `didUpdateResult`. Add a `LabelCaptureBasicOverlay` alongside the VF (they can coexist — see brushes above) and attach a `LabelCaptureListener` to capture the frame separately. The listener will fire as fields are detected; cache the most recent JPEG and hand it to the customer along with the VF's final field set when `didCaptureLabelWith:` fires.

## ARE — Adaptive Recognition Engine

ARE is overlay-agnostic — it's a property of the `LabelDefinition` and is **not** specific to the Validation Flow (it works with the Basic and Advanced overlays too). If the user asks about ARE, see the **ARE — Adaptive Recognition Engine** section in `integration.md` for the full constraint list (license flag, Beta status, trial vs production) and the `.adaptiveRecognition(.auto)` enabling API.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/ios/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample that uses `LabelCaptureValidationFlowOverlay`.
