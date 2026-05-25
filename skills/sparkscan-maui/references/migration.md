# Migrating SparkScan on .NET MAUI Between Major SDK Versions

This guide covers the SparkScan-relevant changes when moving an existing **MAUI** integration (`<UseMaui>true</UseMaui>`) between major Scandit Data Capture SDK versions. For BarcodeCapture-specific changes, cross-reference [skills/barcode-capture-maui/references/migration.md](../../barcode-capture-maui/references/migration.md).

Always cross-reference the official migration guides:

- 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/ (Android) and https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/ (iOS) — MAUI inherits both per-TFM.
- 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/ (Android) and https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/ (iOS).

## Step 0 — Determine the current and target versions

WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` to pin the latest stable release. Skip `-beta.*`/`-preview.*`/`-rc.*`. Open the project's `.csproj` and note the existing `<PackageReference>` versions for all four packages:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Core.Maui`
- `Scandit.DataCapture.Barcode`
- `Scandit.DataCapture.Barcode.Maui`

Bump them all to the same target version. Releases are aligned across the four packages — a mismatch will fail to build or restore.

## 6.x → 7.x

### NuGet packages

Update all four packages to a 7.x release in lockstep. Run `dotnet restore` / `dotnet build` for both TFMs (`net*-android`, `net*-ios`) to surface any compile breaks.

### SparkScan API renames

The renames are the same as on the per-TFM skills, applied through the MAUI bindable surface as well:

| 6.x | 7.x |
|-----|-----|
| `SparkScanView.TorchButtonVisible` | `SparkScanView.TorchControlVisible` |
| `SparkScanViewSettings.ContinuousCaptureTimeout` | _Removed_ — controlled internally. Delete any assignment. |
| `SparkScanViewSettings.SoundModeOn` / `SoundModeOff` | `SparkScanViewSettings.SoundEnabled` (`bool`) |
| `SparkScanViewSettings.HapticModeOn` / `HapticModeOff` | `SparkScanViewSettings.HapticEnabled` (`bool`) |
| `SparkScanFeedback` | `SparkScanBarcodeFeedback` (abstract) + `SparkScanBarcodeSuccessFeedback` / `SparkScanBarcodeErrorFeedback` (concrete) |
| `sparkScan.Feedback = …` | `sparkScanView.Feedback = …` (delegate, set in the page code-behind or as the XAML bindable property `Feedback="{Binding ...}"`). The delegate now receives the `Barcode` and returns a `SparkScanBarcodeFeedback`. |

If your XAML uses `Feedback="{Binding ...}"`, double-check the binding still resolves to an `ISparkScanFeedbackDelegate` (and not the old `SparkScanFeedback` POCO).

### Default changes

- `SparkScanViewSettings.TriggerButtonCollapseTimeout` default changed to `5 seconds`. Use `TimeSpan.FromSeconds(-1)` to disable auto-collapse.

### New 7.x APIs worth adopting

- `SparkScanScanningModeDefault(SparkScanScanningBehavior, SparkScanPreviewBehavior)` and `SparkScanScanningModeTarget(SparkScanScanningBehavior, SparkScanPreviewBehavior)` replace the older positional constructors.
- `SparkScanView.LabelCaptureButtonVisible` and `LabelCaptureButtonTapped` event for opening a Label Capture flow from the toolbar.
- `SparkScanView.ViewStateChanged` event (`EventHandler<SparkScanViewStateEventArgs>`).
- `SparkScanView.PreviewCloseControlVisible` bindable property.

### Builder chain — unchanged

The MAUI builder shape stayed the same:

```csharp
builder.UseScanditCore().UseScanditBarcode(c => c.AddSparkScanView());
```

If you previously had `UseScanditCore(c => c.AddDataCaptureView())` because you were also using BarcodeCapture, leave that in place — it is required for `<scandit:DataCaptureView>`.

## 7.x → 8.x

### NuGet packages

Bump all four packages to an 8.x release. Pin the same version on all four.

### Builder chain — still unchanged

```csharp
builder.UseScanditCore().UseScanditBarcode(c => c.AddSparkScanView());
```

The `UseScanditCore()` / `UseScanditBarcode(...)` extensions invoke `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` internally for SDK 8.0+, **so you do not add any explicit `Initialize()` call in `MainApplication.cs` or `AppDelegate.cs`** for MAUI projects. If a migration walkthrough for `sparkscan-net-android` / `sparkscan-net-ios` instructs you to add `Initialize()` calls, that's for **non-MAUI** projects only.

> If your project is a hybrid where MAUI shells delegate to native Activities/ViewControllers, only those native paths need explicit `Initialize()` calls. The pure MAUI path (`Platforms/Android/MainApplication.cs` + `Platforms/iOS/AppDelegate.cs` calling `MauiProgram.CreateMauiApp()`) does not.

### Symbology renames

- `Symbology.Ean13Upca` (was `Ean13UpcA` in earlier 7.x — confirm via IntelliSense).
- `Symbology.Upce` (was `UpcE`).
- Other PascalCase normalizations carry over from BarcodeCapture; cross-check against the .NET API page.

### API renames inherited from BarcodeCapture

These also affect SparkScan code:

- `BarcodeCaptureFeedback` → `BarcodeCapture.Feedback` (BarcodeCapture-specific; mentioned for context).
- `SparkScan.SparkScanLicenseInfo` is the supported way to query licensed symbologies — there is no longer a top-level helper.

### Removed / replaced

- `SparkScanViewSettings.IgnoreDragLimits` was removed; drag bounds are controlled internally.
- `SparkScanView.PreviewSizeControlVisible` replaces some legacy preview-size APIs.

### XAML bindable additions in 8.x

- `Feedback` bindable property on `<scandit:SparkScanView>` — you can wire the feedback delegate from XAML as well as from code-behind.
- `SparkScanViewSettings.SmartSelectionCandidateBrush` for theming the smart-selection highlight.

## Common migration mistakes (MAUI-specific)

- **Forgetting to update all four NuGet packages.** The two `.Maui` packages and the two plain packages must all carry the same version. A mismatch produces obscure `MissingMethodException`s at startup.
- **Manually calling `ScanditCaptureCore.Initialize()` in `MainApplication.cs` / `AppDelegate.cs`.** The MAUI builder extensions handle initialization. Adding an explicit call on top will not crash, but it's redundant and easy to forget when you later rebase off the upstream MAUI template.
- **Confusing the SparkScan builder shape with BarcodeCapture's.** SparkScan: `UseScanditCore()` (no lambda) + `UseScanditBarcode(c => c.AddSparkScanView())`. BarcodeCapture: `UseScanditCore(c => c.AddDataCaptureView())` + `UseScanditBarcode()` (no lambda). The two are easy to mix up.
- **Leaving `xmlns:scandit="…;assembly=Scandit.DataCapture.Barcode.Maui"`.** The XAML assembly attribute is `ScanditBarcodeCaptureMaui` (no dots) — the NuGet id and the actual assembly name differ. Update any `xmlns:scandit=…` entries that copy the package id.
- **Stale lifecycle calls from a pre-MAUI port.** If you previously had a native `Platforms/Android/MainActivity.cs` calling `sparkScanView.OnPause()` / `OnResume()`, replace those with `this.SparkScanView.OnAppearing()` / `OnDisappearing()` on the MAUI page. The Android-only `OnPause`/`OnResume` and iOS-only `PrepareScanning`/`StopScanning` are not on the MAUI control.
- **Hardware-trigger keycode customization.** `HardwareTriggerKeyCode` is `#if __ANDROID__` only — it cannot be set from cross-platform MAUI code. If you need to customize it, do so from an Android-specific partial class or via a `DependencyService`.
- **`DisplayAlert` warnings.** In MAUI 9 the non-async `DisplayAlert` overload is obsolete. Replace with `await this.DisplayAlertAsync(title, message, "OK")`.

## Validation checklist

After bumping versions, run:

```bash
dotnet restore
dotnet build -f net*-android
dotnet build -f net*-ios
```

Smoke-test on a device:

- The trigger button appears and the camera preview opens when tapped.
- Scanning a known-good barcode reports a match.
- Returning to background and foreground does not leave the camera locked or the preview frozen.
- For Android, hardware-button trigger (if enabled) still maps to `HardwareTriggerEnabled` behavior.
