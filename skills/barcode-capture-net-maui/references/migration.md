# BarcodeCapture .NET MAUI Migration Guide

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

> Note: Scandit's MAUI packages were not published on all `6.x` minor versions. If the project is on a `6.x` MAUI release, confirm with the user before assuming the BarcodeCapture MAUI API was identical to 7.x — fetch the MAUI changelog if in doubt.

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Core.Maui`
- `Scandit.DataCapture.Barcode`
- `Scandit.DataCapture.Barcode.Maui`

All four should move together. Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use BarcodeCapture (search for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `IBarcodeCaptureListener`, `BarcodeCaptureEventArgs`, `UseScanditBarcode`, `UseScanditCore`, `<scandit:DataCaptureView>`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for .NET MAUI BarcodeCapture has three things to handle: a camera setup update, a scan-intention behavioral change, and a composite-codes default change. Go through each section below and apply every change that matches the project.

### Camera setup — use `RecommendedCameraSettings`

Look for any of these patterns: `new CameraSettings()`, `VideoResolution.Auto`, `camera.ApplySettingsAsync(new CameraSettings(...))`. If found, replace the block with the recommended settings property.

**Before (v6 pattern — remove this):**

```csharp
var cameraSettings = new CameraSettings { PreferredResolution = VideoResolution.Auto };
var camera = Camera.GetCamera(CameraPosition.WorldFacing);
camera?.ApplySettingsAsync(cameraSettings);
```

**After (v7+ pattern — use this):**

```csharp
var camera = Camera.GetCamera(CameraPosition.WorldFacing);
camera?.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
```

Remove the `using` directive for `VideoResolution` once the reference is gone. If `BarcodeCapture.RecommendedCameraSettings` is already in use, skip this section.

> `BarcodeCapture.RecommendedCameraSettings` is a **static property**, not a method.

### Scan intention default change

The default scan intention is now `ScanIntention.Smart` from v7. Most projects need no action.

- If the project already explicitly sets `ScanIntention.Manual` (or another value) on `BarcodeCaptureSettings`, leave it.
- If the project uses a single-image frame source, you must set `settings.ScanIntention = ScanIntention.Manual` — Smart is incompatible with single-frame sources.
- If the property was not set, scanning now uses the Smart Scan algorithm by default. Inform the user but do not change the code.

### Composite codes default change

Default support for Composite Codes was removed when Smart Scan is enabled. If the project scans composite codes (CC-A, CC-B, CC-C), enable them explicitly using `CompositeType`:

```csharp
settings.EnableSymbologies(CompositeType.A | CompositeType.B);
settings.EnabledCompositeTypes = CompositeType.A | CompositeType.B;
```

If the project does not use composite codes, no action is needed.

### `BarcodeTracking` → `BarcodeBatch` rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch`. The API is otherwise unchanged.

### Builder chain — confirm both `UseScanditCore` and `UseScanditBarcode` are present

`UseScanditCore(c => c.AddDataCaptureView())` and `UseScanditBarcode()` are required from 7.x onwards. If the project's `MauiProgram.cs` only calls one of them (e.g. an older sample that bundled both registrations under `UseScanditBarcode`), add the missing call.

---

## Migration: 7 → 8

The 7→8 step for .NET MAUI BarcodeCapture is small. The factory methods (`BarcodeCapture.Create(context, settings)`), the `BarcodeScanned` event, the listener interface, and the `<scandit:DataCaptureView>` XAML control are unchanged.

### `VideoResolution.Auto` deprecated

If the project creates a `CameraSettings` with `VideoResolution.Auto`, replace it with `BarcodeCapture.RecommendedCameraSettings` (see the 6→7 section). The deprecation is formal in 8.x.

### `BarcodeCaptureLicenseInfo` is available from 8.4

If the project already inspects license info, no change is needed. If the user wants to start using it:

```csharp
var licensed = barcodeCapture.BarcodeCaptureLicenseInfo?.LicensedSymbologies;
```

The value is populated after `IDataCaptureContextListener.OnModeAdded` fires.

### `SelectionMode` introduced in 8.5

`BarcodeCaptureSettings.SelectionMode` (`SelectionMode.Off` / `On` / `Auto`) is the recommended replacement for the deprecated `ScanIntention.SmartSelection`. If the project does not use `SmartSelection`, no action is needed.

### `HandlerChanged` overlay pattern is still required

The pattern of creating `BarcodeCaptureOverlay.Create(barcodeCapture)` inside `dataCaptureView.HandlerChanged` (and attaching via `dataCaptureView.AddOverlay(overlay)`) is unchanged in v8. If a v6 / early-v7 codebase was creating the overlay in the constructor or `OnAppearing`, move it inside the `HandlerChanged` event handler.

### No other breaking BarcodeCapture changes

`BarcodeCapture.Create(context, settings)`, `IBarcodeCaptureListener`, `BarcodeScanned` / `SessionUpdated` events, `BarcodeCaptureSession`, `BarcodeCaptureOverlay.Create`, and the `<scandit:DataCaptureView>` MAUI control are all unchanged in v8.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild for each target framework (`net*-android` and `net*-ios`). Fix any remaining compile errors using the API references (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides for both underlying TFMs:
   - Android 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - Android 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
   - iOS 6 → 7: https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/
   - iOS 7 → 8: https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCapture API reference for the affected TFM (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html` or `https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html`) to find the correct API before guessing.
