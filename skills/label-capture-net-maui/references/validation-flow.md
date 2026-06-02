# Label Capture Validation Flow — .NET MAUI

The Validation Flow is a guided, multi-step scanning experience built on top of Label Capture. Instead of capturing a whole label in one frame, it lets users scan label fields progressively across several scans, shows a live checklist of captured vs. missing fields, lets them **manually type** values for fields that won't scan, and asks them to review/confirm before finalizing. Use it when accuracy and user confirmation matter more than raw speed; skip it if the basic scan-and-handle path in `references/integration.md` is enough.

This guide builds on the integration guide — the `MauiProgram.cs` setup, `DataCaptureContext`, label definition, `LabelCapture` mode, camera, and `<scandit:DataCaptureView>` are all set up the same way. The Validation Flow only changes **which overlay and listener you use**, plus one iOS keyboard workaround and the overlay lifecycle calls.

> **Single label definition only.** The Validation Flow overlay works with exactly **one** `LabelDefinition` (that definition can contain many fields). If the settings contain multiple definitions, use the basic overlay instead.

> **PriceCapture and VIN pre-made labels are not VF-compatible.** `LabelDefinition.PriceCaptureDefinitionWithName(name)` and `LabelDefinition.VinLabelDefinitionWithName(name)` are **explicitly documented as incompatible with the Validation Flow** — using them inside VF "may result in incorrect data being captured." For price labels or VIN scanning, either build a custom definition out of custom barcode and text fields to use with VF, or keep the pre-made label but use the basic overlay path instead.

## Differences from the basic flow

- Replace (or complement) `LabelCaptureBasicOverlay` with `LabelCaptureValidationFlowOverlay`.
- Implement `ILabelCaptureValidationFlowListener` instead of handling `OnSessionUpdated` yourself — the overlay drives the capture loop and calls you back **once** with the final, user-confirmed fields. The listener is a **plain C# class** (no `NSObject` / `Java.Lang.Object` base — this is MAUI).
- **Call `overlay.OnResume()` / `overlay.OnPause()`** from the page/view-model lifecycle. Unlike the iOS-only skill (which says skip them), a single MAUI build serves both platforms: these methods do real work on Android (keyboard inset handling, etc.) and are harmless no-ops on iOS, so you call them in MAUI.
- **iOS keyboard workaround.** On iOS 18+ MAUI's `KeyboardAutoManagerScroll` prevents the validation flow's manual-entry `UITextField` from becoming first responder. Add `KeyboardAutoManagerScroll.Disconnect();` (guarded by `#if IOS`) in `MauiProgram.CreateMauiApp()`. Without it, the user can't type into the manual-entry field on iOS.

> The Validation Flow overlay does not draw field/label highlights itself. If you want highlighting **and** the guided flow, add a `LabelCaptureBasicOverlay` alongside it (both attach to the same `DataCaptureView`). The official sample does this and sets the basic overlay's `LabelBrush = Brush.TransparentBrush` so only the validation UI is visible.

## Step 0 — iOS keyboard workaround in MauiProgram.cs

```csharp
#if IOS
using Microsoft.Maui.Platform;
#endif

public static MauiApp CreateMauiApp()
{
    ScanditLabelCapture.Initialize();

#if IOS
    // MAUI's KeyboardAutoManagerScroll prevents the validation-flow manual-entry
    // UITextField from becoming first responder on iOS 18+. Disconnect it.
    KeyboardAutoManagerScroll.Disconnect();
#endif

    var builder = MauiApp.CreateBuilder();
    builder.UseMauiApp<App>()
           .UseScanditCore(configure => configure.AddDataCaptureView());
    // ...DI registrations as in integration.md Step 1...
    return builder.Build();
}
```

## Step 1 — Create the overlay (after `HandlerChanged`)

`LabelCaptureValidationFlowOverlay.Create(labelCapture, view)` takes the mode and an optional `DataCaptureView`. In MAUI, pass `null` and attach the overlay yourself via `dataCaptureView.AddOverlay(overlay)` inside the `HandlerChanged` handler (the same place you create the basic overlay).

A small service keeps both overlays together:

```csharp
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.UI.Overlay;
using Scandit.DataCapture.Label.UI.Overlay.Validation;
using Brush = Scandit.DataCapture.Core.UI.Style.Brush;

internal class LabelCaptureService(DataCaptureContext dataCaptureContext) : ILabelCaptureService
{
    private readonly LabelCapture labelCapture =
        LabelCapture.Create(dataCaptureContext, BuildLabelCaptureSettings());

    // Basic overlay only for highlighting; hide the label outline so only the
    // validation UI is visible.
    public LabelCaptureBasicOverlay BuildOverlay()
    {
        var overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        overlay.LabelBrush = Brush.TransparentBrush;
        return overlay;
    }

    public LabelCaptureValidationFlowOverlay BuildValidationFlowOverlay(Action<string> onLabelScanned)
    {
        // Optionally customize the texts/placeholders (Step 3).
        var settings = LabelCaptureValidationFlowSettings.Create();

        var overlay = LabelCaptureValidationFlowOverlay.Create(this.labelCapture, view: null);
        overlay.Listener = new LabelCaptureValidationFlowListener(onLabelScanned);
        overlay.ApplySettings(settings);
        return overlay;
    }

    // ...BuildLabelCaptureSettings(), Enable/Disable as in integration.md...
}
```

Wire both overlays in the page's `HandlerChanged`:

```csharp
private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
{
    this.labelCaptureOverlay = this.viewModel.BuildOverlay();
    this.validationFlowOverlay = this.viewModel.GetValidationFlowOverlay();

    this.dataCaptureView.AddOverlay(this.labelCaptureOverlay);
    this.dataCaptureView.AddOverlay(this.validationFlowOverlay);
}
```

### LabelCaptureValidationFlowOverlay members

| Member | Description |
|--------|-------------|
| `static Create(LabelCapture, DataCaptureView?)` | Factory. In MAUI pass `null` and add via `dataCaptureView.AddOverlay(overlay)`. |
| `Listener` | `ILabelCaptureValidationFlowListener?` (get/set). |
| `ApplySettings(LabelCaptureValidationFlowSettings)` | Apply customized texts/placeholders; takes effect immediately. |
| `OnResume()` / `OnPause()` | **Call these from the page lifecycle in MAUI** (real on Android, no-op on iOS). |
| `ShouldHandleKeyboardInsetsInternally` | `bool` — Android keyboard inset handling (no effect on iOS). |
| `Dispose()` | Releases native resources. |

## Step 2 — Implement the listener (plain C# class)

`ILabelCaptureValidationFlowListener` has three methods. The one you must implement is `OnValidationFlowLabelCaptured` — it delivers the final, user-validated fields. The other two are optional hooks for analytics / progress; provide empty bodies if unused. **The listener is a plain C# class** — no platform base class.

```csharp
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay.Validation;

internal class LabelCaptureValidationFlowListener(Action<string> onLabelScanned)
    : ILabelCaptureValidationFlowListener
{
    public void OnValidationFlowLabelCaptured(IList<LabelField> fields)
    {
        // A field the user typed by hand surfaces its value through Text — even a barcode
        // field. Read Barcode?.Data first and fall back to Text.
        string? barcode = fields.FirstOrDefault(f => f.Name == "Barcode")?.Barcode?.Data
                          ?? fields.FirstOrDefault(f => f.Name == "Barcode")?.Text;
        string? expiry = fields.FirstOrDefault(f => f.Name == "Expiry Date")?.Text;

        // Marshal to the main thread before touching the UI.
        MainThread.BeginInvokeOnMainThread(() =>
            onLabelScanned($"Barcode: {barcode}, Expiry: {expiry}"));
    }

    // Optional: fired when the user types a value for a field. Useful for analytics.
    public void OnManualInputSubmitted(LabelField field, string? oldValue, string newValue) { }

    // Optional: progress updates (sync = once; async = started/finished pairs by asyncId).
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
settings.ValidationHintText = "fields captured";          // progress shown after a scan phase
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

Drive the camera and mode through the page lifecycle as in `references/integration.md` Step 6, and **call the overlay's `OnResume()` / `OnPause()`** from the same `ResumeAsync` / `SleepAsync`. The SDK auto-disables the mode and pauses the camera before `OnValidationFlowLabelCaptured` fires.

```csharp
public override async Task ResumeAsync()
{
    var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
    if (status != PermissionStatus.Granted)
    {
        status = await Permissions.RequestAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted) return;
    }

    if (this.shouldResumeScanning)
    {
        await cameraService.ResumeFrameSourceAsync();
        labelCaptureService.Enable();
    }

    this.validationFlowOverlay?.OnResume();
}

public override async Task SleepAsync()
{
    this.validationFlowOverlay?.OnPause();

    this.shouldResumeScanning = labelCaptureService.IsEnabled;

    await cameraService.PauseFrameSourceAsync();
    labelCaptureService.Disable();
}
```

To scan another label after a confirmation (e.g. once the user dismisses the result alert), re-enable the mode and turn the camera back on:

```csharp
await cameraService.ResumeFrameSourceAsync();
labelCaptureService.Enable();
```

A typical view-model wiring, mirroring the official sample, pauses the camera when a label is confirmed and resumes after the user dismisses a "Label captured" alert:

```csharp
public LabelCaptureValidationFlowOverlay GetValidationFlowOverlay()
{
    return this.validationFlowOverlay ??= labelCaptureService.BuildValidationFlowOverlay(
        onLabelScanned: async label =>
        {
            await cameraService.PauseFrameSourceAsync();
            await messageService.ShowAsync(
                title: "Label captured",
                message: label,
                buttonText: "Continue scanning",
                onDismiss: async () =>
                {
                    await cameraService.ResumeFrameSourceAsync();
                    labelCaptureService.Enable();
                });
        });
}
```

## Key rules

1. **Validation Flow needs a single `LabelDefinition`.**
2. **iOS keyboard workaround** — add `KeyboardAutoManagerScroll.Disconnect();` (guarded by `#if IOS`) in `MauiProgram.cs`, or the manual-entry field won't accept typing on iOS 18+.
3. **Use `LabelCaptureValidationFlowOverlay` + `ILabelCaptureValidationFlowListener`** (plain C# class) — don't also hand-process `OnSessionUpdated`; the overlay drives the loop. Create the overlay in `HandlerChanged` with `Create(labelCapture, view: null)` + `AddOverlay`.
4. **Call `overlay.OnResume()` / `OnPause()`** from `ResumeAsync` / `SleepAsync` — they're real on Android and no-ops on iOS, and a single MAUI build targets both.
5. **`OnValidationFlowLabelCaptured` delivers the final confirmed fields**; marshal to the main thread with `MainThread.BeginInvokeOnMainThread(...)`. The mode is auto-disabled and the camera auto-paused before it fires.
6. **Manually entered values come back as `field.Text`** — read `Barcode?.Data ?? Text` for fields that may have been typed.
7. **Customize via `LabelCaptureValidationFlowSettings.Create()` + `ApplySettings`**; avoid the deprecated text properties.
8. **For highlighting + the guided flow, add a `LabelCaptureBasicOverlay` alongside** the validation overlay on the same `DataCaptureView` (set `LabelBrush = Brush.TransparentBrush`).

## Where to go next

- [Advanced Configurations (Android)](https://docs.scandit.com/sdks/net/android/label-capture/advanced/) · [iOS](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) — full Validation Flow customization, adaptive recognition, and the advanced overlay.
