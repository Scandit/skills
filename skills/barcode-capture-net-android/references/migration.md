# BarcodeCapture .NET for Android Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />` (or `Scandit.DataCapture.Core`) line.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x (`dotnet.android >= 6.16`) | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Barcode`

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use BarcodeCapture (search for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `IBarcodeCaptureListener`, `BarcodeCaptureEventArgs`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for .NET Android BarcodeCapture has three things to handle: a camera setup update, a scan-intention behavioral change, and a composite-codes default change. Go through each section below and apply every change that matches the project.

### Camera setup — use `RecommendedCameraSettings`

Look for any of these patterns: `new CameraSettings()`, `VideoResolution.Auto`, `camera.ApplySettingsAsync(new CameraSettings(...))`. If found, replace the block with the recommended settings property.

**Before (v6 pattern — remove this):**

```csharp
var cameraSettings = new CameraSettings { PreferredResolution = VideoResolution.Auto };
var camera = Camera.GetDefaultCamera();
camera?.ApplySettingsAsync(cameraSettings);
```

**After (v7+ pattern — use this):**

```csharp
var camera = Camera.GetDefaultCamera();
camera?.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
```

Remove the `using Scandit.DataCapture.Core.Source;` reference for `VideoResolution` after making the change. If `BarcodeCapture.RecommendedCameraSettings` is already in use, skip this section.

> Note: `BarcodeCapture.RecommendedCameraSettings` is a **static property**, not a method. The .NET binding has a `Camera.GetDefaultCamera(CameraSettings?)` overload, but the official .NET samples use the explicit two-step pattern (`GetDefaultCamera()` followed by `ApplySettingsAsync`) — prefer it for parity with Scandit's samples and for clarity.

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

---

## Migration: 7 → 8

The 7→8 step for .NET Android BarcodeCapture is mostly mechanical. The factory methods (`BarcodeCapture.Create(context, settings)`) and the listener / event surface are unchanged. The one **required** action is adding explicit SDK initialization at process start — without it, the app crashes on the first Scandit API call.

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

Make sure these `using` directives are present in the file:

```csharp
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;
```

**If `MainApplication.cs` does not exist** — create it next to `MainActivity.cs`. Android will refuse to load two `[Application]`-decorated classes, so do not add a second one.

```csharp
using Android.Runtime;
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;

namespace MyApp; // match the project's namespace

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

Symptom if this step is skipped: instant launch crash at the first `DataCaptureView.Create` / `BarcodeCapture.Create` call, because the DI container has no registrations.

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

### No other breaking BarcodeCapture changes

`BarcodeCapture.Create(context, settings)`, `IBarcodeCaptureListener`, `BarcodeScanned`/`SessionUpdated` events, `BarcodeCaptureSession`, and `BarcodeCaptureOverlay.Create` are all unchanged in v8 for .NET for Android.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html`) to find the correct API before guessing.
