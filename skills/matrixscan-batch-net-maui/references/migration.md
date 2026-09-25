# MatrixScan Batch .NET MAUI Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for any of:

- `<PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="..." />`
- `<PackageReference Include="Scandit.DataCapture.Core.Maui" Version="..." />`
- `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />`
- `<PackageReference Include="Scandit.DataCapture.Core" Version="..." />`

All four should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

> Note: Scandit's MAUI packages were not published on all `6.x` minor versions. If the project is on a `6.x` MAUI release, confirm with the user before assuming the BarcodeBatch MAUI API was identical to 7.x — fetch the MAUI changelog if in doubt. MatrixScan Batch was named `BarcodeTracking` in v6 (under `Scandit.DataCapture.Barcode.Tracking.*`) and was renamed to `BarcodeBatch` at v7.0 across all platforms.

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest stable version. Then update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Core.Maui`
- `Scandit.DataCapture.Barcode`
- `Scandit.DataCapture.Barcode.Maui`

All four should move together. Do **not** guess. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix).

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use MatrixScan Batch (search for `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchSession`, `BarcodeBatchEventArgs`, `IBarcodeBatchListener`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, and also the v6 names `BarcodeTracking`, `BarcodeTrackingSettings`, `BarcodeTrackingSession`, `IBarcodeTrackingListener`, `BarcodeTrackingBasicOverlay`, `BarcodeTrackingAdvancedOverlay`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for .NET MAUI MatrixScan Batch is primarily about the cross-platform `BarcodeTracking` → `BarcodeBatch` rename and the new namespace under `Batch.*`. Go through every section below and apply each change that matches the project.

### `BarcodeTracking` → `BarcodeBatch` rename

The class family was renamed at v7.0 across all platforms (Android, iOS, .NET, MAUI, Flutter, etc.). Apply this rename everywhere the old names appear:

| Old (v6) | New (v7) |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `BarcodeTrackingEventArgs` | `BarcodeBatchEventArgs` |
| `IBarcodeTrackingListener` | `IBarcodeBatchListener` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingBasicOverlayStyle` | `BarcodeBatchBasicOverlayStyle` |
| `IBarcodeTrackingBasicOverlayListener` | `IBarcodeBatchBasicOverlayListener` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `IBarcodeTrackingAdvancedOverlayListener` | `IBarcodeBatchAdvancedOverlayListener` |
| `BarcodeTracking.RecommendedCameraSettings` | `BarcodeBatch.RecommendedCameraSettings` |

Method parameter names that include `BarcodeTracking` (e.g. `OnObservationStarted(BarcodeTracking barcodeTracking)`) become `OnObservationStarted(BarcodeBatch barcodeBatch)`. Update the parameter type and parameter name to match.

### Namespace rename

The `using` directives change with the class names:

| Old (v6) | New (v7) |
|---|---|
| `using Scandit.DataCapture.Barcode.Tracking.Capture;` | `using Scandit.DataCapture.Barcode.Batch.Capture;` |
| `using Scandit.DataCapture.Barcode.Tracking.Data;` | `using Scandit.DataCapture.Barcode.Batch.Data;` |
| `using Scandit.DataCapture.Barcode.Tracking.UI.Overlay;` | `using Scandit.DataCapture.Barcode.Batch.UI.Overlay;` |

Apply a project-wide search-and-replace on `Scandit.DataCapture.Barcode.Tracking` → `Scandit.DataCapture.Barcode.Batch` followed by `BarcodeTracking` → `BarcodeBatch`. Run the build afterwards and clean up any references the rename missed.

### Camera setup — use `RecommendedCameraSettings`

If the project constructs a `CameraSettings` by hand (e.g. `new CameraSettings { PreferredResolution = ... }`), prefer the recommended settings property after the rename:

**Before (v6 pattern):**

```csharp
var cameraSettings = new CameraSettings { PreferredResolution = VideoResolution.Auto };
var camera = Camera.GetCamera(CameraPosition.WorldFacing);
camera?.ApplySettingsAsync(cameraSettings);
```

**After (v7+ pattern):**

```csharp
var camera = Camera.GetCamera(CameraPosition.WorldFacing);
camera?.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
```

If a specific resolution (e.g. `VideoResolution.FullHd`) is required — and on MAUI this is the official sample's choice for better decode range — fetch the recommended settings first and then override only what you need:

```csharp
var cameraSettings = BarcodeBatch.RecommendedCameraSettings;
cameraSettings.PreferredResolution = VideoResolution.FullHd;
this.camera.ApplySettingsAsync(cameraSettings);
```

`BarcodeBatch.RecommendedCameraSettings` is a **static property**, not a method.

### Factory rename: nothing to change

`BarcodeBatch.Create(context, settings)` was the .NET factory in v6 (as `BarcodeTracking.Create(context, settings)`) and continues to be the factory in v7+. There is **no** rename from `Create(...)` to `ForDataCaptureContext(...)` — the .NET binding has always exposed `Create`. If the codebase already uses `BarcodeTracking.Create(...)`, the only change is renaming `BarcodeTracking` → `BarcodeBatch` (covered above).

### Builder chain — confirm both `UseScanditCore` and `UseScanditBarcode` are present

`UseScanditCore(c => c.AddDataCaptureView())` and `UseScanditBarcode()` are required from 7.x onwards in `MauiProgram.cs`. If the project's `MauiProgram.cs` only calls one of them (e.g. an older sample that bundled both registrations under `UseScanditBarcode`), add the missing call.

### Advanced overlay's `ViewForTrackedBarcode` — partial-class pattern unchanged

The MAUI-specific `partial`-class split for `BarcodeBatchAdvancedOverlay.ViewForTrackedBarcode` (returning `Android.Views.View?` on Android and `UIKit.UIView?` on iOS, via `ToPlatform(new MauiContext(...))`) is the same in v6 and v7. The only change is the type rename — `IBarcodeTrackingAdvancedOverlayListener` becomes `IBarcodeBatchAdvancedOverlayListener` and `BarcodeTrackingAdvancedOverlay` becomes `BarcodeBatchAdvancedOverlay`.

### New v7 APIs (optional, mention only if asked)

- `BarcodeBatchBasicOverlayStyle.Dot` — an alternative to the default `Frame` style. Pass it to `BarcodeBatchBasicOverlay.Create(barcodeBatch, BarcodeBatchBasicOverlayStyle.Dot)`.

---

## Migration: 7 → 8

The 7→8 step for .NET MAUI MatrixScan Batch is small. The factory methods (`BarcodeBatch.Create(context, settings)` and the overlay `Create(...)` overloads), the listener / event surface, the session API, the `<scandit:DataCaptureView>` XAML control, and the `HandlerChanged` overlay pattern are **all unchanged**.

### **No** manual `Initialize()` call needed in MAUI

The non-MAUI `matrixscan-batch-net-android` and `matrixscan-batch-net-ios` skills both call out that SDK 8.0+ requires explicit `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` calls in `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`. **In MAUI this is not required** — the `UseScanditCore(...)` and `UseScanditBarcode()` builder extensions perform the SDK initialization themselves. Leave `MainApplication.cs` and `AppDelegate.cs` as the MAUI template generates them; if a previous skill or sample added the `Initialize()` calls there for some reason, you can safely remove them.

If `MauiProgram.cs` is missing either `UseScanditCore(c => c.AddDataCaptureView())` or `UseScanditBarcode()`, **that** is the v8 blocker — add the missing call.

### `VideoResolution.Auto` deprecated

If the project creates a `CameraSettings` with `VideoResolution.Auto`, replace it with `BarcodeBatch.RecommendedCameraSettings` (see the 6→7 section). The deprecation is formal in 8.x.

### `BarcodeBatchLicenseInfo` is available from 8.4

If the user wants to inspect which symbologies the active license allows, this is available in 8.4+:

```csharp
var licensed = barcodeBatch.BarcodeBatchLicenseInfo?.LicensedSymbologies;
```

The value is populated after `IDataCaptureContextListener.OnModeAdded` fires. The property does not exist on 8.0–8.3 — gate any usage on the installed SDK version.

### `HandlerChanged` overlay pattern is still required

The pattern of creating `BarcodeBatchBasicOverlay.Create(barcodeBatch, style)` (and `BarcodeBatchAdvancedOverlay.Create(barcodeBatch)`) inside `dataCaptureView.HandlerChanged` (and attaching via `dataCaptureView.AddOverlay(overlay)`) is unchanged in v8. If a v6 / early-v7 codebase was creating the overlay in the constructor or `OnAppearing`, move it inside the `HandlerChanged` event handler.

### No other breaking BarcodeBatch changes

`BarcodeBatch.Create(context, settings)`, `BarcodeBatchSettings.Create()`, `IBarcodeBatchListener.OnSessionUpdated(BarcodeBatch, BarcodeBatchSession, IFrameData)`, the `SessionUpdated` event, `BarcodeBatchSession` properties (`AddedTrackedBarcodes`, `UpdatedTrackedBarcodes`, `RemovedTrackedBarcodes`, `TrackedBarcodes`), both overlays' factories, the `<scandit:DataCaptureView>` MAUI control, and the partial-class `ToPlatform` pattern for `BarcodeBatchAdvancedOverlay` are all unchanged in v8 for .NET MAUI.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild for each target framework (`net*-android` and `net*-ios`). Fix any remaining compile errors using the API references (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides for both underlying TFMs:
   - Android 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - Android 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
   - iOS 6 → 7: https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/
   - iOS 7 → 8: https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, and anything that required a judgment call (e.g., the `using` directive renames that the IDE may also auto-fix on save). Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeBatch API reference for the affected TFM (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html` or `https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html`) to find the correct API before guessing.
