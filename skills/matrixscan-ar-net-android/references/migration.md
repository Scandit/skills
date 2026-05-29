# MatrixScan AR .NET for Android Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />` (or `Scandit.DataCapture.Core`) line. Both packages should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 7.2 – 7.x | 8.x | Apply the **7 → 8 migration** below |
| 8.x | 8.x (newer) | No source changes needed — just bump the `<PackageReference>` versions (Step 2) and rebuild |

> Note: `BarcodeAr` on `dotnet.android` was **first shipped in 7.2**. There is no v6 → v7 migration to perform — anything older than 7.2 does not have the `BarcodeAr` API on `dotnet.android` at all. If the user claims to be migrating "v6 BarcodeAr" code, ask them to confirm the version: they may be confusing `BarcodeAr` with the older `BarcodeTracking`/`BarcodeBatch` API (which is a *different* feature and a different skill — `matrixscan-batch-net-android`).

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest stable version. Then update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Barcode`

Do **not** guess. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix).

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use MatrixScan AR (search for `BarcodeAr`, `BarcodeArSettings`, `BarcodeArView`, `BarcodeArSession`, `BarcodeArEventArgs`, `IBarcodeArListener`, `IBarcodeArHighlightProvider`, `IBarcodeArAnnotationProvider`, `BarcodeArFeedback`) and apply the relevant changes below.

---

## Migration: 7 → 8

The 7 → 8 step for .NET Android MatrixScan AR is mostly mechanical. The `BarcodeAr` factory pattern (`new BarcodeAr(context, settings)`), the `BarcodeArView.Create(...)` factory, the listener / event surface, the session API, the provider interfaces (`IBarcodeArHighlightProvider.HighlightForBarcodeAsync`, `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync`), and the highlight / annotation constructors are all **unchanged** in v8. The one **required** action is adding explicit SDK initialization at process start — without it, the app crashes on the first Scandit API call.

### Explicit SDK initialization is now required

Scandit 8.0 removed the implicit container bootstrap that 7.x performed automatically. The app must now call `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before any Scandit type is constructed.

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

Symptom if this step is skipped: instant launch crash at the first `DataCaptureContext.ForLicenseKey(...)` / `new BarcodeAr(...)` / `BarcodeArView.Create(...)` call, because the DI container has no registrations.

### No other breaking BarcodeAr changes

These all stay the same in v8 — **do not "fix" code that already uses them**:

- `new BarcodeAr(dataCaptureContext, settings)` — still a plain constructor, no `Create(...)` / `ForDataCaptureContext(...)` factory exists in .NET.
- `new BarcodeArSettings()` and `settings.EnableSymbology(...)` / `settings.EnableSymbologies(...)`.
- `BarcodeArView.Create(parentView, barcodeAr, dataCaptureContext, viewSettings, cameraSettings)` — same factory, same five arguments. `cameraSettings` is still nullable (pass `null` to use `BarcodeAr.RecommendedCameraSettings`).
- `IBarcodeArListener.OnSessionUpdated(BarcodeAr, BarcodeArSession, IFrameData)` — still the single-method interface. There are still **no** `OnObservationStarted` / `OnObservationStopped` callbacks.
- The `barcodeAr.SessionUpdated` event and the `BarcodeArEventArgs` shape (`BarcodeAr`, `Session`, `FrameData`).
- `IBarcodeArHighlightProvider.HighlightForBarcodeAsync(Barcode)` → `Task<IBarcodeArHighlight?>` and `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync(Barcode)` → `Task<IBarcodeArAnnotation?>` — still async, still take only a `Barcode` (no `Context`).
- Highlight constructors: `new BarcodeArRectangleHighlight(barcode)`, `new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot)`.
- Annotation constructors: `new BarcodeArInfoAnnotation(barcode)`, `new BarcodeArStatusIconAnnotation(barcode)`, `new BarcodeArPopoverAnnotation(barcode, buttons)`.
- `BarcodeArFeedback` — `new BarcodeArFeedback()` (silent), `BarcodeArFeedback.DefaultFeedback` (static property), `Scanned` / `Tapped`.
- Lifecycle on `BarcodeArView`: `OnResume()` / `OnPause()` / `Pause()` / `Start()` / `Stop()` / `Reset()` / `Dispose()`. `OnDestroy()` still does **not** exist on `BarcodeArView` — keep using `Dispose()`.
- The `HighlightForBarcodeTapped` event on `BarcodeArView` is unchanged.

### Optional v8 additions (mention only if asked)

- **`BarcodeArView.GetNotificationPresenter()`** (added in 8.5+) — returns the view's `IBarcodeArNotificationPresenter` so callers can swap in a custom presenter for user-facing notifications. Optional; pre-8.5 deployments do not have it.

### Things that exist on other platforms but **not** on `dotnet.android` v8

Do not introduce these during the migration — they will not compile:

- **`SetBarcodeFilter(IBarcodeArFilter)`** — the Kotlin/iOS API added in 8.1 is not exposed on `dotnet.android`. There is no `IBarcodeArFilter` interface in the .NET binding.
- **`BarcodeArCoordinatorLayout`** — that container is SparkScan-specific. `BarcodeArView` attaches itself directly to whatever `ViewGroup` is passed to `BarcodeArView.Create(parentView, ...)`.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guide:
   - 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which files were created (e.g. `MainApplication.cs`), and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeAr API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html`) to find the correct API before guessing.
