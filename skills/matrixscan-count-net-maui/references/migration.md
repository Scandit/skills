# MatrixScan Count .NET MAUI Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="..." />` line (or any of the other three Scandit packages). All four packages — `Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui` — should be pinned to the **same** version. If they drift, treat the lowest as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.19 – 6.x | 7.x | Apply the **6 → 7 migration** below, then the 7 → 8 step if going all the way to 8.x |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 8.x | 8.x (newer) | No source changes needed — just bump the four `<PackageReference>` versions (Step 2) and rebuild |

> Note: `BarcodeCount` on `dotnet.android` / `dotnet.ios` has been available since **6.19**. If the user claims to be migrating an older version, ask them to confirm — `BarcodeCount` does not exist before 6.19.

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency versions

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest stable version. Then update the version in **all four** `<PackageReference>` entries:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Core.Maui`
- `Scandit.DataCapture.Barcode`
- `Scandit.DataCapture.Barcode.Maui`

Do **not** guess. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix).

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use MatrixScan Count (search for `BarcodeCount`, `BarcodeCountSettings`, `BarcodeCountView`, `BarcodeCountSession`, `BarcodeCountEventArgs`, `IBarcodeCountListener`, `BarcodeCountCaptureList`, `BarcodeCountFeedback`, `AddBarcodeCountView`) and apply the relevant changes below.

---

## Migration: 7 → 8 (MAUI)

The 7 → 8 step for .NET MAUI MatrixScan Count is **almost entirely a no-op at the source level**, and notably **simpler than the non-MAUI Android/iOS Count skills**.

### No manual SDK initialization to add (this is the key MAUI difference)

The non-MAUI `matrixscan-count-net-android` / `matrixscan-count-net-ios` skills require you to add `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` at process start for SDK 8.0+. **In MAUI you do not** — the `UseScanditCore()` / `UseScanditBarcode(c => c.AddBarcodeCountView())` builder extensions in `MauiProgram.cs` perform that initialization on 8.0+ themselves.

So during a MAUI 7 → 8 migration:
- **Do not** add `Initialize()` calls to `Platforms/Android/MainApplication.cs` or `Platforms/iOS/AppDelegate.cs`.
- **Do** confirm `MauiProgram.cs` has the builder chain `.UseScanditCore().UseScanditBarcode(configure => configure.AddBarcodeCountView())`. If the project predates the MAUI Count handler or used a different setup, ensure `AddBarcodeCountView()` is present inside the `UseScanditBarcode` lambda. (If the app was on 7.x it already had this chain — it has not changed in 8.0.)

### No other breaking BarcodeCount changes

These all stay the same in v8 — **do not "fix" code that already uses them**:

- `BarcodeCount.Create(dataCaptureContext, settings)` — still a static factory; there is no public `new BarcodeCount(...)`.
- `new BarcodeCountSettings()` and `settings.EnableSymbology(...)` / `settings.EnableSymbologies(...)`.
- The MAUI `<scandit:BarcodeCountView>` control and its bindable properties (`DataCaptureContext`, `BarcodeCount`, `ViewStyle`, the `ShouldShow*` toggles) — unchanged. The XAML namespace is still `clr-namespace:Scandit.DataCapture.Barcode.Count.UI.Maui;assembly=ScanditBarcodeCaptureMaui`.
- Subscribing to `ListButtonTapped` / `ExitButtonTapped` / `SingleScanButtonTapped` inside `HandlerChanged` — unchanged.
- `IBarcodeCountListener` — still the three-method interface (`OnScan`, `OnObservationStarted`, `OnObservationStopped`).
- The `barcodeCount.Scanned` event and `BarcodeCountEventArgs` shape (`BarcodeCount`, `Session`, `FrameData`).
- `BarcodeCountSession.RecognizedBarcodes` / `AdditionalBarcodes` / `GetSpatialMap()`.
- Camera handling: `Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings)`, `dataCaptureContext.SetFrameSourceAsync(camera)`, `camera.SwitchToDesiredStateAsync(...)`, and the `barcodeCount.Enabled` toggle — unchanged.
- Capture list: `BarcodeCountCaptureList.Create(listener, targets)`, `TargetBarcode.Create(data, quantity)`, `barcodeCount.SetBarcodeCountCaptureList(list)`.
- `BarcodeCountFeedback` — `new BarcodeCountFeedback()` (silent), `BarcodeCountFeedback.DefaultFeedback` (static property), `Success` / `Failure`.

So in practice a MAUI 7 → 8 BarcodeCount migration is: bump the four package versions (Step 2), rebuild, done. Review the official 7 → 8 guides for any cross-cutting Core changes unrelated to `BarcodeCount`.

---

## Migration: 6 → 7 (MAUI)

There are **no MatrixScan Count source-code breaking changes** specific to .NET MAUI in the 6 → 7 step — the `BarcodeCount` API surface above is the same. Bump the four `<PackageReference>` versions (Step 2) and rebuild. If the user is going from 6.x all the way to 8.x, also apply the 7 → 8 step above (which, for MAUI, is still essentially just the package bump). Review the official 6 → 7 guides for cross-cutting Core changes unrelated to `BarcodeCount`.

---

## Things that exist on other platforms but **not** in the .NET binding — do not introduce

Do not add these during a migration; they will not compile:

- **`BarcodeCountMappingFlowSettings`** / mapping-flow configuration — not surfaced in the .NET binding. Mapping is limited to `BarcodeCountSettings.MappingEnabled` + `BarcodeCountSession.GetSpatialMap()`.
- **`BarcodeCountSessionSnapshot`** — no .NET equivalent.

Also do not "port" the non-MAUI manual initialization into MAUI: adding `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` on top of the builder chain is redundant in MAUI and not what the official MAUI sample does.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - Android: [6 → 7](https://docs.scandit.com/sdks/net/android/migrate-6-to-7/) · [7 → 8](https://docs.scandit.com/sdks/net/android/migrate-7-to-8/)
   - iOS: [6 → 7](https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/) · [7 → 8](https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/)
3. Show the user a summary of only the changes actually made: which files were edited (usually just the `.csproj`), and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCount API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html` or the `dotnet.ios` equivalent) to find the correct API before guessing.
