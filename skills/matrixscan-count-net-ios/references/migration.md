# MatrixScan Count .NET for iOS Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />` (or `Scandit.DataCapture.Core`) line. Both packages should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.19 – 6.x | 7.x | Apply the **6 → 7 migration** below, then the 7 → 8 step if going all the way to 8.x |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 8.x | 8.x (newer) | No source changes needed — just bump the `<PackageReference>` versions (Step 2) and rebuild |

> Note: `BarcodeCount` on `dotnet.ios` has been available since **6.19**. If the user claims to be migrating an older version, ask them to confirm — `BarcodeCount` does not exist on `dotnet.ios` before 6.19.

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

Search for files that use MatrixScan Count (search for `BarcodeCount`, `BarcodeCountSettings`, `BarcodeCountView`, `BarcodeCountSession`, `BarcodeCountEventArgs`, `IBarcodeCountListener`, `BarcodeCountCaptureList`, `BarcodeCountFeedback`) and apply the relevant changes below.

---

## Migration: 7 → 8

The 7 → 8 step for .NET iOS MatrixScan Count is mostly mechanical. The `BarcodeCount.Create(...)` factory, the `BarcodeCountView.Create(...)` factory (with its `CGRect` frame argument), the listener / `Scanned` event surface, the session API, the camera handling, the capture-list APIs, and the feedback class are all **unchanged** in v8. The one **required** action is adding explicit SDK initialization at process start — without it, the app crashes on the first Scandit API call.

### Explicit SDK initialization is now required

Scandit 8.0 removed the implicit container bootstrap that 7.x performed automatically. The app must now call `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before any Scandit type is constructed. On iOS this belongs in `AppDelegate.FinishedLaunching` (`application:didFinishLaunchingWithOptions:`).

Open `AppDelegate.cs` and add the two `Initialize()` calls at the top of `FinishedLaunching` (before the root view controller / any Scandit usage):

```csharp
[Export("application:didFinishLaunchingWithOptions:")]
public bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
{
    ScanditCaptureCore.Initialize();
    ScanditBarcodeCapture.Initialize();

    // ... existing launch code stays below
    return true;
}
```

Make sure these `using` directives are present:

```csharp
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;
```

Symptom if this step is skipped: instant launch crash at the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeCount.Create(...)` call, because the DI container has no registrations.

### No other breaking BarcodeCount changes

These all stay the same in v8 — **do not "fix" code that already uses them**:

- `BarcodeCount.Create(dataCaptureContext, settings)` — still a static factory; there is no public `new BarcodeCount(...)` constructor.
- `new BarcodeCountSettings()` and `settings.EnableSymbology(...)` / `settings.EnableSymbologies(...)`.
- `BarcodeCountView.Create(frame, dataCaptureContext, barcodeCount[, BarcodeCountViewStyle])` — same factory; first argument is still a `CGRect` frame. The view is still a `UIView` you add with `View.AddSubview(...)`.
- `IBarcodeCountListener` — still the three-method interface (`OnScan`, `OnObservationStarted`, `OnObservationStopped`).
- The `barcodeCount.Scanned` event and the `BarcodeCountEventArgs` shape (`BarcodeCount`, `Session`, `FrameData`).
- `BarcodeCountSession.RecognizedBarcodes` / `AdditionalBarcodes` / `GetSpatialMap()`.
- Camera handling: `Camera.GetDefaultCamera()`, `camera.ApplySettingsAsync(BarcodeCount.RecommendedCameraSettings)`, `dataCaptureContext.SetFrameSourceAsync(camera)`, `camera.SwitchToDesiredStateAsync(...)` — unchanged. `barcodeCount.Enabled` toggle — unchanged.
- Capture list: `BarcodeCountCaptureList.Create(listener, targets)`, `TargetBarcode.Create(data, quantity)`, `barcodeCount.SetBarcodeCountCaptureList(list)`.
- `BarcodeCountFeedback` — `new BarcodeCountFeedback()` (silent), `BarcodeCountFeedback.DefaultFeedback` (static property), `Success` / `Failure`.
- iOS-only view APIs (`HardwareTriggerEnabled`, `PrepareScanning`/`StopScanning`, `*AccessibilityLabel`/`*AccessibilityHint`) — unchanged.

---

## Migration: 6 → 7

There are **no MatrixScan Count source-code breaking changes** specific to .NET iOS in the 6 → 7 step — the `BarcodeCount` API surface above is the same. Bump the `<PackageReference>` versions (Step 2) and rebuild. (Explicit initialization is only required from 8.0 onward — do not add `Initialize()` calls when targeting 7.x.) If the user is going from 6.x all the way to 8.x, also apply the 7 → 8 step above.

Review the official 6 → 7 guide for any cross-cutting Core changes unrelated to `BarcodeCount`.

---

## Things that exist on other platforms but **not** on `dotnet.ios` — do not introduce

Do not add these during a migration; they will not compile:

- **`BarcodeCountMappingFlowSettings`** / mapping-flow configuration — not surfaced in the .NET binding. Mapping is limited to `BarcodeCountSettings.MappingEnabled` + `BarcodeCountSession.GetSpatialMap()`.
- **`BarcodeCountSessionSnapshot`** — no .NET equivalent.
- **`EnableHardwareTrigger(int? keyCode)` / `HardwareTriggerSupported`** (Android-only) — on iOS use the `barcodeCountView.HardwareTriggerEnabled` `bool` property instead.
- **`IBarcodeCountViewListener.OnCaptureListCompleted(view)`** (Android-only) — not part of the iOS listener interface.
- **`*ContentDescription`** accessibility properties (Android-only) — on iOS use `*AccessibilityLabel` / `*AccessibilityHint`.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited (e.g. `AppDelegate.cs`), and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCount API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html`) to find the correct API before guessing.
