# MatrixScan Count (.NET for Android) Integration Guide

`BarcodeCount` is the multi-barcode counting mode, designed for high-volume scanning such as inventory and receiving. It scans every barcode in the camera feed during a scan phase, then reports them all at once when the user triggers the scan. `BarcodeCountView` provides the full built-in AR counting UI (camera preview, shutter, list/exit buttons, on-screen highlights and hints).

Unlike MatrixScan AR (`BarcodeAr`), **`BarcodeCount` does not manage its own camera** — you create a `Camera`, set it as the context's frame source, and switch it on/off across the lifecycle yourself. And unlike `BarcodeArView`, **`BarcodeCountView` is a real Android `View` that you add to the layout yourself** with `container.AddView(...)`.

Examples below use C# and an `AppCompatActivity`. The same APIs work in a Fragment — adapt ownership of `DataCaptureContext`, `Camera`, `BarcodeCount`, and `BarcodeCountView` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts `BarcodeCountView` as a XAML element and wires it through `HandlerChanged`, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeCount` has been available on `dotnet.android` since **6.19**, so any current stable release supports it.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add both packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- `Xamarin.AndroidX.AppCompat` — required because the `CameraPermissionActivity` helper inherits from `AppCompatActivity`. The `dotnet new android` template already pulls it in transitively; for manually scaffolded projects add it explicitly:
  ```xml
  <PackageReference Include="Xamarin.AndroidX.AppCompat" Version="<latest-version-with-xamarin-suffix>" />
  ```
  **When fetching the latest version, pick the highest available including any Xamarin-revision suffix — e.g. `1.7.0.5`, not bare `1.7.0`.** The `.X` suffix marks Xamarin-binding patch revisions and carries critical transitive-dep updates.
- **`Theme.AppCompat` descendant required on the activity.** Because the activity inherits from `AppCompatActivity`, its theme must be a `Theme.AppCompat` descendant or `SetContentView` crashes at launch with `IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity`. The official sample sets `android:theme="@style/AppTheme"` (an AppCompat descendant) on `<application>` in the manifest. Alternatively set it on the `[Activity]` attribute:
  ```csharp
  [Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
  ```
- **`SupportedOSPlatformVersion` must be at least `24`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>
  ```
  Lower values fail the build because Scandit's Android AAR has `minSdkVersion=24`.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. Without this, the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeCount.Create(...)` call crashes because the container has no registrations.

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

  If the project already has an `Application` subclass, add the two `Initialize()` calls to its existing `OnCreate()` rather than creating a second one (Android will refuse to load two `[Application]`-decorated classes). **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip this file entirely.**
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- `AndroidManifest.xml` setup — two concerns:

  1. **Camera entries** (top-level, sibling to `<application>`):
     ```xml
     <uses-feature android:name="android.hardware.camera" android:required="true" />
     <uses-permission android:name="android.permission.CAMERA" />
     ```

  2. **Do not add `<activity>` declarations** for `MainActivity` (or any other `[Activity]`-decorated class). The attribute is the canonical registration in .NET for Android; a manual `<activity android:name=".MainActivity">` resolves against `<ApplicationId>` and won't match the generated class, producing `ClassNotFoundException` at launch.

  Request the camera permission at runtime using `RequestPermissions` before scanning starts (Android API 23+). The `CameraPermissionActivity` helper at the bottom of this guide encapsulates that flow.

### Project scaffolding (new projects only)

If a .NET Android project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add `BarcodeCount` on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

Add the Scandit and `Xamarin.AndroidX.AppCompat` packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `24.0`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as every extra symbology adds processing overhead.

Once the user responds, ask which Activity (or Fragment) they'd like to integrate `BarcodeCount` into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** — do not guess).
2. Ensure `<SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
4. Request the `CAMERA` permission at runtime before scanning starts (the `CameraPermissionActivity` helper below).
5. Create `MainApplication.cs` with `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` (SDK 8.0+).
6. Ensure the activity uses a `Theme.AppCompat` descendant (manifest `<application android:theme=...>` or the `[Activity]` `Theme=` attribute).
7. Provide a layout with a container (e.g. a `FrameLayout`) for the `BarcodeCountView`, or host it in a full-screen `FrameLayout` created in code.
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

this.dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure BarcodeCountSettings

Choose which barcode symbologies to count. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need.

`BarcodeCountSettings` is constructed with a plain `new` (it is the `BarcodeCount` *mode* that uses a factory, not the settings).

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;

BarcodeCountSettings settings = new BarcodeCountSettings();

HashSet<Symbology> symbologies = new()
{
    Symbology.Ean13Upca,
    Symbology.Ean8,
    Symbology.Code128,
};
settings.EnableSymbologies(symbologies);

// Optional: if the environment guarantees no duplicate barcode values, this speeds up scanning.
settings.ExpectsOnlyUniqueBarcodes = true;
```

`ExpectsOnlyUniqueBarcodes` (default `false`) tells the engine each barcode value appears at most once in the scene, so it can stop re-evaluating a value once counted. Leave it `false` if the same barcode can legitimately appear multiple times.

### Filtering (scan only some of the barcodes on a label)

When a label carries several barcodes and you only want to count some of them, filter the rest out through `settings.FilterSettings` (a `BarcodeFilterSettings`, exposed read-only on `BarcodeCountSettings`). Filtering is by symbology, by symbol count, or by a regex on the barcode data. Filtered barcodes are still detected but are covered by a highlight and excluded from the count.

```csharp
using Scandit.DataCapture.Barcode.Data;

BarcodeCountSettings settings = new BarcodeCountSettings();
settings.EnableSymbologies(enabledSymbologies);

// Exclude an entire symbology (e.g. count Code 128 but never PDF417):
settings.FilterSettings.ExcludedSymbologies = new HashSet<Symbology> { Symbology.Pdf417 };

// Or exclude by a regex matched against the barcode data (e.g. anything starting with 1234):
settings.FilterSettings.ExcludedCodesRegex = "^1234.*";
```

| `BarcodeFilterSettings` member | Type | Description |
|--------|------|-------------|
| `ExcludedSymbologies` | `ISet<Symbology>` (get/set) | Symbologies to filter out. Has no effect on a symbology that isn't also enabled on the mode. |
| `ExcludedCodesRegex` | `string` (get/set) | Regex matched against each barcode's data; matching barcodes are filtered out. |
| `ExcludedSymbolCounts` | `IDictionary<Symbology, ISet<int>>` (get/set) | Filter by symbol count per symbology. |
| `SetExcludedSymbolCounts(IList<short>, Symbology)` / `GetExcludedSymbolCountsForSymbology(Symbology)` | methods | Per-symbology symbol-count filtering. |

By default the filtered barcodes are covered by a transparent layer. To change that highlight's color/transparency, set the **view's** `FilterSettings` property (distinct from `BarcodeCountSettings.FilterSettings`, which holds the filter *rules* above — this one holds the filter *highlight*). On .NET the highlight type is the **`IBarcodeFilterHighlightSettings` interface** (the cross-platform name `BarcodeFilterHighlightSettings` is exposed as this interface), implemented by `BarcodeFilterHighlightSettingsBrush`:

```csharp
using Scandit.DataCapture.Barcode.Filter.UI;
using Scandit.DataCapture.Core.UI.Style;

this.barcodeCountView.FilterSettings =
    BarcodeFilterHighlightSettingsBrush.Create(new Brush(fillColor, strokeColor, strokeWidth));
```

### BarcodeCountSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new BarcodeCountSettings()` | constructor | All symbologies disabled. |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `GetSymbologySettings(Symbology)` | method | Per-symbology `SymbologySettings` (`ActiveSymbolCounts`, checksum config, etc.). |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `ExpectsOnlyUniqueBarcodes` | `bool` (get/set) | When `true`, assumes each barcode appears once and optimizes accordingly. |
| `DisableModeWhenCaptureListCompleted` | `bool` (get/set) | When using a capture list, auto-disable the mode once the list is complete. |
| `MappingEnabled` | `bool` (get/set) | Enables the spatial map (`session.GetSpatialMap()`). |
| `FilterSettings` | `BarcodeFilterSettings` (get) | Per-symbology filtering configuration. |
| `SetProperty` / `GetProperty` / `GetProperty<T>` / `TryGetProperty<T>` | methods | Read/write experimental engine flags. |

## Step 3 — Create the BarcodeCount mode

`BarcodeCount` is created with a **static factory** that attaches the mode to the context. There is **no** public `new BarcodeCount(...)` constructor.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;

this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);
```

There is also a `BarcodeCount.Create(settings)` overload that creates the mode without a context (you would attach it to a context later); for a normal integration use the two-argument form above.

### BarcodeCount members

| Member | Description |
|--------|-------------|
| `static BarcodeCount Create(DataCaptureContext? context, BarcodeCountSettings settings)` | Factory — creates the mode and attaches it to the context. |
| `static BarcodeCount Create(BarcodeCountSettings settings)` | Factory — creates the mode without a context. |
| `Context` | `DataCaptureContext?` (get). |
| `Feedback` | `BarcodeCountFeedback` (get/set) — sound / vibration. See Optional configuration. |
| `Enabled` | `bool` (get/set) — **set `true` to process frames.** Toggle in `OnResume`/`OnPause`. |
| `static CameraSettings RecommendedCameraSettings` | Recommended camera settings for counting. |
| `ApplySettingsAsync(BarcodeCountSettings)` | `Task` — applies new settings. |
| `AddListener(IBarcodeCountListener)` / `RemoveListener(...)` | Register/remove a listener. |
| `event EventHandler<BarcodeCountEventArgs> Scanned` | Raised when a scan phase finishes. Corresponds to `IBarcodeCountListener.OnScan`. **Recommended** in idiomatic C#. |
| `Reset()` | Clear all counted barcodes and AR overlays for a fresh scanning process. |
| `StartScanningPhase()` / `EndScanningPhase()` | Manually delimit a scanning phase (advanced; the view's shutter normally drives this). |
| `SetBarcodeCountCaptureList(BarcodeCountCaptureList)` | Apply a capture/receiving list (see that section). |
| `SetAdditionalBarcodes(IList<Barcode>)` / `ClearAdditionalBarcodes()` | Seed/clear barcodes that should be considered already counted (e.g. restored across backgrounding). |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the `Scanned` event — not both for the same handler.** They both deliver the scan result; subscribing to both double-processes.

## Step 4 — Set up the camera (you manage it; the view does not)

This is the key difference from MatrixScan AR. Get the default camera with the recommended settings and set it as the context's frame source. Keep a reference so you can switch it on/off across the lifecycle.

```csharp
using Scandit.DataCapture.Core.Source;

CameraSettings cameraSettings = BarcodeCount.RecommendedCameraSettings;
this.camera = Camera.GetDefaultCamera(cameraSettings);
if (this.camera is null)
{
    throw new InvalidOperationException("MatrixScan Count requires a camera.");
}

await this.dataCaptureContext.SetFrameSourceAsync(this.camera);
```

The camera is off by default. You turn it on in `OnResume` and off in `OnPause` (Step 7). Do **not** look for `barcodeCountView.OnResume()`/`Start()` — those don't exist; the camera is the lifecycle handle.

## Step 5 — Create and add the BarcodeCountView

`BarcodeCountView.Create` takes the Android **`Context`** (the activity), the `DataCaptureContext`, the `BarcodeCount` mode, and optionally a `BarcodeCountViewStyle`. The returned view **is** an Android `View` (implicit conversion), so add it to your layout with `AddView`.

```csharp
using Scandit.DataCapture.Barcode.Count.UI;
using Android.Widget;

this.barcodeCountView = BarcodeCountView.Create(
    this,                       // Android Context
    this.dataCaptureContext,
    this.barcodeCount,
    BarcodeCountViewStyle.Icon); // or BarcodeCountViewStyle.Dot

// Add it to a container from your XML layout...
FrameLayout container = this.FindViewById<FrameLayout>(Resource.Id.data_capture_view_container)!;
container.AddView(this.barcodeCountView);

// ...or host it full-screen in a FrameLayout created in code:
// var container = new FrameLayout(this);
// this.SetContentView(container);
// container.AddView(this.barcodeCountView);
```

`BarcodeCountViewStyle` is `Icon` (counted barcodes show a check-mark icon) or `Dot` (a dot). Use the three-argument `Create` overload to accept the default style.

### Common BarcodeCountView members

| Member | Description |
|--------|-------------|
| `static Create(Context, DataCaptureContext, BarcodeCount)` / `Create(Context, DataCaptureContext, BarcodeCount, BarcodeCountViewStyle)` | Factory. First arg is the Android `Context`, not a parent view. |
| `implicit operator View(BarcodeCountView)` | Lets you pass the view straight to `container.AddView(...)`. |
| `Style` | `BarcodeCountViewStyle` (get). |
| `Listener` | `IBarcodeCountViewListener?` (get/set) — custom brushes + tap callbacks. |
| `ShouldShowListButton` / `ShouldShowExitButton` / `ShouldShowShutterButton` / `ShouldShowFloatingShutterButton` / `ShouldShowSingleScanButton` / `ShouldShowClearHighlightsButton` / `ShouldShowStatusModeButton` / `ShouldShowUserGuidanceView` / `ShouldShowHints` / `ShouldShowToolbar` / `ShouldShowScanAreaGuides` / `ShouldShowListProgressBar` / `ShouldShowTorchControl` | `bool` toggles for the built-in UI. |
| `ShouldDisableModeOnExitButtonTapped` | `bool`. |
| `TapToUncountEnabled` | `bool`. |
| `TorchControlPosition` | `Anchor`. |
| `RecognizedBrush` / `NotInListBrush` / `AcceptedBrush` / `RejectedBrush` | `Brush?` (get/set) overlay styles; static `Default*Brush` provide the defaults. |
| `BarcodeNotInListActionSettings` | `BarcodeCountNotInListActionSettings` (get) — see that section. |
| `EnableHardwareTrigger(int? keyCode)` / static `HardwareTriggerSupported` | Android hardware-trigger support. |
| `SetToolbarSettings(BarcodeCountToolbarSettings)` | Customize toolbar button text. |
| `SetStatusProvider(IBarcodeCountStatusProvider)` | Enable status mode (see that section). |
| `ClearHighlights()` | Clear current on-screen highlights. |
| `SetBrushForRecognizedBarcode` / `*NotInList` / `*Accepted` / `*Rejected` `(TrackedBarcode, Brush?)` | Per-barcode brush override. |
| `event ExitButtonTapped` / `ListButtonTapped` / `SingleScanButtonTapped` | Toolbar button taps. See Step 8. |
| `Dispose()` | Releases native resources. Call from `OnDestroy`. |

## Step 6 — Handle scan results

`Scanned` (equivalently `IBarcodeCountListener.OnScan`) fires when a scan phase finishes. It runs on a **background thread**, and the `BarcodeCountSession` is only valid inside the callback — copy out the barcodes you need immediately.

The recommended idiomatic C# pattern is the event:

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;

// After creating barcodeCount (or in OnResume — see lifecycle note in Step 7):
this.barcodeCount.Scanned += this.OnBarcodeCountScanned;

private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
{
    // Copy the recognized barcodes out of the session right away.
    List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
    List<Barcode> additional = args.Session.AdditionalBarcodes.ToList();

    this.RunOnUiThread(() =>
    {
        foreach (Barcode barcode in recognized)
        {
            // barcode.Data, barcode.Symbology
        }
    });
}
```

If you prefer the listener interface, implement `IBarcodeCountListener` — note it has **three** methods:

```csharp
using Scandit.DataCapture.Core.Data;

public class MainActivity : CameraPermissionActivity, IBarcodeCountListener
{
    public void OnScan(BarcodeCount mode, BarcodeCountSession session, IFrameData data)
    {
        List<Barcode> recognized = session.RecognizedBarcodes.ToList();
        this.RunOnUiThread(() => /* update UI */);
    }

    public void OnObservationStarted(BarcodeCount mode) { }
    public void OnObservationStopped(BarcodeCount mode) { }
}

// In setup:
this.barcodeCount.AddListener(this);
```

### BarcodeCountSession members

| Member | Type | Description |
|--------|------|-------------|
| `RecognizedBarcodes` | `IList<Barcode>` | All barcodes counted in this scan phase. |
| `AdditionalBarcodes` | `IList<Barcode>` | Barcodes added via `SetAdditionalBarcodes` (e.g. restored across backgrounding). |
| `FrameSequenceId` | `long` | Identifier of the underlying frame sequence. |
| `Reset()` | method | Reset all session state. Only call from inside the callback. |
| `GetSpatialMap()` / `GetSpatialMap(int rows, int cols)` | `BarcodeSpatialGrid?` | The spatial layout of counted barcodes (requires `settings.MappingEnabled = true`). |

### Storing scanned barcodes across the results screen

Because the session is not accessible outside `OnScan`, store the barcodes if you need them later (e.g. to show a results list when the user taps the List or Exit button). A common pattern is to keep them in a shared manager and, when the app goes to background, persist the current barcodes as *additional* barcodes so the count survives:

```csharp
// When leaving for a results screen, or going to background:
this.barcodeCount.SetAdditionalBarcodes(savedBarcodes);

// To start a brand-new counting process:
this.barcodeCount.ClearAdditionalBarcodes();
this.barcodeCount.Reset();
```

## Step 7 — Camera permission and lifecycle

Toggle the camera and the mode across the activity lifecycle. The camera — not the view — is the lifecycle handle.

```csharp
using Scandit.DataCapture.Core.Source;

protected override void OnResume()
{
    base.OnResume();

    // (Re)subscribe and enable the mode so frames are processed.
    this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
    this.barcodeCount.Enabled = true;

    // Request camera permission; the camera is turned on once granted.
    this.RequestCameraPermission();
}

protected override void OnPause()
{
    base.OnPause();
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
}

protected override void OnCameraPermissionGranted()
{
    // Permission granted (or already held) — turn the camera on.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

protected override void OnDestroy()
{
    base.OnDestroy();
    this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
    this.barcodeCountView.Dispose();
    this.barcodeCount.Dispose();
}
```

> If you navigate to a results screen *within* the app and want to keep the count, avoid turning the camera off and avoid resetting — only pause the frame source when actually backgrounding. The official sample tracks a `navigatingInternally` flag for exactly this.

## Step 8 — List / Exit / Single-Scan button taps

The built-in toolbar buttons are surfaced as C# events on `BarcodeCountView`. Subscribe to react when the user taps them:

```csharp
this.barcodeCountView.ListButtonTapped += (sender, args) =>
{
    // Show the current scan results (order not yet complete).
};

this.barcodeCountView.ExitButtonTapped += (sender, args) =>
{
    // The user finished — show the final results.
};

this.barcodeCountView.SingleScanButtonTapped += (sender, args) =>
{
    // The user wants to switch to a single-barcode scan flow.
};
```

Each event argument (`ListButtonTappedEventArgs`, `ExitButtonTappedEventArgs`, `SingleScanButtonTappedEventArgs`) exposes a `.View` property.

## Complete minimal example

```csharp
using Android.OS;
using Android.Widget;

using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private BarcodeCount barcodeCount = null!;
    private BarcodeCountView barcodeCountView = null!;

    private readonly List<Barcode> scannedBarcodes = new();

    protected override async void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Camera (you manage it — the view does not).
        this.camera = Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            await this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        // Configure and create BarcodeCount.
        BarcodeCountSettings settings = new BarcodeCountSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });
        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);

        // Host the counting UI. BarcodeCountView IS an Android View — add it yourself.
        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.barcodeCountView = BarcodeCountView.Create(
            this, this.dataCaptureContext, this.barcodeCount, BarcodeCountViewStyle.Icon);
        container.AddView(this.barcodeCountView);

        this.barcodeCountView.ListButtonTapped += (s, e) => this.ShowResults();
        this.barcodeCountView.ExitButtonTapped += (s, e) => this.ShowResults();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
        this.barcodeCount.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
        this.barcodeCountView.Dispose();
        this.barcodeCount.Dispose();
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        this.RunOnUiThread(() =>
        {
            this.scannedBarcodes.Clear();
            this.scannedBarcodes.AddRange(recognized);
        });
    }

    private void ShowResults()
    {
        // Present this.scannedBarcodes to the user.
    }
}
```

## Capture list (receiving / "scan against an expected list")

A capture list checks scanned barcodes against an expected set of `TargetBarcode`s, classifying them as correct / wrong / missing. Both `BarcodeCountCaptureList` and `TargetBarcode` use **factory** methods.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture.List;
using Scandit.DataCapture.Barcode.Batch.Data;

private sealed class CaptureListListener : IBarcodeCountCaptureListListener
{
    public void OnObservationStarted() { }
    public void OnObservationStopped() { }

    public void OnCaptureListSessionUpdated(BarcodeCountCaptureListSession session)
    {
        IList<TrackedBarcode> correct = session.CorrectBarcodes;
        IList<TrackedBarcode> wrong   = session.WrongBarcodes;
        IList<TargetBarcode>  missing = session.MissingBarcodes;
        // Update progress UI...
    }

    public void OnCaptureListCompleted(BarcodeCountCaptureListSession session)
    {
        // Every expected barcode has been scanned.
    }
}

// Build the expected list and apply it to the mode:
var targets = new List<TargetBarcode>
{
    TargetBarcode.Create("0123456789012", 3),
    TargetBarcode.Create("9876543210987", 1),
};
BarcodeCountCaptureList captureList =
    BarcodeCountCaptureList.Create(new CaptureListListener(), targets);
this.barcodeCount.SetBarcodeCountCaptureList(captureList);

// Optional: auto-disable the mode once the whole list is captured.
settings.DisableModeWhenCaptureListCompleted = true;
```

### BarcodeCountCaptureListSession members

| Member | Type | Description |
|--------|------|-------------|
| `CorrectBarcodes` | `IList<TrackedBarcode>` | Scanned barcodes that are on the list. |
| `WrongBarcodes` | `IList<TrackedBarcode>` | Scanned barcodes that are not on the list. |
| `MissingBarcodes` | `IList<TargetBarcode>` | Expected barcodes not yet scanned. |
| `AdditionalBarcodes` | `IList<Barcode>` | Additional barcodes. |
| `AcceptedBarcodes` / `RejectedBarcodes` | `IList<TrackedBarcode>` | Used with the not-in-list accept/reject action. |

## Spatial map

When `settings.MappingEnabled = true`, the session can return a `BarcodeSpatialGrid` describing the physical layout of counted barcodes (e.g. a shelf grid):

```csharp
BarcodeSpatialGrid? grid = args.Session.GetSpatialMap();
if (grid is not null)
{
    for (int r = 0; r < grid.Rows(); r++)
    {
        for (int c = 0; c < grid.Columns(); c++)
        {
            BarcodeSpatialGridElement? element = grid.ElementAt(r, c);
            // element?.MainBarcode, element?.SubBarcode
        }
    }
}
```

> The .NET binding does **not** expose `BarcodeCountMappingFlowSettings` or a session-snapshot type. Mapping is limited to `MappingEnabled` + `GetSpatialMap()`.

## Optional configuration

### Customize feedback (BarcodeCountFeedback)

`BarcodeCount` plays a sound on success/failure by default. To customize:

```csharp
using Scandit.DataCapture.Barcode.Count.Feedback;

// Silent — no sound, no vibration:
this.barcodeCount.Feedback = new BarcodeCountFeedback();

// Restore defaults:
this.barcodeCount.Feedback = BarcodeCountFeedback.DefaultFeedback;
```

`BarcodeCountFeedback` exposes two `Core.Common.Feedback.Feedback` slots:

| Property | Type | Description |
|----------|------|-------------|
| `Success` | `Feedback` | Played on a successful scan. |
| `Failure` | `Feedback` | Played on a failed / rejected scan. |

To customize one:
```csharp
using Scandit.DataCapture.Core.Common.Feedback;

this.barcodeCount.Feedback = new BarcodeCountFeedback
{
    Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
    Failure = new Feedback(null, null),  // silent on failure
};
```

> `BarcodeCountFeedback.DefaultFeedback` is a **static property** in .NET — not a method. Calling it as `DefaultFeedback()` is a compile error.

### Custom brushes and barcode taps (IBarcodeCountViewListener)

Assign `barcodeCountView.Listener` to color barcodes differently and react to taps:

```csharp
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Core.UI.Style;

private sealed class ViewListener : IBarcodeCountViewListener
{
    public Brush? BrushForRecognizedBarcode(BarcodeCountView view, TrackedBarcode b) => null;          // null = default
    public Brush? BrushForRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode b) => null;
    public Brush? BrushForAcceptedBarcode(BarcodeCountView view, TrackedBarcode b) => null;
    public Brush? BrushForRejectedBarcode(BarcodeCountView view, TrackedBarcode b) => null;

    public void OnRecognizedBarcodeTapped(BarcodeCountView view, TrackedBarcode b) { }
    public void OnFilteredBarcodeTapped(BarcodeCountView view, TrackedBarcode b) { }
    public void OnRecognizedBarcodeNotInListTapped(BarcodeCountView view, TrackedBarcode b) { }
    public void OnAcceptedBarcodeTapped(BarcodeCountView view, TrackedBarcode b) { }
    public void OnRejectedBarcodeTapped(BarcodeCountView view, TrackedBarcode b) { }
    public void OnCaptureListCompleted(BarcodeCountView view) { }   // Android-only
}

this.barcodeCountView.Listener = new ViewListener();
```

### Not-in-list action

When a capture list is set, you can prompt the user to accept/reject barcodes that are not on the list, via `barcodeCountView.BarcodeNotInListActionSettings`:

```csharp
var action = this.barcodeCountView.BarcodeNotInListActionSettings;
action.Enabled = true;
action.AcceptButtonText = "Accept";
action.RejectButtonText = "Reject";
action.BarcodeAcceptedHint = "Barcode accepted";
action.BarcodeRejectedHint = "Barcode rejected";
```

### Status mode

Status mode lets you annotate each counted barcode with a status (expired, fragile, low stock, etc.). Implement `IBarcodeCountStatusProvider` and register it via `SetStatusProvider`:

```csharp
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Batch.Data;

private sealed class StatusProvider : IBarcodeCountStatusProvider
{
    public void OnStatusRequested(IList<TrackedBarcode> barcodes, IBarcodeCountStatusProviderCallback callback)
    {
        var items = barcodes
            .Select(b => BarcodeCountStatusItem.Create(b, BarcodeCountStatus.LowStock))
            .ToList();

        callback.OnStatusReady(
            BarcodeCountStatusResultSuccess.Create(items, "All items reviewed", "Status mode off"));
    }
}

this.barcodeCountView.ShouldShowStatusModeButton = true;
this.barcodeCountView.SetStatusProvider(new StatusProvider());
```

`BarcodeCountStatus` values: `None`, `NotAvailable`, `Expired`, `Fragile`, `QualityCheck`, `LowStock`, `Wrong`. Result factories: `BarcodeCountStatusResultSuccess.Create(statusList, enabledMessage, disabledMessage)`, `BarcodeCountStatusResultError.Create(statusList, errorMessage, disabledMessage)`, `BarcodeCountStatusResultAbort.Create(errorMessage)`.

### Show / hide built-in UI elements

The built-in UI is an integral part of MatrixScan Count and is recommended, but individual elements can be toggled with the `ShouldShow*` `bool` properties on `BarcodeCountView`. Set them after creating the view:

```csharp
// Hide toolbar buttons:
this.barcodeCountView.ShouldShowListButton = false;
this.barcodeCountView.ShouldShowExitButton = false;
this.barcodeCountView.ShouldShowShutterButton = false;

// Hide guidance and hints:
this.barcodeCountView.ShouldShowUserGuidanceView = false;
this.barcodeCountView.ShouldShowHints = false;

// Strap mode — a draggable floating shutter button for wrist-mounted devices:
this.barcodeCountView.ShouldShowFloatingShutterButton = true;

// "Clear screen" button — wipes AR overlays but keeps the counted barcodes:
this.barcodeCountView.ShouldShowClearHighlightsButton = true;
```

Other toggles: `ShouldShowSingleScanButton`, `ShouldShowStatusModeButton`, `ShouldShowToolbar`, `ShouldShowScanAreaGuides`, `ShouldShowListProgressBar`, `ShouldShowTorchControl`. To clear the on-screen highlights imperatively (without a button), call `this.barcodeCountView.ClearHighlights()`.

### Toolbar text

```csharp
var toolbar = new BarcodeCountToolbarSettings
{
    AudioOnButtonText = "Sound on",
    AudioOffButtonText = "Sound off",
    VibrationOnButtonText = "Vibration on",
    VibrationOffButtonText = "Vibration off",
};
this.barcodeCountView.SetToolbarSettings(toolbar);
```

### Hardware trigger (scan on a hardware button)

On Android you can let a hardware button (e.g. the volume-down key, or the dedicated scan button on XCover devices) drive the shutter instead of the on-screen button. This is a `BarcodeCountView` method on .NET Android — **not** the `HardwareTriggerEnabled` property (that property is the iOS/cross-platform shape and is **not** exposed on `dotnet.android`).

```csharp
using Android.Views; // for Keycode

// Use the default button (volume-down on most devices, the dedicated HW button on XCover):
if (BarcodeCountView.HardwareTriggerSupported)
{
    this.barcodeCountView.EnableHardwareTrigger(null);
}

// ...or react to a specific key code:
this.barcodeCountView.EnableHardwareTrigger((int)Keycode.VolumeDown);
```

- `EnableHardwareTrigger(int? hardwareTriggerKeyCode)` — pass `null` for the default button, or a `Keycode` cast to `int` for a specific key.
- Static `BarcodeCountView.HardwareTriggerSupported` (`bool`, get) — `true` only on API level 28+. Gate the call on it.

### Apply settings at runtime

```csharp
BarcodeCountSettings updated = new BarcodeCountSettings();
updated.EnableSymbology(Symbology.Qr, true);
await this.barcodeCount.ApplySettingsAsync(updated);
```

## Camera permission helper

The same permission helper as the official Scandit .NET Android samples — copy verbatim:

```csharp
using Android;
using Android.Annotation;
using Android.Content.PM;
using Android.OS;
using Android.Runtime;
using AndroidX.AppCompat.App;

public abstract class CameraPermissionActivity : AppCompatActivity
{
    private const string CAMERA_PERMISSION = Manifest.Permission.Camera;
    private const int CAMERA_PERMISSION_REQUEST = 0;

    private bool userDeniedPermissionOnce;
    private bool paused = true;

    protected override void OnPause()
    {
        base.OnPause();
        this.paused = true;
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.paused = false;
    }

    protected bool HasCameraPermission() =>
        Build.VERSION.SdkInt < BuildVersionCodes.M
        || CheckSelfPermission(CAMERA_PERMISSION) == Permission.Granted;

    [TargetApi(@Value = (int)BuildVersionCodes.M)]
    protected void RequestCameraPermission()
    {
        if (!this.HasCameraPermission())
        {
            if (!this.userDeniedPermissionOnce)
            {
                this.RequestPermissions(new string[] { CAMERA_PERMISSION }, CAMERA_PERMISSION_REQUEST);
            }
        }
        else
        {
            this.OnCameraPermissionGranted();
        }
    }

    public override void OnRequestPermissionsResult(
        int requestCode, string[] permissions, [GeneratedEnum] Permission[] grantResults)
    {
        if (requestCode == CAMERA_PERMISSION_REQUEST)
        {
            if (grantResults.Length > 0 && grantResults[0] == Permission.Granted)
            {
                this.userDeniedPermissionOnce = false;
                if (!this.paused) this.OnCameraPermissionGranted();
            }
            else
            {
                this.userDeniedPermissionOnce = true;
            }
        }
        else
        {
            base.OnRequestPermissionsResult(requestCode, permissions, grantResults);
        }
    }

    protected abstract void OnCameraPermissionGranted();
}
```

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **`BarcodeCount.Create(...)`, `new BarcodeCountSettings()`** — the mode uses a factory (no public constructor); the settings use `new`. (Opposite of MatrixScan AR.)
3. **You manage the camera** — `Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings)`, `dataCaptureContext.SetFrameSourceAsync(camera)`, `camera.SwitchToDesiredStateAsync(FrameSourceState.On/Off)` in `OnResume`/`OnPause`. `BarcodeCountView` has no `OnResume`/`OnPause`/`Start`/`Stop`.
4. **Set `barcodeCount.Enabled = true`** so frames are processed; toggle it across the lifecycle.
5. **`BarcodeCountView` is an Android `View`** — `BarcodeCountView.Create(context, …)` then `container.AddView(view)`. The first `Create` argument is the `Context`, not a parent view.
6. **`Scanned` event is idiomatic** — prefer `barcodeCount.Scanned += handler` over `AddListener`. Both deliver the scan result.
7. **`IBarcodeCountListener` has three methods** — `OnScan`, `OnObservationStarted`, `OnObservationStopped`.
8. **Copy barcodes out of the session immediately** — `session.RecognizedBarcodes.ToList()` inside the callback; the session is invalid afterward. `OnScan` runs on a background thread, so `RunOnUiThread` for UI.
9. **Capture list & TargetBarcode use factories** — `BarcodeCountCaptureList.Create(listener, targets)`, `TargetBarcode.Create(data, quantity)`, applied with `barcodeCount.SetBarcodeCountCaptureList(list)`.
10. **Feedback uses `Success`/`Failure`** — empty `new BarcodeCountFeedback()` is silent; `BarcodeCountFeedback.DefaultFeedback` (static property) restores defaults.
11. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Code128`, not the Kotlin underscore style.
12. **SDK 8.0+ requires `MainApplication`** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` in `OnCreate()` before any Scandit type is used.
13. **No `<activity>` in the manifest** — `[Activity(MainLauncher = true, ...)]` is the canonical registration.
14. **Use a `Theme.AppCompat` descendant** for the activity (manifest `<application android:theme=...>` or `[Activity(Theme=...)]`). Required because the activity inherits from `AppCompatActivity`.
