# MatrixScan Count .NET MAUI Integration Guide

`BarcodeCount` is the multi-barcode counting mode, designed for high-volume scanning such as inventory and receiving. It scans every barcode in the camera feed during a scan phase, then reports them all at once when the user triggers the scan. In .NET MAUI you host the full built-in counting UI with the dedicated `<scandit:BarcodeCountView>` control (camera preview, shutter, list/exit buttons, on-screen highlights and hints) and combine it with the cross-platform `Scandit.DataCapture.Core` / `Scandit.DataCapture.Barcode` APIs (a `DataCaptureContext`, a `Camera`, a `BarcodeCount` mode, the `Scanned` event).

Two things make BarcodeCount in MAUI different from the other Scandit MAUI modes:

1. **It has a dedicated MAUI view** (`<scandit:BarcodeCountView>`), unlike `BarcodeBatch` which uses the generic `<scandit:DataCaptureView>` + an overlay. In that respect it resembles SparkScan's `<scandit:SparkScanView>`.
2. **But you still manage the camera yourself.** Unlike `SparkScanView` (which drives the camera through its own `OnAppearing()`/`OnDisappearing()`), `BarcodeCountView` does **not** own the camera. You create a `Camera`, set it as the context's frame source, and switch it on/off across the page lifecycle. The MAUI `BarcodeCountView` has no `OnAppearing()`/`OnDisappearing()`/`StartScanning()` methods.

The examples below follow the structure of the official Scandit MAUI `MatrixScanCountSimpleSample`: a `BarcodeCountPage` (`ContentPage`) wired to a `BarcodeCountPageViewModel` through `BindingContext`, with a shared `CameraManager` and `BarcodeManager`. You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same (see the compact example at the end).

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `matrixscan-count-net-android` (for `net*-android`) or `matrixscan-count-net-ios` (for `net*-ios`). Those skills host `BarcodeCountView` as a native view, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all four packages.

Do **not** guess, do **not** reuse a version from training data. The latest stable version changes regularly — only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeCount` has been available on `dotnet.android` / `dotnet.ios` since **6.19**, so any current stable release supports it.

Then add **four** NuGet packages, pinned to that same version:
```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="<latest-stable-from-nuget>" />
</ItemGroup>
```
All four are needed. The `*.Maui` packages provide the MAUI builder extensions, handlers, and XAML controls; the plain packages provide the platform bindings they delegate to.

### Other prerequisites

- A `<UseMaui>true</UseMaui>` MAUI project targeting at least one of `net10.0-android` or `net10.0-ios`.
- **Android `SupportedOSPlatformVersion` must be at least `24`** — the MAUI template's default is `21`, which is below Scandit's Android AAR minimum and will produce a `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library` build error. If the `.csproj` has a lower value for the Android `SupportedOSPlatformVersion`, **update it to `24.0`** as part of the integration. iOS minimum is `15.0` (matches the MAUI template default).
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - **Android target**: MAUI's `Permissions.Camera` adds `android.permission.CAMERA` automatically when requested at build time. You can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
  - **iOS target**: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` with a short user-facing description. Without it the app crashes on first camera access.
- **No manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` call is needed** — the MAUI builder extensions (`UseScanditCore` / `UseScanditBarcode` below) perform this initialization for you on SDK 8.0+. This is different from the non-MAUI .NET Android / iOS Count skills, which require the calls in `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`. In a MAUI app, leave `Platforms/Android/MainApplication.cs` and `Platforms/iOS/AppDelegate.cs` as the MAUI template generates them.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as every extra symbology adds processing overhead.

Once the user responds, ask which `ContentPage` they'd like to host the counting UI on (and whether they want the MVVM split or a single-file page). Then write the integration code directly into that page (and supporting files). Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**
1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version (skip `-beta.*`/`-preview.*`/`-rc.*`). Do not skip this step — versions from training data are stale and will fail `dotnet restore`.
2. Add all four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`) to the `.csproj`, all pinned to that same version.
3. If the `.csproj` targets `net*-android` with `SupportedOSPlatformVersion` below `24`, bump it to `24.0`.
4. Update `MauiProgram.cs` to call `.UseScanditCore().UseScanditBarcode(configure => configure.AddBarcodeCountView())`.
5. Add the `<scandit:...>` XAML namespace and the `<scandit:BarcodeCountView>` element to the page, with `DataCaptureContext="{Binding DataCaptureContext}"` and `BarcodeCount="{Binding BarcodeCount}"`.
6. For iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. For Android: rely on `Permissions.Camera` (MAUI auto-adds the manifest entry) or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Namespaces

| Class | Namespace |
|-------|-----------|
| `BarcodeCount`, `BarcodeCountSettings`, `BarcodeCountSession`, `BarcodeCountEventArgs`, `IBarcodeCountListener` | `Scandit.DataCapture.Barcode.Count.Capture` |
| `BarcodeCountCaptureList`, `TargetBarcode`, `IBarcodeCountCaptureListListener`, `BarcodeCountCaptureListSession` | `Scandit.DataCapture.Barcode.Count.Capture.List` |
| `BarcodeCountFeedback` | `Scandit.DataCapture.Barcode.Count.Feedback` |
| `BarcodeCountViewStyle`, `IBarcodeCountViewListener`, `ExitButtonTappedEventArgs`, `ListButtonTappedEventArgs`, `SingleScanButtonTappedEventArgs`, status-mode types | `Scandit.DataCapture.Barcode.Count.UI` |
| `BarcodeCountView` (MAUI XAML control) | `Scandit.DataCapture.Barcode.Count.UI.Maui` |
| `Symbology`, `Barcode`, `SymbologyDescription` | `Scandit.DataCapture.Barcode.Data` |
| `TrackedBarcode` | `Scandit.DataCapture.Barcode.Batch.Data` |
| `DataCaptureContext` | `Scandit.DataCapture.Core.Capture` |
| `Camera`, `FrameSourceState`, `CameraSettings` | `Scandit.DataCapture.Core.Source` |
| `IFrameData` | `Scandit.DataCapture.Core.Data` |
| `UseScanditCore` | `Scandit.DataCapture.Core` |
| `UseScanditBarcode` | `Scandit.DataCapture.Barcode` |

## Step 1 — Register the MAUI builder extensions

In `MauiProgram.cs`, chain the Scandit builder extensions. **For BarcodeCount, `UseScanditCore` takes no lambda and `UseScanditBarcode` takes a lambda containing `AddBarcodeCountView()`** (the same shape as SparkScan, the opposite of BarcodeBatch/BarcodeCapture).

```csharp
using Scandit.DataCapture.Core;          // UseScanditCore
using Scandit.DataCapture.Barcode;       // UseScanditBarcode

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .UseScanditCore()
            .UseScanditBarcode(configure =>
            {
                configure.AddBarcodeCountView();
            });

        return builder.Build();
    }
}
```

- `UseScanditBarcode(configure => configure.AddBarcodeCountView())` registers the `BarcodeCountView` MAUI handler. **Required.**
- Do **not** write `.UseScanditCore(c => c.AddDataCaptureView())` — that's the BarcodeBatch/BarcodeCapture builder. BarcodeCount uses its own `<scandit:BarcodeCountView>`, not the generic `<scandit:DataCaptureView>`.
- Do **not** add `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` to `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`. The builder extensions perform SDK 8.0+ initialization themselves. (The non-MAUI Count skills require those manual calls — MAUI does not.)

## Step 2 — Create the DataCaptureContext, Camera, and BarcodeCount mode

In a small app these can live directly on the page; in larger apps factor them into a view model + shared managers. The official sample uses a `BarcodeCountPageViewModel` plus `LazyThreadSafetyMode.PublicationOnly` singletons (`CameraManager`, `BarcodeManager`).

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.ViewModels;

public class BarcodeCountPageViewModel : BaseViewModel
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private readonly DataCaptureContext dataCaptureContext;
    private readonly BarcodeCount barcodeCount;
    private readonly BarcodeCountSettings barcodeCountSettings;

    // Exposed for the XAML bindings on <scandit:BarcodeCountView>.
    public DataCaptureContext DataCaptureContext => this.dataCaptureContext;
    public BarcodeCount BarcodeCount => this.barcodeCount;

    public BarcodeCountPageViewModel()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // You manage the camera — the view does not (see Step 4 / CameraManager).
        CameraManager.Instance.Initialize(this.dataCaptureContext);

        // All symbologies are disabled by default. Enable only what you need —
        // every extra symbology adds processing overhead.
        this.barcodeCountSettings = new BarcodeCountSettings();
        this.barcodeCountSettings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        // BarcodeCount is created with a FACTORY and attached to the context.
        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, this.barcodeCountSettings);

        // Idiomatic C#: subscribe to the Scanned event (fires once per scan phase).
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        // See Step 6 — copy barcodes out of args.Session immediately.
    }
}
```

### BarcodeCount members

| Member | Description |
|--------|-------------|
| `static BarcodeCount Create(DataCaptureContext?, BarcodeCountSettings)` | Factory — creates the mode and attaches it to the context. No public `new BarcodeCount(...)`. |
| `static BarcodeCount Create(BarcodeCountSettings)` | Factory — creates the mode without a context. |
| `Enabled` (`bool` get/set) | **Set `true` to process frames.** Toggle across the lifecycle. |
| `Feedback` (`BarcodeCountFeedback` get/set) | Sound / vibration. See Optional configuration. |
| static `RecommendedCameraSettings` (`CameraSettings`) | Recommended camera settings for counting. Static **property**. |
| `ApplySettingsAsync(BarcodeCountSettings)` (`Task`) | Apply new settings. |
| `AddListener` / `RemoveListener(IBarcodeCountListener)` | Register/remove a listener. |
| `event EventHandler<BarcodeCountEventArgs> Scanned` | Raised when a scan phase finishes (= `IBarcodeCountListener.OnScan`). **Recommended.** |
| `Reset()` | Clear all counted barcodes and AR overlays for a fresh process. |
| `SetBarcodeCountCaptureList(BarcodeCountCaptureList)` | Apply a capture/receiving list. |
| `SetAdditionalBarcodes(IList<Barcode>)` / `ClearAdditionalBarcodes()` | Seed/clear already-counted barcodes (e.g. restored across backgrounding). |
| `Dispose()` | Releases native resources. |

> Use **either** `AddListener` **or** the `Scanned` event for the same handler — not both, or you double-process the scan result.

### BarcodeCountSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new BarcodeCountSettings()` | constructor | All symbologies disabled. (The settings use `new`; the *mode* uses the `Create` factory.) |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `GetSymbologySettings(Symbology)` | method | Per-symbology `SymbologySettings`. |
| `EnabledSymbologies` | get | Currently enabled symbologies. |
| `ExpectsOnlyUniqueBarcodes` | `bool` get/set | When `true`, assumes each barcode appears once and optimizes accordingly. |
| `DisableModeWhenCaptureListCompleted` | `bool` get/set | Auto-disable the mode once a capture list is complete. |
| `MappingEnabled` | `bool` get/set | Enables the spatial map (`session.GetSpatialMap()`). |
| `FilterSettings` | `BarcodeFilterSettings` (get) | Per-symbology / regex filtering. Mutate it (`ExcludedSymbologies`, `ExcludedCodesRegex`); do not reassign. See Filtering. |

> Symbology names are C# PascalCase: `Ean13Upca`, `Ean8`, `Upce`, `Code39`, `Code93`, `Code128`, `InterleavedTwoOfFive`, `Qr`, `DataMatrix`, `Pdf417`, `Aztec`, … Not Kotlin's `EAN13_UPCA` and not Swift's `.ean13UPCA`.

## Step 3 — Set up the camera (you manage it; the view does not)

This is the key difference from SparkScan in MAUI. Get the default camera with the recommended settings and set it as the context's frame source. Keep a reference so you can switch it on/off across the lifecycle. The official sample factors this into a `CameraManager` singleton:

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp;

public sealed class CameraManager
{
    private static readonly Lazy<CameraManager> instance =
        new(() => new CameraManager(), LazyThreadSafetyMode.PublicationOnly);
    public static CameraManager Instance => instance.Value;

    private Camera? camera;

    private CameraManager() { }

    public void Initialize(DataCaptureContext dataCaptureContext)
    {
        // Use the recommended camera settings for BarcodeCount.
        CameraSettings cameraSettings = BarcodeCount.RecommendedCameraSettings;

        // The camera is off by default; turn it on to start streaming frames.
        this.camera = Camera.GetDefaultCamera(cameraSettings);
        if (this.camera is null)
        {
            throw new InvalidOperationException("MatrixScan Count requires a camera.");
        }

        dataCaptureContext.SetFrameSourceAsync(this.camera);
    }

    public void ResumeFrameSource() =>
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);

    public void PauseFrameSource() =>
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}
```

> The MAUI `BarcodeCountView` has no `OnResume()`/`OnPause()`/`Start()`/`Stop()`/`OnAppearing()`/`OnDisappearing()`. The camera is the lifecycle handle.

## Step 4 — Add the BarcodeCountView in XAML

`Scandit.DataCapture.Barcode.Count.UI.Maui.BarcodeCountView` is a MAUI `View` with bindable properties. Add the XAML namespace and place it on the page; bind its `DataCaptureContext` and `BarcodeCount` to the view model.

```xml
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Barcode.Count.UI.Maui;assembly=ScanditBarcodeCaptureMaui"
             xmlns:viewmodels="clr-namespace:MyApp.ViewModels"
             x:DataType="viewmodels:BarcodeCountPageViewModel"
             x:Class="MyApp.Views.BarcodeCountPage"
             Title="MatrixScan Count">
    <ContentPage.BindingContext>
        <viewmodels:BarcodeCountPageViewModel x:Name="viewModel" />
    </ContentPage.BindingContext>
    <ContentPage.Content>
        <AbsoluteLayout>
            <scandit:BarcodeCountView
                x:Name="barcodeCountView"
                AbsoluteLayout.LayoutBounds="0,0,1,1"
                AbsoluteLayout.LayoutFlags="All"
                DataCaptureContext="{Binding DataCaptureContext}"
                BarcodeCount="{Binding BarcodeCount}"
                ViewStyle="Icon"
                ShouldShowTorchControl="True" />
        </AbsoluteLayout>
    </ContentPage.Content>
</ContentPage>
```

> ⚠️ **`DataCaptureContext="{Binding DataCaptureContext}"` and `BarcodeCount="{Binding BarcodeCount}"` are both mandatory.** Without them the view has no context/mode, the preview renders black, and counting never starts. Both are `OneTime` bindable properties — the page's `BindingContext` must expose `DataCaptureContext` (type `Scandit.DataCapture.Core.Capture.DataCaptureContext`) and `BarcodeCount` (type `Scandit.DataCapture.Barcode.Count.Capture.BarcodeCount`). Setting `x:Name` alone does **not** wire them.

> **Use `ViewStyle`, not `Style`.** The MAUI property that selects the counting-UI look is `ViewStyle="Icon"` (counted barcodes get a check-mark icon) or `ViewStyle="Dot"` (a dot). The default is `Dot`. `Style` is a stock MAUI property and has no effect on the counting UI. `ViewStyle` is `OneTime` — set it in XAML.

### Common BarcodeCountView bindable properties

| Property | Type | Description |
|----------|------|-------------|
| `DataCaptureContext` | `DataCaptureContext` (OneTime) | The context. **Bind it — mandatory.** |
| `BarcodeCount` | `BarcodeCount` (OneTime) | The mode. **Bind it — mandatory.** |
| `ViewStyle` | `BarcodeCountViewStyle` (OneTime) | `Icon` or `Dot`. Default `Dot`. |
| `ShouldShowListButton` / `ShouldShowExitButton` / `ShouldShowShutterButton` / `ShouldShowFloatingShutterButton` / `ShouldShowSingleScanButton` / `ShouldShowClearHighlightsButton` / `ShouldShowStatusModeButton` / `ShouldShowUserGuidanceView` / `ShouldShowHints` / `ShouldShowToolbar` / `ShouldShowScanAreaGuides` / `ShouldShowListProgressBar` / `ShouldShowTorchControl` | `bool` | Built-in UI toggles. |
| `ShouldDisableModeOnExitButtonTapped` | `bool` | Default `true`. |
| `TapToUncountEnabled` | `bool` | Tap a counted barcode to remove it. |
| `TorchControlPosition` | `Anchor` | Where the torch control sits. |
| `RecognizedBrush` / `NotInListBrush` / `AcceptedBrush` / `RejectedBrush` | `Brush?` | Overlay styles; static `Default*Brush` provide defaults. |

Non-bindable members (use from code-behind after the handler is ready): `Listener` (`IBarcodeCountViewListener?`), `BarcodeNotInListActionSettings` (get), `SetToolbarSettings(...)`, `ClearHighlights()`, `SetStatusProvider(...)`, `SetBrushForRecognizedBarcode`/`*NotInList`/`*Accepted`/`*Rejected`, `EnableHardwareTrigger(int?)` + static `HardwareTriggerSupported` (Android), `HardwareTriggerEnabled` (iOS).

## Step 5 — Subscribe to the view's button events in `HandlerChanged`

The List / Exit / SingleScan button events only fire once the native handler is attached. Subscribe to them inside `barcodeCountView.HandlerChanged` (the official sample's pattern) — subscribing in the constructor before the handler exists silently does nothing.

```csharp
using Scandit.DataCapture.Barcode.Count.UI;   // ExitButtonTappedEventArgs, ListButtonTappedEventArgs

namespace MyApp.Views;

public partial class BarcodeCountPage : ContentPage
{
    private readonly BarcodeCountPageViewModel viewModel;

    public BarcodeCountPage()
    {
        this.InitializeComponent();
        this.viewModel = (BarcodeCountPageViewModel)this.BindingContext;

        // Wire the view's events once the platform handler exists.
        this.barcodeCountView.HandlerChanged += this.OnBarcodeCountViewHandlerChanged;
    }

    private void OnBarcodeCountViewHandlerChanged(object? sender, EventArgs e)
    {
        this.barcodeCountView.ListButtonTapped += this.OnListButtonTapped;
        this.barcodeCountView.ExitButtonTapped += this.OnExitButtonTapped;
    }

    private void OnListButtonTapped(object? sender, ListButtonTappedEventArgs e)
    {
        // The user tapped the List button — show current results (order not complete).
        this.ShowResults(isOrderCompleted: false);
    }

    private void OnExitButtonTapped(object? sender, ExitButtonTappedEventArgs e)
    {
        // The user finished — show the final results.
        this.ShowResults(isOrderCompleted: true);
    }

    private void ShowResults(bool isOrderCompleted)
    {
        // Navigate to a results page using the barcodes you stored in Step 6.
    }
}
```

Each event-arg type lives in `Scandit.DataCapture.Barcode.Count.UI` (the non-MAUI namespace). The `SingleScanButtonTapped` event works the same way.

## Step 6 — Handle scan results

`Scanned` (equivalently `IBarcodeCountListener.OnScan`) fires when a scan phase finishes. It runs on a **background thread**, and the `BarcodeCountSession` is only valid inside the callback — copy out the barcodes you need immediately, and dispatch UI work via `MainThread.BeginInvokeOnMainThread(...)`.

The recommended idiomatic C# pattern is the event (wired in Step 2):

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;

private readonly List<Barcode> scannedBarcodes = new();

private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
{
    // Copy the recognized barcodes out of the session right away.
    List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
    List<Barcode> additional = args.Session.AdditionalBarcodes.ToList();

    MainThread.BeginInvokeOnMainThread(() =>
    {
        this.scannedBarcodes.Clear();
        this.scannedBarcodes.AddRange(recognized);
        // barcode.Data, barcode.Symbology, new SymbologyDescription(barcode.Symbology).ReadableName
    });
}
```

If you prefer the listener interface, implement `IBarcodeCountListener` — note it has **three** methods:

```csharp
using Scandit.DataCapture.Core.Data;

public class BarcodeCountPageViewModel : BaseViewModel, IBarcodeCountListener
{
    public void OnScan(BarcodeCount mode, BarcodeCountSession session, IFrameData data)
    {
        List<Barcode> recognized = session.RecognizedBarcodes.ToList();
        MainThread.BeginInvokeOnMainThread(() => /* update UI */);
    }

    public void OnObservationStarted(BarcodeCount mode) { }
    public void OnObservationStopped(BarcodeCount mode) { }
}

// In setup: this.barcodeCount.AddListener(this);
```

### BarcodeCountSession members

| Member | Type | Description |
|--------|------|-------------|
| `RecognizedBarcodes` | `IList<Barcode>` | All barcodes counted in this scan phase. |
| `AdditionalBarcodes` | `IList<Barcode>` | Barcodes added via `SetAdditionalBarcodes` (e.g. restored across backgrounding). |
| `FrameSequenceId` | `long` | Identifier of the underlying frame sequence. |
| `Reset()` | method | Reset all session state. Only call from inside the callback. |
| `GetSpatialMap()` / `GetSpatialMap(int rows, int cols)` | `BarcodeSpatialGrid?` | Spatial layout (requires `settings.MappingEnabled = true`). |

### Storing scanned barcodes across the results screen

Because the session is not accessible outside `OnScan`, store the barcodes if you need them later (e.g. to show a results list when the user taps List or Exit). The official sample keeps them in a shared `BarcodeManager` and, when the app goes to background, persists them as *additional* barcodes so the count survives:

```csharp
// When leaving for a results screen, or going to background:
this.barcodeCount.SetAdditionalBarcodes(savedBarcodes);

// To start a brand-new counting process:
this.barcodeCount.ClearAdditionalBarcodes();
this.barcodeCount.Reset();
```

## Step 7 — Lifecycle and camera permission

Drive the camera from the page's MAUI lifecycle. The official sample distinguishes *navigating internally* (to the results page — keep the camera/session) from *going to background* (pause the camera and persist barcodes as additional barcodes).

```csharp
// On the page:
protected override void OnAppearing()
{
    base.OnAppearing();
    _ = this.viewModel.ResumeAsync();
}

protected override void OnDisappearing()
{
    base.OnDisappearing();
    // navigatingInternally: true when going to the results page (keep camera/session).
    this.viewModel.PauseScanning(navigatingInternally: true);
}
```

```csharp
// On the view model (ResumeAsync / SleepAsync come from a BaseViewModel that forwards
// the application's lifecycle messages — see the official sample's BaseViewModel):
public override async Task ResumeAsync()
{
    var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
    if (status != PermissionStatus.Granted)
    {
        status = await Permissions.RequestAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            return; // surface a message; do not start the camera
        }
    }

    this.ResumeFrameSource();
}

public override Task SleepAsync()
{
    this.PauseScanning(navigatingInternally: false);
    return Task.CompletedTask;
}

public void PauseScanning(bool navigatingInternally)
{
    if (!navigatingInternally)
    {
        CameraManager.Instance.PauseFrameSource();
        // Persist scanned barcodes so the count survives backgrounding.
        BarcodeManager.Instance.SaveCurrentBarcodesAsAdditionalBarcodes();
    }
}

private void ResumeFrameSource()
{
    this.barcodeCount.Enabled = true;       // process frames
    CameraManager.Instance.ResumeFrameSource();
}
```

> Use `MainThread.BeginInvokeOnMainThread(...)` for UI dispatch from the background `Scanned` callback — not `RunOnUiThread` (Android-only) or `DispatchQueue.MainQueue` (iOS-only).

## Capture list (receiving / "scan against an expected list")

A capture list checks scanned barcodes against an expected set of `TargetBarcode`s, classifying them as correct / wrong / missing. Both `BarcodeCountCaptureList` and `TargetBarcode` use **factory** methods.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture.List;
using Scandit.DataCapture.Barcode.Batch.Data;   // TrackedBarcode

private sealed class CaptureListListener : IBarcodeCountCaptureListListener
{
    public void OnObservationStarted() { }
    public void OnObservationStopped() { }

    public void OnCaptureListSessionUpdated(BarcodeCountCaptureListSession session)
    {
        IList<TrackedBarcode> correct = session.CorrectBarcodes;
        IList<TrackedBarcode> wrong   = session.WrongBarcodes;
        IList<TargetBarcode>  missing = session.MissingBarcodes;
        // Update progress UI on the main thread.
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
this.barcodeCountSettings.DisableModeWhenCaptureListCompleted = true;
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

`BarcodeCountFeedback` exposes two `Core.Common.Feedback.Feedback` slots — `Success` (played on a successful scan) and `Failure` (played on a failed / rejected scan):

```csharp
using Scandit.DataCapture.Core.Common.Feedback;

this.barcodeCount.Feedback = new BarcodeCountFeedback
{
    Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
    Failure = new Feedback(null, null),   // silent on failure
};
```

> `BarcodeCountFeedback.DefaultFeedback` is a **static property** in .NET — not a method. Calling it as `DefaultFeedback()` is a compile error.

### Custom brushes and barcode taps (IBarcodeCountViewListener)

Assign `barcodeCountView.Listener` (after the handler is ready) to color barcodes differently and react to taps. The interface's brush-for and tap callbacks use `TrackedBarcode` (from `Scandit.DataCapture.Barcode.Batch.Data`):

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
}

// In OnBarcodeCountViewHandlerChanged:
this.barcodeCountView.Listener = new ViewListener();
```

> Note `BarcodeCountView` here is the platform type `Scandit.DataCapture.Barcode.Count.UI.BarcodeCountView` that the listener callbacks reference — the listener interface is shared across TFMs, the MAUI control wraps it.

### Not-in-list action

When a capture list is set, prompt the user to accept/reject barcodes not on the list via `barcodeCountView.BarcodeNotInListActionSettings` (available once the handler is ready):

```csharp
var action = this.barcodeCountView.BarcodeNotInListActionSettings;
if (action is not null)
{
    action.Enabled = true;
    action.AcceptButtonText = "Accept";
    action.RejectButtonText = "Reject";
    action.BarcodeAcceptedHint = "Barcode accepted";
    action.BarcodeRejectedHint = "Barcode rejected";
}
```

### Status mode

Annotate each counted barcode with a status (expired, fragile, low stock, etc.). Implement `IBarcodeCountStatusProvider` and register it via `SetStatusProvider` (after the handler is ready):

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

### Filtering

If several barcode types appear in the scene and you only want to count one of them, filter the rest out. Filtering is configured through `barcodeCountSettings.FilterSettings` (a `BarcodeFilterSettings` you read off the settings — you do **not** `new` it for this), then applied by creating the mode with those settings. You can filter by symbology or by a regex on the barcode data.

Exclude a symbology (e.g. count everything except PDF417):

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;

var settings = new BarcodeCountSettings();
settings.EnableSymbologies(new HashSet<Symbology>
{
    Symbology.Code128,
    Symbology.Pdf417,
});

// Count Code 128 but ignore PDF417 on the same label.
settings.FilterSettings.ExcludedSymbologies = new[] { Symbology.Pdf417 };
```

Exclude by a regex on the barcode data (e.g. drop anything starting with `1234`):

```csharp
settings.FilterSettings.ExcludedCodesRegex = "^1234.*";
```

> `BarcodeCountSettings.FilterSettings` is a **get-only** property — mutate the object it returns (`ExcludedSymbologies`, `ExcludedCodesRegex`, `ExcludedSymbolCounts`), do not reassign `FilterSettings`. On .NET, `BarcodeFilterSettings` is unified across iOS and Android (the Kotlin/Swift `BarcodeFilterSettings.Create()` factory does not exist here). Filtered barcodes are highlighted transparently by default; the per-barcode `IBarcodeCountViewListener.OnFilteredBarcodeTapped` callback fires when one is tapped.

### Expect only unique barcodes

If the environment guarantees each physical barcode value appears at most once (no duplicate labels), set `ExpectsOnlyUniqueBarcodes` to optimize scanning:

```csharp
var settings = new BarcodeCountSettings();
settings.EnableSymbologies(new HashSet<Symbology> { Symbology.Ean13Upca });
settings.ExpectsOnlyUniqueBarcodes = true;
```

### Hardware trigger

A hardware trigger lets the user start scanning with a physical button (e.g. a scan sled or a rugged device key). **The API differs by platform**, and MAUI compiles per target — guard each call with a platform check so the Android-only and iOS-only members are not referenced on the wrong target:

```csharp
#if ANDROID
// Android: enable via EnableHardwareTrigger(int? keyCode); null = default key.
if (Scandit.DataCapture.Barcode.Count.UI.BarcodeCountView.HardwareTriggerSupported)
{
    this.barcodeCountView.EnableHardwareTrigger(null);
}
#elif IOS
// iOS: a single bool property.
this.barcodeCountView.HardwareTriggerEnabled = true;
#endif
```

> Do **not** call `HardwareTriggerEnabled` on Android or `EnableHardwareTrigger` / `HardwareTriggerSupported` on iOS — those members only exist on their respective platform binding. Set this from code-behind after the handler is ready (inside `HandlerChanged`), like the other view configuration.

### Disable built-in UI elements

The built-in UI is integral to MatrixScan Count and Scandit recommends keeping it, but individual elements can be toggled off via the `ShouldShow*` properties (bindable in XAML, or set from code-behind):

```csharp
this.barcodeCountView.ShouldShowListButton = false;
this.barcodeCountView.ShouldShowExitButton = false;
this.barcodeCountView.ShouldShowShutterButton = false;
this.barcodeCountView.ShouldShowUserGuidanceView = false;
this.barcodeCountView.ShouldShowHints = false;
```

### Apply settings at runtime

```csharp
BarcodeCountSettings updated = new BarcodeCountSettings();
updated.EnableSymbology(Symbology.Qr, true);
await this.barcodeCount.ApplySettingsAsync(updated);
```

## Complete minimal example (single-page variant)

If the project is small and does not justify a dedicated ViewModel/Manager split, this is a compact `ContentPage.xaml.cs` that works end-to-end. The XAML is the same as Step 4, but set `BindingContext = this` from code-behind and bind to the page's own `DataCaptureContext` / `BarcodeCount` properties.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Count.UI;           // event args
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp.Views;

public partial class BarcodeCountPage : ContentPage
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeCount BarcodeCount { get; }

    private readonly Camera? camera;
    private readonly List<Barcode> scannedBarcodes = new();

    public BarcodeCountPage()
    {
        this.InitializeComponent();

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        // You manage the camera — the view does not.
        this.camera = Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            this.DataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        var settings = new BarcodeCountSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.BarcodeCount = BarcodeCount.Create(this.DataCaptureContext, settings);
        this.BarcodeCount.Scanned += this.OnScanned;

        this.BindingContext = this;
        this.barcodeCountView.HandlerChanged += this.OnHandlerChanged;
    }

    private void OnHandlerChanged(object? sender, EventArgs e)
    {
        this.barcodeCountView.ListButtonTapped += (s, args) => this.ShowResults();
        this.barcodeCountView.ExitButtonTapped += (s, args) => this.ShowResults();
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();

        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted) return;
        }

        this.BarcodeCount.Enabled = true;
        if (this.camera is not null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        if (this.camera is not null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    private void OnScanned(object? sender, BarcodeCountEventArgs args)
    {
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        MainThread.BeginInvokeOnMainThread(() =>
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

## Troubleshooting

### Black / blank camera preview

**Symptom:** The page renders, but the camera area is black; no scans happen even with permission granted.

**Cause (most common):** `<scandit:BarcodeCountView>` is missing the `DataCaptureContext` and/or `BarcodeCount` binding.

**Fix:** Add both `DataCaptureContext="{Binding DataCaptureContext}"` and `BarcodeCount="{Binding BarcodeCount}"`. The page's `BindingContext` must expose both properties. Setting only `x:Name` does not wire them. Also confirm the camera is actually turned on (`camera.SwitchToDesiredStateAsync(FrameSourceState.On)`) and `barcodeCount.Enabled = true` — unlike SparkScan, the view does not start the camera for you.

### Builder-chain mismatch / `AddBarcodeCountView` not found, or view never initializes

**Symptom:** `AddBarcodeCountView` is reported missing, or the view is blank because the handler is never registered.

**Cause:** Wrong builder shape. For BarcodeCount it is `.UseScanditCore().UseScanditBarcode(c => c.AddBarcodeCountView())`. Writing `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()` (the BarcodeBatch/BarcodeCapture shape) does not register the BarcodeCount handler.

**Fix:** Use the chain in Step 1. `AddBarcodeCountView()` goes inside the `UseScanditBarcode` lambda.

### List/Exit/SingleScan events never fire

**Symptom:** Subscribed to `ListButtonTapped` / `ExitButtonTapped` but the handlers never run.

**Cause:** Subscribed before the native handler existed (e.g. in the constructor, before `HandlerChanged`).

**Fix:** Subscribe inside `barcodeCountView.HandlerChanged` (Step 5). The events forward to the native view, which doesn't exist until the handler attaches.

### `RunOnUiThread` / `DispatchQueue` not found

`Scanned` runs on a background thread. In MAUI dispatch UI work with `MainThread.BeginInvokeOnMainThread(() => …)` or `MainThread.InvokeOnMainThreadAsync(...)` — `RunOnUiThread` is Android-only and `DispatchQueue.MainQueue.DispatchAsync` is iOS-only.

## Key rules

1. **Fetch the SDK version from NuGet, do not guess** — WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` for the latest stable before editing the `.csproj`. Skip `-beta`/`-preview`/`-rc`.
2. **Four NuGet packages** — Core + Core.Maui + Barcode + Barcode.Maui, all the same version.
3. **Builder chain** — `.UseScanditCore().UseScanditBarcode(c => c.AddBarcodeCountView())`. Core takes no lambda; Barcode takes the lambda with `AddBarcodeCountView()`. **No** manual `Initialize()` in `MainApplication`/`AppDelegate`.
4. **`<scandit:BarcodeCountView>` with both `DataCaptureContext` and `BarcodeCount` bound** — namespace `clr-namespace:Scandit.DataCapture.Barcode.Count.UI.Maui;assembly=ScanditBarcodeCaptureMaui`. Omitting either binding produces a black preview.
5. **`ViewStyle="Icon"` (or `Dot`), not `Style`** — `ViewStyle` is the counting-UI style property; default is `Dot`.
6. **You manage the camera** — `Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Off)` across `OnAppearing`/`OnDisappearing`. The MAUI `BarcodeCountView` has no `OnAppearing`/`OnDisappearing`/`StartScanning` (that's SparkScanView).
7. **`barcodeCount.Enabled = true`** so frames are processed; toggle it across the lifecycle.
8. **`BarcodeCount.Create(...)`, `new BarcodeCountSettings()`** — the mode uses a factory (no public constructor); the settings use `new`.
9. **Subscribe to List/Exit/SingleScan events in `HandlerChanged`** — they no-op before the handler attaches. Event-arg types are in `Scandit.DataCapture.Barcode.Count.UI`.
10. **`Scanned` event is idiomatic** — prefer `barcodeCount.Scanned += handler` over `AddListener`. Both deliver the scan result. `IBarcodeCountListener` has three methods (`OnScan`, `OnObservationStarted`, `OnObservationStopped`).
11. **Copy barcodes out of the session immediately** — `session.RecognizedBarcodes.ToList()` inside the callback; the session is invalid afterward. `Scanned` runs on a background thread — dispatch UI work via `MainThread.BeginInvokeOnMainThread`.
12. **Capture list & TargetBarcode use factories** — `BarcodeCountCaptureList.Create(listener, targets)`, `TargetBarcode.Create(data, quantity)`, applied with `barcodeCount.SetBarcodeCountCaptureList(list)`.
13. **Feedback uses `Success`/`Failure`** — empty `new BarcodeCountFeedback()` is silent; `BarcodeCountFeedback.DefaultFeedback` (static property) restores defaults.
14. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Code128`, not the Kotlin underscore style.
15. **Android `SupportedOSPlatformVersion` ≥ 24**, iOS `NSCameraUsageDescription` in `Info.plist`.
