# Label Capture Validation Flow — .NET for Android

The Validation Flow is a guided, multi-step scanning experience built on top of Label Capture. Instead of capturing a whole label in one frame, it lets users scan label fields progressively across several scans, shows a live checklist of captured vs. missing fields, lets them **manually type** values for fields that won't scan, and asks them to review/confirm before finalizing. Use it when accuracy and user confirmation matter more than raw speed; skip it if the basic scan-and-handle path in `references/integration.md` is enough.

This guide builds on the integration guide — the `DataCaptureContext`, label definition, `LabelCapture` mode, camera, and `DataCaptureView` are all set up the same way. The Validation Flow only changes **which overlay and listener you use**.

> **Single label definition only.** The Validation Flow overlay works with exactly **one** `LabelDefinition` (that definition can contain many fields). If the settings contain multiple definitions, use the basic overlay instead.

> **PriceCapture and VIN pre-made labels are not VF-compatible.** `LabelDefinition.PriceCaptureDefinitionWithName(name)` and `LabelDefinition.VinLabelDefinitionWithName(name)` are **explicitly documented as incompatible with the Validation Flow** — using them inside VF "may result in incorrect data being captured." For price labels or VIN scanning, either build a custom definition out of custom barcode and text fields to use with VF, or keep the pre-made label but use the basic overlay path instead.

## Differences from the basic flow

- Replace (or complement) `LabelCaptureBasicOverlay` with `LabelCaptureValidationFlowOverlay`.
- Implement `ILabelCaptureValidationFlowListener` instead of handling `OnSessionUpdated` yourself — the overlay drives the capture loop and calls you back **once** with the final, user-confirmed fields.
- The overlay needs lifecycle delegation: call its `OnResume()` / `OnPause()` from the activity/fragment.
- The validation-flow callback (`OnValidationFlowLabelCaptured`) runs on the **main thread**, so it's safe to touch UI directly. (This is the opposite of the basic `OnSessionUpdated`, which is on a background thread.) Before it fires, the SDK automatically disables the mode and pauses the camera; re-enable + turn the camera back on to scan the next label.

> The Validation Flow overlay does not draw field/label highlights itself. If you want highlighting **and** the guided flow, add a `LabelCaptureBasicOverlay` alongside it (both attach to the same `DataCaptureView`).

## Step 1 — Create the overlay

`LabelCaptureValidationFlowOverlay.Create(labelCapture, view)` takes the mode and an optional `DataCaptureView` (pass `null` and add it yourself via `dataCaptureView.AddOverlay(overlay)`, or pass the view to auto-add).

```csharp
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.UI.Overlay.Validation;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
// ...add dataCaptureView to your layout (see integration.md Step 5)...

this.validationFlowOverlay = LabelCaptureValidationFlowOverlay.Create(this.labelCapture, null);
this.validationFlowOverlay.Listener = new MyValidationFlowListener(/* ... */);
this.dataCaptureView.AddOverlay(this.validationFlowOverlay);

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
| `OnResume()` / `OnPause()` | **Android lifecycle delegation — required.** Call from the activity/fragment's `OnResume`/`OnPause`. |
| `ShouldHandleKeyboardInsetsInternally` | `bool` (get/set) — when `true`, the overlay adjusts its own layout when the soft keyboard appears so the manual-entry field isn't obscured. Useful for Android 15 edge-to-edge windows that don't handle insets themselves. |
| `Dispose()` | Releases native resources. |

## Step 2 — Implement the listener

`ILabelCaptureValidationFlowListener` has three methods. The one you must implement is `OnValidationFlowLabelCaptured` — it delivers the final, user-validated fields on the main thread. The other two are optional hooks for analytics / progress; provide empty bodies if unused.

```csharp
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay.Validation;

internal sealed class MyValidationFlowListener : Java.Lang.Object, ILabelCaptureValidationFlowListener
{
    private readonly Action<string?, string?> onConfirmed;

    public MyValidationFlowListener(Action<string?, string?> onConfirmed)
    {
        this.onConfirmed = onConfirmed;
    }

    // Called on the MAIN thread when the user has confirmed the captured label.
    public void OnValidationFlowLabelCaptured(IList<LabelField> fields)
    {
        string? barcode = fields.FirstOrDefault(f => f.Name == "Barcode")?.Barcode?.Data
                          ?? fields.FirstOrDefault(f => f.Name == "Barcode")?.Text; // manual entry arrives as Text
        string? expiry = fields.FirstOrDefault(f => f.Name == "Expiry Date")?.Text;
        this.onConfirmed(barcode, expiry);
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

## Step 4 — Lifecycle delegation

The overlay manages its own UI state (the in-progress checklist, keyboard, standby), so it must be told when the host resumes/pauses. Call `OnResume()` / `OnPause()` in addition to toggling the camera.

```csharp
protected override void OnResume()
{
    base.OnResume();
    this.RequestCameraPermission();          // turns camera on once granted
    this.validationFlowOverlay.OnResume();
}

protected override void OnPause()
{
    base.OnPause();
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.validationFlowOverlay.OnPause();
}
```

To scan another label after a confirmation, re-enable the mode and turn the camera back on (e.g. after the user dismisses the result):

```csharp
this.labelCapture.Enabled = true;
this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
```

## Key rules

1. **Validation Flow needs a single `LabelDefinition`.**
2. **Use `LabelCaptureValidationFlowOverlay` + `ILabelCaptureValidationFlowListener`** — don't also hand-process `OnSessionUpdated`; the overlay drives the loop.
3. **`OnValidationFlowLabelCaptured` runs on the main thread** and delivers the final confirmed fields; the mode is auto-disabled and the camera auto-paused before it fires.
4. **Delegate lifecycle** — call `overlay.OnResume()` / `overlay.OnPause()` from the host.
5. **Manually entered values come back as `field.Text`** — fall back to `Text` when a field may have been typed.
6. **Customize via `LabelCaptureValidationFlowSettings.Create()` + `ApplySettings`**; avoid the deprecated text properties.
7. **Set `ShouldHandleKeyboardInsetsInternally = true`** if the keyboard covers the manual-entry field (common on Android 15 edge-to-edge windows).

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/android/label-capture/advanced/) — full Validation Flow customization, adaptive recognition, and the advanced overlay.
