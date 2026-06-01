# Label Capture Validation Flow — .NET for iOS

The Validation Flow is a guided, multi-step scanning experience built on top of Label Capture. Instead of capturing a whole label in one frame, it lets users scan label fields progressively across several scans, shows a live checklist of captured vs. missing fields, lets them **manually type** values for fields that won't scan, and asks them to review/confirm before finalizing. Use it when accuracy and user confirmation matter more than raw speed; skip it if the basic scan-and-handle path in `references/integration.md` is enough.

This guide builds on the integration guide — the `DataCaptureContext`, label definition, `LabelCapture` mode, camera, and `DataCaptureView` are all set up the same way. The Validation Flow only changes **which overlay and listener you use**.

> **Single label definition only.** The Validation Flow overlay works with exactly **one** `LabelDefinition` (that definition can contain many fields). If the settings contain multiple definitions, use the basic overlay instead.

## Differences from the basic flow

- Replace (or complement) `LabelCaptureBasicOverlay` with `LabelCaptureValidationFlowOverlay`.
- Implement `ILabelCaptureValidationFlowListener` instead of handling `OnSessionUpdated` yourself — the overlay drives the capture loop and calls you back **once** with the final, user-confirmed fields.
- The validation-flow callback (`OnValidationFlowLabelCaptured`) runs on the **main thread** on iOS, but it's good practice to marshal explicitly with `DispatchQueue.MainQueue.DispatchAsync(...)` before touching UIKit (as the official iOS sample does). Before it fires, the SDK automatically disables the mode and pauses the camera; re-enable + turn the camera back on to scan the next label.

> **No iOS lifecycle delegation.** Unlike Android, the iOS validation-flow overlay does **not** need `OnResume()` / `OnPause()` calls — those methods (and `ShouldHandleKeyboardInsetsInternally`) exist in the binding but are **Android-specific no-ops on iOS**. Do not call them in an iOS integration. The camera lifecycle in `ViewWillAppear`/`ViewWillDisappear` is enough.

> The Validation Flow overlay does not draw field/label highlights itself. If you want highlighting **and** the guided flow, add a `LabelCaptureBasicOverlay` alongside it (both attach to the same `DataCaptureView`). The official sample does this and sets the basic overlay's `LabelBrush = Brush.TransparentBrush` so only the validation UI is visible.

## Step 1 — Create the overlay

`LabelCaptureValidationFlowOverlay.Create(labelCapture, view)` takes the mode and an optional `DataCaptureView` (pass `null` and add it yourself via `dataCaptureView.AddOverlay(overlay)`, or pass the view to auto-add).

```csharp
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.UI.Overlay.Validation;
using UIKit;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
// ...add dataCaptureView to your view hierarchy (see integration.md Step 5)...

this.validationFlowOverlay = LabelCaptureValidationFlowOverlay.Create(this.labelCapture, this.dataCaptureView);
this.validationFlowOverlay.Listener = new MyValidationFlowListener(/* ... */);

// Optionally customize the texts (Step 3).
var settings = LabelCaptureValidationFlowSettings.Create();
this.validationFlowOverlay.ApplySettings(settings);
```

### LabelCaptureValidationFlowOverlay members

| Member | Description |
|--------|-------------|
| `static Create(LabelCapture, DataCaptureView?)` | Factory. Pass `null` for the view and add it with `AddOverlay`, or pass the view to auto-add. |
| `Listener` | `ILabelCaptureValidationFlowListener?` (get/set). |
| `ApplySettings(LabelCaptureValidationFlowSettings)` | Apply customized texts/placeholders; takes effect immediately. |
| `OnResume()` / `OnPause()` | **Android-only.** No-ops on iOS — do not call them. |
| `ShouldHandleKeyboardInsetsInternally` | `bool` — **Android-only; has no effect on iOS.** |
| `Dispose()` | Releases native resources. |

## Step 2 — Implement the listener

`ILabelCaptureValidationFlowListener` has three methods. The one you must implement is `OnValidationFlowLabelCaptured` — it delivers the final, user-validated fields. The other two are optional hooks for analytics / progress; provide empty bodies if unused. The listener derives from **`NSObject`**.

```csharp
using CoreFoundation;
using Foundation;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay.Validation;

internal sealed class MyValidationFlowListener : NSObject, ILabelCaptureValidationFlowListener
{
    private readonly Action<string?, string?> onConfirmed;

    public MyValidationFlowListener(Action<string?, string?> onConfirmed)
    {
        this.onConfirmed = onConfirmed;
    }

    // Delivers the final fields once the user has confirmed the captured label.
    public void OnValidationFlowLabelCaptured(IList<LabelField> fields)
    {
        // A field the user typed by hand surfaces its value through Text — even a barcode field.
        // Read Barcode?.Data first and fall back to Text.
        string? barcode = fields.FirstOrDefault(f => f.Name == "Barcode")?.Barcode?.Data
                          ?? fields.FirstOrDefault(f => f.Name == "Barcode")?.Text;
        string? expiry = fields.FirstOrDefault(f => f.Name == "Expiry Date")?.Text;

        // Marshal to the main thread before touching UIKit.
        DispatchQueue.MainQueue.DispatchAsync(() => this.onConfirmed(barcode, expiry));
    }

    // Optional: fired when the user types a value for a field. Useful for analytics.
    public void OnManualInputSubmitted(LabelField field, string? oldValue, string newValue) { }

    // Optional: progress updates (sync = once; async = started/finished pairs correlated by asyncId).
    public void OnValidationFlowResultUpdate(
        LabelResultUpdateType type, long asyncId, IList<LabelField> fields, IFrameData? frameData) { }
}
```

> A field the user filled in manually surfaces its value through `field.Text`, even for a barcode field — read `Barcode?.Data` first and fall back to `Text` when reading values that may have been entered by hand.

## Step 3 — Customize texts and placeholders (optional)

`LabelCaptureValidationFlowSettings.Create()` gives a settings object with default texts. Set any of these properties, then call `overlay.ApplySettings(settings)`.

```csharp
var settings = LabelCaptureValidationFlowSettings.Create();

settings.StandbyHintText = "Scanning paused to save battery";
settings.ValidationHintText = "fields captured";          // shown after a scan phase (progress)
settings.ValidationErrorText = "Invalid value";           // shown under a field with a bad value
settings.ScanningText = "Scanning…";
settings.AdaptiveScanningText = "Processing…";
settings.FinishButtonText = "Finish";
settings.RestartButtonText = "Restart";
settings.PauseButtonText = "Pause";

// Placeholder shown in the manual-entry field, per label-field name:
settings.SetPlaceholderText("MM/DD/YYYY", "Expiry Date");

this.validationFlowOverlay.ApplySettings(settings);
```

Available text properties: `StandbyHintText`, `ValidationHintText`, `ValidationErrorText`, `ScanningText`, `AdaptiveScanningText`, `FinishButtonText`, `RestartButtonText`, `PauseButtonText`, plus `SetPlaceholderText(placeholder, fieldName)` / `GetPlaceholderText(fieldName)`.

> `MissingFieldsHintText`, `RequiredFieldErrorText`, and `ManualInputButtonText` exist but are **deprecated** — don't introduce them in new code.

## Step 4 — Lifecycle & scanning the next label

There is no overlay lifecycle delegation on iOS. Just drive the camera and mode through the controller lifecycle as in `references/integration.md` Step 7:

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    this.labelCapture.Enabled = true;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.labelCapture.Enabled = false;
}
```

The SDK auto-disables the mode and pauses the camera before `OnValidationFlowLabelCaptured` fires. To scan another label after a confirmation (e.g. once the user dismisses the result), re-enable the mode and turn the camera back on:

```csharp
this.labelCapture.Enabled = true;
this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
```

## Key rules

1. **Validation Flow needs a single `LabelDefinition`.**
2. **Use `LabelCaptureValidationFlowOverlay` + `ILabelCaptureValidationFlowListener`** (derive the listener from `NSObject`) — don't also hand-process `OnSessionUpdated`; the overlay drives the loop.
3. **`OnValidationFlowLabelCaptured` delivers the final confirmed fields**; marshal to the main thread with `DispatchQueue.MainQueue.DispatchAsync(...)` before touching UIKit. The mode is auto-disabled and the camera auto-paused before it fires.
4. **No iOS lifecycle delegation** — `overlay.OnResume()` / `overlay.OnPause()` and `ShouldHandleKeyboardInsetsInternally` are Android-only no-ops; don't call them. The camera lifecycle is the only handle.
5. **Manually entered values come back as `field.Text`** — fall back to `Text` when a field may have been typed.
6. **Customize via `LabelCaptureValidationFlowSettings.Create()` + `ApplySettings`**; avoid the deprecated text properties.
7. **For highlighting + the guided flow, add a `LabelCaptureBasicOverlay` alongside** the validation overlay on the same `DataCaptureView`.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) — full Validation Flow customization, adaptive recognition, and the advanced overlay.
