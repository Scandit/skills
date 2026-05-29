# MatrixScan AR .NET MAUI Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit MAUI SDK the project currently has installed.

Check the `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="..." />` line (and the other three Scandit packages). All four packages should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 7.2 – 7.x | 8.x | Apply the **7 → 8 migration** below |
| 8.x | 8.x (newer) | No source changes needed — bump the four `<PackageReference>` versions (Step 2) and rebuild |

> Note: `BarcodeAr` first shipped on `dotnet.android` / `dotnet.ios` in **7.2**. There is no v6 → v7 migration to perform for `BarcodeAr` — anything older than 7.2 does not have the `BarcodeAr` API. If the user claims to be migrating "v6 BarcodeAr" code, ask them to confirm the version: they may be confusing `BarcodeAr` with the older `BarcodeTracking`/`BarcodeBatch` API (a *different* feature, covered by `matrixscan-batch-maui`).

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency versions

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Then update the SDK version in every Scandit `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Core.Maui`
- `Scandit.DataCapture.Barcode`
- `Scandit.DataCapture.Barcode.Maui`

Do **not** guess. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix).

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use MatrixScan AR (search for `BarcodeAr`, `BarcodeArSettings`, `BarcodeArView`, `BarcodeArSession`, `BarcodeArEventArgs`, `IBarcodeArListener`, `IBarcodeArHighlightProvider`, `IBarcodeArAnnotationProvider`, `BarcodeArFeedback`, `AddBarcodeArView`) and apply the relevant changes below.

---

## Migration: 7 → 8 (MAUI)

The 7 → 8 step for **MAUI** `BarcodeAr` is the smallest of all the platforms: the MAUI builder extensions (`UseScanditCore` / `UseScanditBarcode`) already handle SDK initialization, so **there is no manual `Initialize()` call to add** (unlike the non-MAUI `matrixscan-ar-net-android` / `matrixscan-ar-net-ios` skills, where v7 → v8 requires adding `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` to `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`). The MAUI builder calls these initializers for you.

If the project's `MauiProgram.cs` already calls `.UseScanditCore().UseScanditBarcode(c => c.AddBarcodeArView())`, you are done with the v7 → v8 migration on the source side — just bump the four package versions and rebuild.

### What MAUI users **do not** need to change in v7 → v8

These all stay the same — **do not "fix" code that already uses them**:

- `new BarcodeAr(dataCaptureContext, settings)` — still a plain constructor, no `Create(...)` / `ForDataCaptureContext(...)` factory exists in .NET.
- `new BarcodeArSettings()` and `settings.EnableSymbology(...)` / `settings.EnableSymbologies(...)`.
- The `<scandit:BarcodeArView>` XAML control and its bindable properties (`DataCaptureContext`, `BarcodeAr`, `BarcodeArViewSettings`, `CameraSettings`, `HighlightProvider`, `AnnotationProvider`, `ShouldShowTorchControl`, `ShouldShowZoomControl`, `ShouldShowCameraSwitchControl`, `TorchControlPosition`, `ZoomControlPosition`, `CameraSwitchControlPosition`).
- The MAUI builder chain `.UseScanditCore().UseScanditBarcode(c => c.AddBarcodeArView())`.
- `IBarcodeArListener.OnSessionUpdated(BarcodeAr, BarcodeArSession, IFrameData)` — still the single-method interface. There are still **no** `OnObservationStarted` / `OnObservationStopped` callbacks.
- The `barcodeAr.SessionUpdated` event and the `BarcodeArEventArgs` shape (`BarcodeAr`, `Session`, `FrameData`).
- `IBarcodeArHighlightProvider.HighlightForBarcodeAsync(Barcode)` → `Task<IBarcodeArHighlight?>` and `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync(Barcode)` → `Task<IBarcodeArAnnotation?>` — still async, still take only a `Barcode` (no `Context` / `UIView`).
- Highlight constructors: `new BarcodeArRectangleHighlight(barcode)`, `new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot)`.
- Annotation constructors: `new BarcodeArInfoAnnotation(barcode)`, `new BarcodeArStatusIconAnnotation(barcode)`, `new BarcodeArPopoverAnnotation(barcode, buttons)`.
- `BarcodeArFeedback` — `new BarcodeArFeedback()` (silent), `BarcodeArFeedback.DefaultFeedback` (static property), `Scanned` / `Tapped`.
- Lifecycle on `BarcodeArView` (MAUI): `OnAppearing` → `OnResume() + Start()`, `OnDisappearing` → `Stop() + OnPause()`. The `OnResume()` / `OnPause()` methods on the MAUI control still no-op on iOS (gated by `#if __ANDROID__` in the handler) — keep calling them for portability.
- The `HighlightForBarcodeTapped` event on the MAUI `BarcodeArView` is unchanged.

### Verify (don't add) the SDK initialization

If a previous developer manually added `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` to `Platforms/Android/MainApplication.cs` or `Platforms/iOS/AppDelegate.cs` (for example because they followed a non-MAUI .NET tutorial), the calls are **redundant** in MAUI — the builder extensions already call them. They are not harmful (`Initialize` is idempotent in 8.x), but you can clean them up to keep the platform shims unmodified.

The canonical MAUI platform shims look like this and should be left alone:

```csharp
// Platforms/Android/MainApplication.cs
using Android.App;
using Android.Runtime;

namespace MyApp;

[Application]
public class MainApplication(IntPtr handle, JniHandleOwnership ownership)
    : MauiApplication(handle, ownership)
{
    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
```

```csharp
// Platforms/iOS/AppDelegate.cs
using Foundation;

namespace MyApp;

[Register("AppDelegate")]
public class AppDelegate : MauiUIApplicationDelegate
{
    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
```

If `MauiProgram.cs` does not already include the BarcodeAr builder chain, add it now:

```csharp
.UseScanditCore()
.UseScanditBarcode(configure =>
{
    configure.AddBarcodeArView();
});
```

> If both `BarcodeBatch` and `BarcodeAr` coexist in the same MAUI app, the builder chain needs both `AddDataCaptureView()` (under `UseScanditCore`, for `BarcodeBatch`) and `AddBarcodeArView()` (under `UseScanditBarcode`, for `BarcodeAr`):
>
> ```csharp
> .UseScanditCore(c => c.AddDataCaptureView())
> .UseScanditBarcode(c => c.AddBarcodeArView());
> ```

### Optional v8 additions (mention only if asked)

- **`BarcodeArView.GetNotificationPresenter()`** (added in 8.5+) — returns the view's `INotificationPresenter` so callers can render notifications inside the AR view. Optional; pre-8.5 deployments do not have it. In MAUI, this only works once the handler has attached the native view — call it after `HandlerReady` fires.

### Things that exist on other platforms / TFMs but **not** on MAUI v8

Do not introduce these during the migration — they will not compile:

- **`SetBarcodeFilter(IBarcodeArFilter)`** — the Kotlin/Swift API added in 8.1 is not exposed on `dotnet.android` / `dotnet.ios` / MAUI. There is no `IBarcodeArFilter` interface in the .NET binding.
- **`ShouldShowMacroModeControl` / `MacroModeControlPosition`** on the MAUI `BarcodeArView` — these are iOS-only on the native binding and not surfaced as MAUI bindable properties. Do not migrate code that previously used them on a non-MAUI iOS app — there is no equivalent in the MAUI control.
- **`BarcodeArView.Create(parentView, barcodeAr, dataCaptureContext, viewSettings, cameraSettings)`** — the static factory exists on the per-TFM (`Scandit.DataCapture.Barcode.Ar.UI`) `BarcodeArView`, not on the MAUI `Scandit.DataCapture.Barcode.Ar.UI.Maui.BarcodeArView`. The MAUI control uses XAML + bindable properties, or constructors (`new BarcodeArView(context, barcodeAr, settings)` / `new BarcodeArView(context, barcodeAr, settings, cameraSettings)`).
- **`BarcodeArView.Dispose()`** — the MAUI `BarcodeArView` is a `Microsoft.Maui.Controls.View`, not `IDisposable` like the per-TFM one. Disposal is handled by the MAUI handler's `DisconnectHandler` (called by the framework on page teardown). Do not add explicit `Dispose()` calls.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - Android target: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
   - iOS target: https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited (likely just the `.csproj` for the version bump and possibly `MauiProgram.cs` if the builder chain was missing), which files were cleaned up (e.g. redundant `Initialize()` calls removed from `MainApplication.cs` / `AppDelegate.cs`), and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeAr API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html` or `dotnet.ios/...`) to find the correct API before guessing. The MAUI-specific surface (the XAML control, builder extension, and `HandlerReady` event) is documented in this skill's `references/integration.md`, not in the per-TFM API reference.
