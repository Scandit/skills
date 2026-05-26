# MatrixScan Batch .NET for Android Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />` (or `Scandit.DataCapture.Core`) line. Both packages should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x (`dotnet.android >= 6.16`) | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version, ask the user which version they are migrating from.

> Note: MatrixScan Batch on `dotnet.android` was first published in 6.16 (a brief window during the 6 line where the class was still named `BarcodeTracking`). The cross-platform rename to `BarcodeBatch` landed at 7.0. Anything older than 6.16 does not have this API on `dotnet.android` — confirm with the user before assuming a version below 6.16.

---

## Step 2: Update the dependency version

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest stable version. Then update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Barcode`

Do **not** guess. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix).

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use MatrixScan Batch (search for `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchSession`, `BarcodeBatchEventArgs`, `IBarcodeBatchListener`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, and also the v6 names `BarcodeTracking`, `BarcodeTrackingSettings`, `BarcodeTrackingSession`, `IBarcodeTrackingListener`, `BarcodeTrackingBasicOverlay`, `BarcodeTrackingAdvancedOverlay`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for .NET Android MatrixScan Batch is primarily about the cross-platform `BarcodeTracking` → `BarcodeBatch` rename and the new namespace under `Batch.*`. Go through every section below and apply each change that matches the project.

### `BarcodeTracking` → `BarcodeBatch` rename

The class family was renamed at v7.0 across all platforms (Android, iOS, .NET, Flutter, etc.). Apply this rename everywhere the old names appear:

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

Method names that include `BarcodeTracking` in the parameter name (e.g. `OnObservationStarted(BarcodeTracking barcodeTracking)`) become `OnObservationStarted(BarcodeBatch barcodeBatch)` etc. Update the parameter type and parameter name to match.

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
var camera = Camera.GetDefaultCamera();
camera?.ApplySettingsAsync(cameraSettings);
```

**After (v7+ pattern):**

```csharp
var camera = Camera.GetDefaultCamera();
camera?.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
```

If a specific resolution (e.g. `VideoResolution.FullHd`) is required, fetch the recommended settings first and then override only what you need:

```csharp
var cameraSettings = BarcodeBatch.RecommendedCameraSettings;
cameraSettings.PreferredResolution = VideoResolution.FullHd;
this.camera.ApplySettingsAsync(cameraSettings);
```

`BarcodeBatch.RecommendedCameraSettings` is a **static property**, not a method. The Kotlin form `createRecommendedCameraSettings()` does not exist in the .NET binding.

### Factory rename: nothing to change

`BarcodeBatch.Create(context, settings)` was the .NET factory in v6 (as `BarcodeTracking.Create(context, settings)`) and continues to be the factory in v7+. There is **no** rename from `Create(...)` to `ForDataCaptureContext(...)` — the .NET binding has always exposed `Create`. If the codebase already uses `BarcodeTracking.Create(...)`, the only change is renaming `BarcodeTracking` → `BarcodeBatch` (covered above).

### New v7 APIs (optional, mention only if asked)

- `BarcodeBatchBasicOverlayStyle.Dot` — an alternative to the default `Frame` style. Pass it to `BarcodeBatchBasicOverlay.Create(barcodeBatch, dataCaptureView, BarcodeBatchBasicOverlayStyle.Dot)`.

---

## Migration: 7 → 8

The 7→8 step for .NET Android MatrixScan Batch is mostly mechanical. The factory methods (`BarcodeBatch.Create(context, settings)` and the overlay `Create(...)` overloads), the listener / event surface, the session API, and the tracked-barcode model are all unchanged. The one **required** action is adding explicit SDK initialization at process start — without it, the app crashes on the first Scandit API call.

### Explicit SDK initialization is now required

Scandit 8.0 removed the implicit container bootstrap that 6.x/7.x performed automatically. The app must now call `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before any Scandit type is constructed.

Check whether the project already has an `Application` subclass (look for `[Application]` on a class deriving from `Android.App.Application`, typically in `MainApplication.cs`).

**If `MainApplication.cs` exists** — add the two `Initialize()` calls at the top of its `OnCreate()` (after `base.OnCreate()`):

```csharp
public override void OnCreate()
{
    base.OnCreate();
    ScanditCaptureCore.Initialize();
    ScanditBarcodeCapture.Initialize();
    // ... existing init code stays below
}
```

Make sure these `using` directives are present:

```csharp
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;
```

**If `MainApplication.cs` does not exist** — create it next to `MainActivity.cs`. Android will refuse to load two `[Application]`-decorated classes, so do not add a second one.

```csharp
using Android.Runtime;
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;

namespace MyApp;

[Application]
public class MainApplication(IntPtr handle, JniHandleOwnership ownership)
    : Application(handle, ownership)
{
    public override void OnCreate()
    {
        base.OnCreate();
        ScanditCaptureCore.Initialize();
        ScanditBarcodeCapture.Initialize();
    }
}
```

Symptom if this step is skipped: instant launch crash at the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeBatch.Create(...)` / `DataCaptureView.Create(...)` call, because the DI container has no registrations.

### `BarcodeBatchLicenseInfo` introduced in 8.4

If the user wants to inspect which symbologies the active license allows, this is available in 8.4+:

```csharp
// Hook IDataCaptureContextListener and wait for OnModeAdded before reading the property.
BarcodeBatchLicenseInfo? info = this.barcodeBatch.BarcodeBatchLicenseInfo;
ICollection<Symbology>? licensed = info?.LicensedSymbologies;
```

The property does not exist on `dotnet.android` 8.0–8.3 — gate any usage on the installed SDK version.

### No other breaking BarcodeBatch changes

`BarcodeBatch.Create(context, settings)`, `BarcodeBatchSettings.Create()`, `IBarcodeBatchListener.OnSessionUpdated(BarcodeBatch, BarcodeBatchSession, IFrameData)`, the `SessionUpdated` event, the `BarcodeBatchSession` properties (`AddedTrackedBarcodes`, `UpdatedTrackedBarcodes`, `RemovedTrackedBarcodes`, `TrackedBarcodes`), and both overlays (`BarcodeBatchBasicOverlay.Create(...)`, `BarcodeBatchAdvancedOverlay.Create(...)`) are all unchanged in v8 for .NET for Android.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, and anything that required a judgment call (e.g., the `using` directive renames that the IDE may also auto-fix on save). Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeBatch API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html`) to find the correct API before guessing.
