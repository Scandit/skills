# MatrixScan Batch .NET MAUI Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks every barcode visible in the camera feed, reporting additions, position updates, and removals on every frame. Unlike `BarcodeCapture` (which scans one barcode at a time), `BarcodeBatch` continuously tracks every barcode in view — it does not stop or disable after a detection. On .NET MAUI you wire it up by combining the cross-platform `Scandit.DataCapture.Core` / `Scandit.DataCapture.Barcode` APIs (a `DataCaptureContext`, a `Camera`, a `BarcodeBatch` mode with the listener / `SessionUpdated` event) with two MAUI-specific pieces: the `<scandit:DataCaptureView>` XAML control from `Scandit.DataCapture.Core.UI.Maui`, and a `BarcodeBatchBasicOverlay` (and optionally a `BarcodeBatchAdvancedOverlay`) that is created **after** the view's platform handler has been attached.

`BarcodeBatch` itself does **not** have a dedicated MAUI handler (unlike `BarcodeArView`, `BarcodeCountView`, `BarcodeFindView`, `BarcodePickView`, `SparkScanView`). The MAUI integration always uses the generic `<scandit:DataCaptureView>` plus a `BarcodeBatchBasicOverlay`.

The examples below follow the structure of the official Scandit MAUI MatrixScan samples (`MatrixScanSimpleSample` and `MatrixScanBubblesSample`): a `MainPage` (`ContentPage`) wired to a `MainPageViewModel` through `BindingContext`, with a `DataCaptureManager` that owns the SDK objects. You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `matrixscan-batch-net-android` (for `net*-android`) or `matrixscan-batch-net-ios` (for `net*-ios`). Those skills cover the non-MAUI workloads.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all four packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.4.0` if only `8.4.0-beta.1` is published. The latest stable version changes regularly — only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix) before proceeding.

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
- **No manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` call is needed** — the MAUI builder extensions (`UseScanditCore` / `UseScanditBarcode` below) perform this initialization for you on SDK 8.0+. This is different from the non-MAUI .NET Android / iOS skills, which require the calls in `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`. In a MAUI app, leave `MainApplication.cs` and `AppDelegate.cs` as the MAUI template generates them.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves tracking performance and accuracy.

Once the user responds, ask which `ContentPage` they'd like to integrate BarcodeBatch into. Then write the integration code directly into that page (and supporting files). Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**
1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version (skip `-beta.*`/`-preview.*`/`-rc.*`). Do not skip this step — versions from training data are stale and will fail `dotnet restore` with `NU1103`.
2. Add all four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`) to the `.csproj`, all pinned to that same version.
3. If the `.csproj` targets `net*-android` with `SupportedOSPlatformVersion` below `24`, bump it to `24.0`. The MAUI template defaults to `21.0`, which fails the build because Scandit's Android AAR requires API 24+.
4. Update `MauiProgram.cs` to call `.UseScanditCore(configure => configure.AddDataCaptureView()).UseScanditBarcode()`.
5. Add the `<scandit:...>` XAML namespace and the `<scandit:DataCaptureView>` element to the page, with `DataCaptureContext="{Binding DataCaptureContext}"`.
6. For iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. For Android: rely on `Permissions.Camera` (MAUI auto-adds the manifest entry) or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Namespaces

| Class | Namespace |
|-------|-----------|
| `BarcodeBatch`, `BarcodeBatchSettings`, `IBarcodeBatchListener`, `BarcodeBatchSession`, `BarcodeBatchEventArgs`, `BarcodeBatchLicenseInfo` | `Scandit.DataCapture.Barcode.Batch.Capture` |
| `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `IBarcodeBatchBasicOverlayListener` | `Scandit.DataCapture.Barcode.Batch.UI.Overlay` |
| `BarcodeBatchAdvancedOverlay`, `IBarcodeBatchAdvancedOverlayListener` | `Scandit.DataCapture.Barcode.Batch.UI.Overlay` |
| `TrackedBarcode` | `Scandit.DataCapture.Barcode.Batch.Data` |
| `Symbology`, `Barcode`, `SymbologyDescription` | `Scandit.DataCapture.Barcode.Data` |
| `DataCaptureContext` | `Scandit.DataCapture.Core.Capture` |
| `Camera`, `FrameSourceState`, `CameraPosition`, `VideoResolution`, `CameraSettings` | `Scandit.DataCapture.Core.Source` |
| `DataCaptureView` (MAUI XAML control) | `Scandit.DataCapture.Core.UI.Maui` |
| `IFrameData` | `Scandit.DataCapture.Core.Data` |
| `Brush` | `Scandit.DataCapture.Core.UI.Style` |
| `Anchor`, `PointWithUnit`, `Quadrilateral`, `FloatWithUnit`, `MeasureUnit` | `Scandit.DataCapture.Core.Common.Geometry` |
| `UseScanditCore`, `UseScanditBarcode` | (extension methods — bring in via `using Scandit.DataCapture.Core;` and `using Scandit.DataCapture.Barcode;`) |

## Step 1 — Register MAUI builder extensions

In `MauiProgram.cs`, chain the Scandit builder extensions:

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
            .UseScanditCore(configure => configure.AddDataCaptureView())
            .UseScanditBarcode();

        return builder.Build();
    }
}
```

- `UseScanditCore(configure => configure.AddDataCaptureView())` registers the `DataCaptureView` MAUI handler. **Required** for BarcodeBatch in MAUI.
- `UseScanditBarcode()` takes **no inner configure**. It exists only to call `ScanditBarcodeCapture.Initialize()`. **Required** for BarcodeBatch in MAUI.

> Do **not** write `.UseScanditBarcode(configure => configure.AddBarcodeBatchView())` — `AddBarcodeBatchView` does not exist. `BarcodeBatch` does not have a pre-built MAUI view; it uses the generic `<scandit:DataCaptureView>`.

> Do **not** add `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` calls to `MainApplication.OnCreate` or `AppDelegate.FinishedLaunching`. The MAUI builder extensions perform the SDK 8.0+ initialization themselves. (The non-MAUI `matrixscan-batch-net-android` / `matrixscan-batch-net-ios` skills do require those manual calls — MAUI does not.)

## Step 2 — Create the DataCaptureContext, Camera, and BarcodeBatch mode

In a small app these can live directly on the page; in larger apps factor them into a `DataCaptureManager` (a singleton or DI-registered service). The official `MatrixScanSimpleSample` uses a `LazyThreadSafetyMode.PublicationOnly` singleton — that pattern is reproduced here.

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp.Models;

public class DataCaptureManager
{
    // Enter your Scandit License key here.
    // Your Scandit License key is available via your Scandit SDK web account.
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private static readonly Lazy<DataCaptureManager> instance =
        new(() => new DataCaptureManager(), LazyThreadSafetyMode.PublicationOnly);

    public static DataCaptureManager Instance => instance.Value;

    public DataCaptureContext DataCaptureContext { get; }
    public Camera? CurrentCamera { get; } = Camera.GetCamera(CameraPosition.WorldFacing);
    public CameraSettings CameraSettings { get; } = BarcodeBatch.RecommendedCameraSettings;
    public BarcodeBatch BarcodeBatch { get; }
    public BarcodeBatchSettings BarcodeBatchSettings { get; }

    private DataCaptureManager()
    {
        // The official sample bumps the camera to Full HD before binding.
        // Keep the default if Full HD is too aggressive for the target device range.
        this.CameraSettings.PreferredResolution = VideoResolution.FullHd;
        this.CurrentCamera?.ApplySettingsAsync(this.CameraSettings);

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);
        this.DataCaptureContext.SetFrameSourceAsync(this.CurrentCamera);

        this.BarcodeBatchSettings = BarcodeBatchSettings.Create();

        // The settings instance initially has all symbologies disabled.
        // Enable only what your app actually needs — fewer symbologies means faster tracking.
        var symbologies = new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Ean8,
            Symbology.Upce,
            Symbology.Code39,
            Symbology.Code128,
        };
        this.BarcodeBatchSettings.EnableSymbologies(symbologies);

        this.BarcodeBatch = BarcodeBatch.Create(this.DataCaptureContext, this.BarcodeBatchSettings);
    }
}
```

### BarcodeBatchSettings members

| Member | Description |
|--------|-------------|
| `BarcodeBatchSettings.Create()` (static factory) | Constructs a new settings instance with all symbologies disabled. There is no public constructor — always use `Create()`. |
| `EnableSymbology(Symbology, bool)` | Enable or disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | Enable a set in one call (a `HashSet<Symbology>` is the idiomatic argument). |
| `GetSymbologySettings(Symbology)` | Returns the per-symbology `SymbologySettings` (e.g. `ActiveSymbolCounts` as `ICollection<short>`). |
| `EnabledSymbologies` (get) | Currently enabled symbologies (`ICollection<Symbology>`). |
| `SetProperty(string, object)` / `GetProperty(string)` / `GetProperty<T>(string)` / `TryGetProperty<T>(string, out T?)` | Read/write unstable/experimental engine flags. |

> Symbology names are C# PascalCase. The full set includes `Ean13Upca`, `Ean8`, `Upce`, `Code39`, `Code93`, `Code128`, `InterleavedTwoOfFive`, `Qr`, `DataMatrix`, `Pdf417`, `Aztec`, `Codabar`, and more. Don't use Kotlin-style underscore names (`EAN13_UPCA`) or Swift-style camelCase (`ean13UPCA`).

### BarcodeBatch members

| Member | Description |
|--------|-------------|
| `BarcodeBatch.Create(DataCaptureContext?, BarcodeBatchSettings)` | Factory — creates the mode. Attaches to the context when `context` is non-null. |
| `Enabled` (`bool` get/set) | Pause / resume tracking without tearing down the camera. |
| `ApplySettingsAsync(BarcodeBatchSettings)` (`Task`) | Apply new settings on the next processed frame. |
| `AddListener(IBarcodeBatchListener)` / `RemoveListener(IBarcodeBatchListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeBatchEventArgs> SessionUpdated` | C# event raised every processed frame. Equivalent to `IBarcodeBatchListener.OnSessionUpdated`. |
| static `RecommendedCameraSettings` (`CameraSettings` get) | Recommended `CameraSettings` for BarcodeBatch. Static **property**, not a method. |
| `Context` (`DataCaptureContext?` get) | The context the mode is attached to. |
| `BarcodeBatchLicenseInfo` (`BarcodeBatchLicenseInfo?` get) | Licensed symbologies. **Available from 8.4+.** Value is populated after `IDataCaptureContextListener.OnModeAdded`. |
| `Dispose()` | Releases native resources. |

> Use **either** `AddListener` **or** the `SessionUpdated` event — not both for the same handler. There is **no** `BarcodeScanned` event on `BarcodeBatch` (batch is tracking, not single-scan).

## Step 3 — Add the DataCaptureView in XAML

`Scandit.DataCapture.Core.UI.Maui.DataCaptureView` is a MAUI `View` with a `DataCaptureContext` bindable property. Add the XAML namespace and place it on the page; bind its `DataCaptureContext` to the view model.

```xml
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage"
             Title="MatrixScan">
    <ContentPage.BindingContext>
        <vm:MainPageViewModel />
    </ContentPage.BindingContext>
    <ContentPage.Content>
        <AbsoluteLayout>
            <scandit:DataCaptureView x:Name="dataCaptureView"
                                     AbsoluteLayout.LayoutBounds="0,0,1,1"
                                     AbsoluteLayout.LayoutFlags="All"
                                     DataCaptureContext="{Binding DataCaptureContext}" />
        </AbsoluteLayout>
    </ContentPage.Content>
</ContentPage>
```

> ⚠️ **`DataCaptureContext="{Binding DataCaptureContext}"` is mandatory.** Without this binding the view has no context, the frame source is never attached to the preview, and the camera renders as a **black/blank screen** even though the code-behind looks correct. The page's `BindingContext` (whether it's a view model or the page itself via `BindingContext = this`) must expose a `DataCaptureContext` property of type `Scandit.DataCapture.Core.Capture.DataCaptureContext`, and the XAML element must bind to it. Setting `x:Name="dataCaptureView"` does **not** wire the context — the binding is separate and required.

`DataCaptureView` exposes:

| Member | Description |
|--------|-------------|
| `DataCaptureContext` | `BindableProperty` — the context whose frame source feeds this preview. Bind to a VM property of type `DataCaptureContext`. |
| `AddOverlay(IDataCaptureOverlay)` / `RemoveOverlay(IDataCaptureOverlay)` | Attach / detach overlays (e.g. `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`). |
| `MapFrameQuadrilateralToView(Quadrilateral)` | Convert image-space coordinates (like `TrackedBarcode.Location`) to view-space coordinates. Useful when computing custom highlight geometry. |
| `HandlerChanged` | Inherited MAUI event — fires when the platform-specific native view has been created. Create overlays here. |

## Step 4 — Create the BarcodeBatchBasicOverlay after `HandlerChanged`

The overlay must be created **after** the MAUI handler has attached a native view. Subscribe to `dataCaptureView.HandlerChanged` and add the overlay there. This matches the official `MatrixScanSimpleSample`.

```csharp
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using MyApp.ViewModels;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private BarcodeBatchBasicOverlay overlay = null!;
    private readonly MainPageViewModel viewModel;

    public MainPage()
    {
        this.InitializeComponent();
        this.viewModel = (MainPageViewModel)this.BindingContext;

        // Initialization of the overlay happens on the handler-changed event so the
        // native platform view exists.
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeBatchBasicOverlay.Create(
            this.viewModel.BarcodeBatch,
            BarcodeBatchBasicOverlayStyle.Frame);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();
        _ = this.viewModel.ResumeAsync();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        _ = this.viewModel.SleepAsync();
    }
}
```

> The `BarcodeBatchBasicOverlay.Create(barcodeBatch, dataCaptureView, ...)` overload with a `DataCaptureView` parameter is intended for native (non-MAUI) views — it expects an `Android.Views.View` or `UIKit.UIView`. **In MAUI you use the overload without a view (`Create(barcodeBatch)` or `Create(barcodeBatch, style)`) and attach via `dataCaptureView.AddOverlay(overlay)`**, because `<scandit:DataCaptureView>` is a MAUI `View` wrapping the native one.

### BarcodeBatchBasicOverlay members

| Member | Description |
|--------|-------------|
| `Create(BarcodeBatch, BarcodeBatchBasicOverlayStyle)` | Factory — creates the overlay with a specific style, detached from a view. **Use this in MAUI**, then attach via `dataCaptureView.AddOverlay(overlay)`. |
| `Create(BarcodeBatch)` | Factory — creates the overlay with default `Frame` style, detached from a view. |
| `Create(BarcodeBatch, DataCaptureView?, BarcodeBatchBasicOverlayStyle)` / `Create(BarcodeBatch, DataCaptureView?)` | Native (non-MAUI) overloads — the `DataCaptureView` here is the native iOS/Android type, not the MAUI XAML control. Do not use in MAUI. |
| `Listener` (`IBarcodeBatchBasicOverlayListener?` get/set) | For per-barcode brush customization. **Requires MatrixScan AR add-on.** |
| `Brush` (`Brush?` get/set) | Uniform brush applied to all tracked barcodes when no listener is set. Setting to `null` hides every tracked barcode. |
| static `DefaultBrushForStyle(BarcodeBatchBasicOverlayStyle)` | Returns the default Scandit brush for that style. |
| `Style` (`BarcodeBatchBasicOverlayStyle` get, read-only) | The overlay style passed to `Create`. |
| `ShouldShowScanAreaGuides` (`bool` get/set) | Debug aid: show the active scan-area outline. Defaults to `false`. |
| `SetBrushForTrackedBarcode(TrackedBarcode, Brush?)` | Imperatively set the brush for a specific tracked barcode. **Requires MatrixScan AR add-on.** |
| `ClearTrackedBarcodeBrushes()` | Clears all imperatively-set brushes. |
| `Dispose()` | Releases native resources. |

### BarcodeBatchBasicOverlayStyle enum

| Value | Description |
|-------|-------------|
| `Frame` | Draws highlights as a rectangular frame, with an appearance animation when a code is newly tracked. **Default.** |
| `Dot` | Draws highlights as a dot, with an appearance animation. |

## Step 5 — Implement IBarcodeBatchListener (or subscribe to SessionUpdated)

The official MAUI sample implements `IBarcodeBatchListener` on the view model. `OnSessionUpdated` is called on a **background recognition thread** — copy the data you need before dispatching to the UI thread via `MainThread.BeginInvokeOnMainThread` or `MainThread.InvokeOnMainThreadAsync`, and **always call `frameData.Dispose()` in a `finally` block** to keep iOS targets from stuttering.

> Why `try/finally` even on Android? The `OnSessionUpdated` callback runs on a background thread on both platforms. On iOS the native binding requires you to dispose the frame buffer or the recognition pipeline runs out of buffers; on Android the binding manages the lifetime itself. Writing the disposal once (in a `try`/`finally`) is safe on both, and MAUI apps almost always multi-target iOS, so the safest portable rule is to always dispose.

### Listener interface (the pattern used by the official sample)

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Data;
using MyApp.Models;

namespace MyApp.ViewModels;

public class MainPageViewModel : BaseViewModel, IBarcodeBatchListener
{
    private readonly HashSet<ScanResult> scanResults = new();
    private readonly Camera? camera = DataCaptureManager.Instance.CurrentCamera;

    public DataCaptureContext DataCaptureContext { get; } =
        DataCaptureManager.Instance.DataCaptureContext;
    public BarcodeBatch BarcodeBatch { get; } =
        DataCaptureManager.Instance.BarcodeBatch;

    public IEnumerable<ScanResult> ScanResults => this.scanResults;

    public MainPageViewModel()
    {
        // Register as a listener immediately — the camera/Enabled flag below gates
        // whether OnSessionUpdated will actually be called.
        this.BarcodeBatch.AddListener(this);
    }

    #region IBarcodeBatchListener
    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            // Called on a background recognition thread. Copy the data you need…
            var newScans = session.AddedTrackedBarcodes
                .Where(tb => tb.Barcode != null)
                .Select(tb => new ScanResult(
                    id: tb.Identifier,
                    data: tb.Barcode.Data ?? string.Empty,
                    symbology: new SymbologyDescription(tb.Barcode.Symbology).ReadableName))
                .ToList();

            if (newScans.Count == 0) return;

            // …then dispatch UI updates onto the main thread.
            MainThread.BeginInvokeOnMainThread(() =>
            {
                lock (this.scanResults)
                {
                    foreach (var result in newScans)
                    {
                        this.scanResults.Add(result);
                    }
                }
                this.OnPropertyChanged(nameof(this.ScanResults));
            });
        }
        finally
        {
            // Mandatory on iOS to avoid a frozen / stuttering preview; safe and recommended
            // on Android too. The MAUI app almost always multi-targets iOS.
            frameData.Dispose();
        }
    }
    #endregion
}

public record ScanResult(int Id, string Data, string Symbology);
```

### Event-based alternative (idiomatic C#)

```csharp
this.BarcodeBatch.SessionUpdated += (sender, args) =>
{
    try
    {
        var addedData = args.Session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .Where(d => d != null)
            .Cast<string>()
            .ToList();

        MainThread.BeginInvokeOnMainThread(() =>
        {
            foreach (var data in addedData)
            {
                // handle data
            }
        });
    }
    finally
    {
        args.FrameData.Dispose();
    }
};
```

### IBarcodeBatchListener

| Callback | Description |
|----------|-------------|
| `OnSessionUpdated(BarcodeBatch, BarcodeBatchSession, IFrameData)` | Called every processed frame. **Background recognition thread.** Copy data, dispatch UI work via `MainThread.BeginInvokeOnMainThread`, and dispose the frame. |
| `OnObservationStarted(BarcodeBatch)` | Listener was registered. |
| `OnObservationStopped(BarcodeBatch)` | Listener was removed. |

### BarcodeBatchEventArgs (for the event-based API)

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeBatch` | `BarcodeBatch` | The mode that raised the event. |
| `Session` | `BarcodeBatchSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. Always call `.Dispose()` on this before the handler returns. |

### BarcodeBatchSession

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `AddedTrackedBarcodes` | `IList<TrackedBarcode>` | Barcodes newly tracked in this frame. |
| `UpdatedTrackedBarcodes` | `IList<TrackedBarcode>` | Barcodes whose position changed in this frame. |
| `RemovedTrackedBarcodes` | `IList<int>` | **Tracking IDs** of barcodes that left the view (not `TrackedBarcode` instances). |
| `TrackedBarcodes` | `IDictionary<int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `FrameSequenceId` | `long` | Identifier of the current frame sequence. |
| `Reset()` | method | Clear all tracked state. Only call from inside `OnSessionUpdated`. |

> **Important:** Do not hold references to `BarcodeBatchSession` or its collections outside `OnSessionUpdated`. Copy any data you need before the callback returns. The session is mutated by the recognition thread on the next frame.

### TrackedBarcode

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `Barcode` | `Barcode` | The decoded barcode. Access `.Data`, `.Symbology`, etc. |
| `Identifier` | `int` | Unique tracking ID. **Reused** after the barcode leaves the frame. |
| `Location` | `Quadrilateral` | Barcode position in image-space coordinates. Use `dataCaptureView.MapFrameQuadrilateralToView(location)` to convert to view space. |
| `GetAnchorPosition(Anchor)` | `Point` | Returns the position of the given anchor on the tracked barcode. |

## Step 6 — Lifecycle and camera permission

Drive the camera from the page's MAUI lifecycle. Request the camera permission inside the `ResumeAsync` path so the first frame is not requested before the user grants access. The order in `SleepAsync` matters — disable `barcodeBatch.Enabled` **before** stopping the camera, because in-flight frames can still report tracked-barcode updates during the asynchronous camera-off transition.

```csharp
using System.ComponentModel;
using Scandit.DataCapture.Core.Source;

namespace MyApp.ViewModels;

public abstract class BaseViewModel : INotifyPropertyChanged
{
    public virtual Task ResumeAsync() => Task.CompletedTask;
    public virtual Task SleepAsync() => Task.CompletedTask;

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged(string name) =>
        this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public partial class MainPageViewModel : BaseViewModel
{
    // ...continuing from Step 5...

    public override async Task SleepAsync()
    {
        // Disable BarcodeBatch FIRST: the camera is stopped asynchronously and may
        // still deliver frames during the transition, which would otherwise produce
        // late OnSessionUpdated callbacks.
        this.BarcodeBatch.Enabled = false;

        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    public override async Task ResumeAsync()
    {
        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted)
            {
                // Surface a message; do not start the camera.
                return;
            }
        }

        await this.ResumeFrameSourceAsync();
    }

    private async Task<bool> ResumeFrameSourceAsync()
    {
        // Clear any previously-tracked results if you want a fresh run each time the page
        // appears. Omit if accumulation across appearings is desired.
        lock (this.scanResults) { this.scanResults.Clear(); }

        this.BarcodeBatch.Enabled = true;

        if (this.camera != null)
        {
            return await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
        return false;
    }
}
```

The page-level wiring is the snippet from Step 4:

```csharp
protected override void OnAppearing()
{
    base.OnAppearing();
    _ = this.viewModel.ResumeAsync();
}

protected override void OnDisappearing()
{
    base.OnDisappearing();
    _ = this.viewModel.SleepAsync();
}
```

## Complete minimal example (single-page variant)

If the project is small and does not justify a dedicated ViewModel/Manager, this is a compact `ContentPage.xaml.cs` that works end-to-end. The XAML is the same as in Step 3 (without the `BindingContext` element — set it from code-behind to `this`).

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;

namespace MyApp.Views;

public partial class MainPage : ContentPage, IBarcodeBatchListener
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    private readonly Camera? camera;
    private readonly BarcodeBatch barcodeBatch;
    private BarcodeBatchBasicOverlay? overlay;

    private readonly HashSet<int> seenTrackingIds = new();

    public MainPage()
    {
        this.InitializeComponent();

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetCamera(CameraPosition.WorldFacing);
        this.camera?.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
        this.DataCaptureContext.SetFrameSourceAsync(this.camera);

        var settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeBatch = BarcodeBatch.Create(this.DataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        this.BindingContext = this;
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeBatchBasicOverlay.Create(
            this.barcodeBatch,
            BarcodeBatchBasicOverlayStyle.Frame);
        this.dataCaptureView.AddOverlay(this.overlay);
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

        this.barcodeBatch.Enabled = true;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        this.barcodeBatch.Enabled = false;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            var newCodes = session.AddedTrackedBarcodes
                .Where(tb => this.seenTrackingIds.Add(tb.Identifier))
                .Select(tb => tb.Barcode.Data ?? string.Empty)
                .ToList();

            if (newCodes.Count == 0) return;

            MainThread.BeginInvokeOnMainThread(() =>
            {
                // Update UI with newCodes here.
            });
        }
        finally
        {
            frameData.Dispose();
        }
    }
}
```

## Optional: per-barcode brush customization (requires MatrixScan AR add-on)

Implement `IBarcodeBatchBasicOverlayListener` to return a different brush per tracked barcode. `BrushForTrackedBarcode` is called from the rendering thread.

```csharp
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Brush = Scandit.DataCapture.Core.UI.Style.Brush;

public partial class MainPageViewModel : BaseViewModel,
    IBarcodeBatchListener,
    IBarcodeBatchBasicOverlayListener
{
    // ...existing code...

    public Brush? BrushForTrackedBarcode(
        BarcodeBatchBasicOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        // Return null to use the overlay's default brush.
        // The Scandit `Brush` is a cross-platform value type — colors are constructed
        // with the platform-agnostic Microsoft.Maui.Graphics.Color.
        var color = trackedBarcode.Barcode.Symbology switch
        {
            Symbology.Ean13Upca => Microsoft.Maui.Graphics.Color.FromRgba(0, 255, 0, 102),  // green @ ~0.4 alpha
            Symbology.Code128   => Microsoft.Maui.Graphics.Color.FromRgba(0, 0, 255, 102),  // blue  @ ~0.4 alpha
            _ => (Microsoft.Maui.Graphics.Color?)null,
        };

        if (color == null) return null;

        return new Brush(
            fillColor:   color,
            strokeColor: color.WithAlpha(1f),
            strokeWidth: 2f);
    }

    public void OnTrackedBarcodeTapped(
        BarcodeBatchBasicOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        // React to the user tapping a barcode highlight.
    }
}
```

Then assign the listener after the overlay is created in `HandlerChanged`:

```csharp
private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
{
    this.overlay = BarcodeBatchBasicOverlay.Create(
        this.viewModel.BarcodeBatch,
        BarcodeBatchBasicOverlayStyle.Frame);
    this.overlay.Listener = this.viewModel;
    this.dataCaptureView.AddOverlay(this.overlay);
}
```

> **MatrixScan AR add-on required** for `BrushForTrackedBarcode` and `SetBrushForTrackedBarcode`. A uniform default brush (no listener, `overlay.Brush = …`) does not require the add-on.

## Optional: BarcodeBatchAdvancedOverlay (advanced, requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom platform view on each tracked barcode and retains its relative position as the barcode moves. In MAUI this is the **single biggest delta from the per-TFM skills**, because `IBarcodeBatchAdvancedOverlayListener.ViewForTrackedBarcode` must return a **native** view — `Android.Views.View` on Android, `UIKit.UIView` on iOS — not a MAUI `View`. The official `MatrixScanBubblesSample` solves this with a `partial` view model split into `Platforms/Android/` and `Platforms/iOS/`, each implementing the platform-specific `ViewForTrackedBarcode` and calling `mauiContentView.ToPlatform(new MauiContext(...))` to convert a MAUI control to the native type.

### Step A — Create a reusable MAUI overlay control

A regular MAUI `ContentView` is the easiest building block — bindable, declarative, cross-platform.

```xml
<!-- Views/StockOverlay.xaml -->
<ContentView xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             x:Class="MyApp.Views.StockOverlay">
    <Border BackgroundColor="#80000000"
            Padding="8"
            StrokeShape="RoundRectangle 6">
        <Label x:Name="dataLabel"
               TextColor="White"
               FontSize="14" />
    </Border>
</ContentView>
```

```csharp
// Views/StockOverlay.xaml.cs
namespace MyApp.Views;

public partial class StockOverlay : ContentView
{
    public StockOverlay(string data)
    {
        this.InitializeComponent();
        this.dataLabel.Text = data;
    }
}
```

### Step B — Cross-platform view-model with platform-specific `partial` halves

The cross-platform half implements the parts that compile on every TFM (anchor, offset, lifecycle, the `IBarcodeBatchListener` callbacks). The `ViewForTrackedBarcode` callback — which returns a platform-specific type — goes into the `partial` halves under `Platforms/Android/` and `Platforms/iOS/`.

```csharp
// ViewModels/MainPageViewModel.cs   (compiled on every TFM)
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Core.Common.Geometry;
using Scandit.DataCapture.Core.Data;
using MyApp.Views;

namespace MyApp.ViewModels;

public partial class MainPageViewModel : BaseViewModel,
    IBarcodeBatchListener,
    IBarcodeBatchAdvancedOverlayListener
{
    // Keep a MAUI ContentView per tracking ID so the same overlay re-attaches if the
    // barcode briefly leaves the frame and comes back with the same identifier.
    private readonly Dictionary<int, StockOverlay> overlays = new();

    // ...existing DataCaptureContext / BarcodeBatch / camera / ResumeAsync / SleepAsync...

    #region IBarcodeBatchAdvancedOverlayListener — cross-platform parts
    public Anchor AnchorForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode) => Anchor.TopCenter;

    public PointWithUnit OffsetForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode) =>
        // -100% of the overlay's own height in the Y direction puts it above the barcode.
        new PointWithUnit(
            new FloatWithUnit(0f, MeasureUnit.Fraction),
            new FloatWithUnit(-1f, MeasureUnit.Fraction));
    #endregion
}
```

```csharp
// Platforms/Android/ViewModels/MainPageViewModel.cs   (compiled only for net*-android)
using Microsoft.Maui.Platform;       // ToPlatform extension
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using MyApp.Views;

namespace MyApp.ViewModels;

public partial class MainPageViewModel
{
    public Android.Views.View? ViewForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        var id = trackedBarcode.Identifier;
        if (!this.overlays.TryGetValue(id, out var stockOverlay))
        {
            stockOverlay = new StockOverlay(trackedBarcode.Barcode.Data ?? string.Empty);
            this.overlays[id] = stockOverlay;
        }

        return stockOverlay.ToPlatform(
            new MauiContext(MainApplication.Current.Services, MainApplication.Context));
    }
}
```

```csharp
// Platforms/iOS/ViewModels/MainPageViewModel.cs   (compiled only for net*-ios)
using Microsoft.Maui.Platform;       // ToPlatform extension
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using MyApp.Views;

namespace MyApp.ViewModels;

public partial class MainPageViewModel
{
    public UIKit.UIView? ViewForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        var id = trackedBarcode.Identifier;
        if (!this.overlays.TryGetValue(id, out var stockOverlay))
        {
            stockOverlay = new StockOverlay(trackedBarcode.Barcode.Data ?? string.Empty);
            this.overlays[id] = stockOverlay;
        }

        return stockOverlay.ToPlatform(new MauiContext(AppDelegate.Current.Services));
    }
}
```

> **Why `partial`?** The native return type (`Android.Views.View?` vs. `UIKit.UIView?`) differs between Android and iOS, so the method cannot be expressed once on the cross-platform class. Splitting into a `partial` class with a per-platform half is the established MAUI pattern, used by Scandit's own `MatrixScanBubblesSample`. Place each platform-specific half under `Platforms/Android/` or `Platforms/iOS/` and MAUI's TFM-based file-include rules will compile only the matching half.

> **`MainApplication.Current` / `AppDelegate.Current`** are app-template defaults set up by the MAUI templates. If the project uses a custom application class, adjust the property name.

### Step C — Create the advanced overlay in `HandlerChanged`

Add the advanced overlay alongside the basic overlay (or instead of it, if you don't need the per-barcode highlights). Assign the listener after construction.

```csharp
private BarcodeBatchBasicOverlay basicOverlay = null!;
private BarcodeBatchAdvancedOverlay advancedOverlay = null!;

private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
{
    this.basicOverlay = BarcodeBatchBasicOverlay.Create(
        this.viewModel.BarcodeBatch,
        BarcodeBatchBasicOverlayStyle.Dot);
    this.dataCaptureView.AddOverlay(this.basicOverlay);

    this.advancedOverlay = BarcodeBatchAdvancedOverlay.Create(this.viewModel.BarcodeBatch);
    this.advancedOverlay.Listener = this.viewModel;
    this.dataCaptureView.AddOverlay(this.advancedOverlay);
}
```

### Imperative updates from outside the listener

If your UI logic needs to attach or update a view from outside `ViewForTrackedBarcode` (e.g. after an async backend lookup completes), call the `Set*ForTrackedBarcode` setters. They are thread-safe but accept the **native** view, so wrap the same `ToPlatform` conversion:

```csharp
this.advancedOverlay.SetViewForTrackedBarcode(
    trackedBarcode,
    mauiContentView.ToPlatform(new MauiContext(/* … */)));

this.advancedOverlay.SetAnchorForTrackedBarcode(trackedBarcode, Anchor.TopCenter);
this.advancedOverlay.SetOffsetForTrackedBarcode(trackedBarcode, offset);
this.advancedOverlay.ClearTrackedBarcodeViews(); // remove all anchored views
```

### BarcodeBatchAdvancedOverlay members

| Member | Description |
|--------|-------------|
| `Create(BarcodeBatch)` | Factory — creates the overlay; attach via `dataCaptureView.AddOverlay(overlay)`. **Use this overload in MAUI.** |
| `Create(BarcodeBatch, DataCaptureView?)` | Factory — non-MAUI overload taking a native iOS/Android view. Not used in MAUI. |
| `Listener` (`IBarcodeBatchAdvancedOverlayListener?` get/set) | Per-barcode view / anchor / offset provider. |
| `SetViewForTrackedBarcode(TrackedBarcode, view)` | Set or update the platform view for a barcode. Pass `null` to remove. The view parameter is platform-specific (`Android.Views.View?` / `UIKit.UIView?`). Thread-safe. |
| `SetAnchorForTrackedBarcode(TrackedBarcode, Anchor)` | Override the anchor for a barcode. Thread-safe. |
| `SetOffsetForTrackedBarcode(TrackedBarcode, PointWithUnit)` | Override the offset for a barcode. Thread-safe. |
| `ClearTrackedBarcodeViews()` | Remove all anchored views. Thread-safe. |
| `ShouldShowScanAreaGuides` (`bool` get/set) | Debug aid. |
| `Dispose()` | Releases native resources. |

### IBarcodeBatchAdvancedOverlayListener

| Callback | Description |
|----------|-------------|
| `ViewForTrackedBarcode(overlay, trackedBarcode)` | Return the platform view (`Android.Views.View?` / `UIKit.UIView?`) to anchor to this barcode, or `null` for none. Called on the main thread. **Must be implemented in a `partial` per-platform half in MAUI.** |
| `AnchorForTrackedBarcode(overlay, trackedBarcode)` → `Anchor` | Cross-platform — return the anchor for this barcode's view (e.g. `Anchor.TopCenter`). |
| `OffsetForTrackedBarcode(overlay, trackedBarcode)` → `PointWithUnit` | Cross-platform — return a `PointWithUnit` offset to fine-tune the view position. |

> For tap callbacks and additional advanced-overlay options, fetch the [Adding AR Overlays (.NET Android)](https://docs.scandit.com/sdks/net/android/matrixscan/advanced/) or [Adding AR Overlays (.NET iOS)](https://docs.scandit.com/sdks/net/ios/matrixscan/advanced/) page.

## Optional: pause / reset tracking

| Action | How |
|--------|-----|
| Pause tracking without releasing the camera | `barcodeBatch.Enabled = false` |
| Resume tracking | `barcodeBatch.Enabled = true` |
| Reset the tracker (clear all tracked barcodes) | Inside `OnSessionUpdated`, call `session.Reset()`. **Do not access `session` outside the callback.** |

## Optional: BarcodeBatchLicenseInfo (8.4+)

Once the mode has been attached to the context and the context has emitted `OnModeAdded`, you can inspect which symbologies the active license allows:

```csharp
// After IDataCaptureContextListener.OnModeAdded fires:
BarcodeBatchLicenseInfo? licenseInfo = this.barcodeBatch.BarcodeBatchLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

`BarcodeBatchLicenseInfo` is available from Scandit `dotnet.android` / `dotnet.ios` 8.4 onwards. On earlier versions the property does not exist.

## Troubleshooting

### Black / blank camera preview

**Symptom:** The page renders, but the camera area is completely black. No tracked-barcode updates arrive even though the camera has permission and the code compiles.

**Cause:** The `<scandit:DataCaptureView>` does not have its `DataCaptureContext` bindable property set.

**Fix:** Add `DataCaptureContext="{Binding DataCaptureContext}"` to the `<scandit:DataCaptureView>` element. The page's `BindingContext` must expose a `DataCaptureContext` property of type `Scandit.DataCapture.Core.Capture.DataCaptureContext`. Setting only `x:Name="dataCaptureView"` is **not** sufficient — the bindable property is what wires the camera feed to the preview.

### Frozen, non-responsive, or stuttering preview on iOS

**Symptom:** On a MAUI app running on iOS, the preview freezes after a few frames or stutters badly. Tracking updates stop arriving.

**Cause:** `IFrameData` (the `frameData` parameter of `OnSessionUpdated`, or `args.FrameData` from the `SessionUpdated` event) holds a native frame buffer. The .NET-iOS binding requires the consumer to explicitly `Dispose()` it; otherwise the recognition pipeline runs out of buffers and stalls. The MAUI layer does not paper over this.

**Fix:** Wrap the body of every `OnSessionUpdated` callback in a `try { ... } finally { frameData.Dispose(); }`, so the frame is always disposed — even on the early-return / exception path. See Step 5 for the full pattern. This is safe on Android too; making it unconditional means the same code works everywhere.

### Advanced-overlay views never appear

**Symptom:** `BarcodeBatchAdvancedOverlay` is attached, the listener is set, but no anchored views show up over tracked barcodes.

**Possible causes (in priority order):**

1. The MatrixScan AR add-on is not enabled on the license — `BarcodeBatchAdvancedOverlay` requires it. Confirm with the Scandit license dashboard.
2. `ViewForTrackedBarcode` returns a MAUI `View` instead of an `Android.Views.View` / `UIKit.UIView`. Without `.ToPlatform(new MauiContext(...))` the conversion never happens and the overlay receives a wrapper it cannot anchor. Use the partial-class split shown above.
3. The advanced overlay was created **before** `dataCaptureView.HandlerChanged` fired — no native view existed yet. Create it inside the `HandlerChanged` handler.
4. The cross-platform half's `AnchorForTrackedBarcode` / `OffsetForTrackedBarcode` return values that place the overlay off-screen. Try `Anchor.TopCenter` + offset `(0, -1 fraction)` first (matches the official sample).

### `MainThread.StartTimer` / `MainThread.RunAsync` not found

`MainThread` only has `BeginInvokeOnMainThread`, `InvokeOnMainThreadAsync`, and `IsMainThread`. There is no `MainThread.StartTimer` (`StartTimer` lives on `IDispatcher`, e.g. `Application.Current.Dispatcher.StartTimer(...)`) and no `MainThread.RunAsync`. For delayed work, use `await Task.Delay(...)` inside a `MainThread.BeginInvokeOnMainThread(async () => …)` lambda.

## Key rules

1. **Fetch the SDK version from NuGet, do not guess** — WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` for the latest stable version before editing the `.csproj`. Skip `-beta`/`-preview`/`-rc` suffixes. Versions from training data are stale.
2. **Android `SupportedOSPlatformVersion` ≥ 24** — the MAUI template defaults to `21`; Scandit's Android AAR requires 24. Bump the `.csproj` value if it's lower.
3. **Builder chain** — `MauiProgram.cs` must call `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`. `UseScanditBarcode` takes no inner configure. **No** manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` in `MainApplication`/`AppDelegate`.
4. **Four NuGet packages** — Core + Core.Maui + Barcode + Barcode.Maui. All four.
5. **DataCaptureView is XAML, and `DataCaptureContext="{Binding DataCaptureContext}"` is mandatory** — use `<scandit:DataCaptureView>` with the `xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"` namespace. Omitting the binding produces a black preview at runtime.
6. **Overlay after HandlerChanged** — create `BarcodeBatchBasicOverlay.Create(barcodeBatch, style)` (or `Create(barcodeBatch)`) inside `dataCaptureView.HandlerChanged`, then attach with `dataCaptureView.AddOverlay(overlay)`. Don't use the two-argument `Create(mode, view)` overload in MAUI — it expects a native iOS/Android view.
7. **MAUI lifecycle** — `OnAppearing` → start camera + `Enabled = true`; `OnDisappearing` → `Enabled = false` **first**, then stop the camera. The official sample explicitly comments on the order because in-flight frames can still report results during the async camera-off transition.
8. **MainThread dispatch** — use `MainThread.BeginInvokeOnMainThread(() => …)` or `MainThread.InvokeOnMainThreadAsync(...)`, not `RunOnUiThread` (Android-specific) or `DispatchQueue.MainQueue.DispatchAsync` (iOS-specific).
9. **`IFrameData.Dispose()` in `try/finally`** — every `OnSessionUpdated` callback must dispose the frame data, even on early-return / exception paths. Mandatory on iOS; safe and recommended on Android. Most MAUI apps multi-target iOS, so always include it.
10. **Don't retain the session** — `BarcodeBatchSession` and its collections are only safe within `OnSessionUpdated`. Copy data out before scheduling main-thread dispatch.
11. **Recognition thread for the listener** — `OnSessionUpdated` is **not** the main thread. Dispatch UI updates via `MainThread.BeginInvokeOnMainThread`.
12. **Camera permission** — `await Permissions.CheckStatusAsync<Permissions.Camera>()` + `await Permissions.RequestAsync<Permissions.Camera>()`. On iOS, set `NSCameraUsageDescription` in `Platforms/iOS/Info.plist`.
13. **AR add-on gates** — per-barcode brush customization (`IBarcodeBatchBasicOverlayListener` / `SetBrushForTrackedBarcode`) and `BarcodeBatchAdvancedOverlay` (anchored views) both require the MatrixScan AR add-on license.
14. **Advanced overlay returns native views** — `IBarcodeBatchAdvancedOverlayListener.ViewForTrackedBarcode` returns `Android.Views.View?` on Android and `UIKit.UIView?` on iOS. Use a `partial` class split into `Platforms/Android/` and `Platforms/iOS/`, and call `mauiContentView.ToPlatform(new MauiContext(...))` to convert a MAUI control. Do **not** return a MAUI `View` directly.
15. **Symbology names PascalCase** (`Ean13Upca`, `Code128`, `Qr`, `DataMatrix`) — not Kotlin's `EAN13_UPCA` / `CODE128` and not Swift's `.ean13UPCA`.
16. **`Enabled`, not `IsEnabled`** — the capture mode's pause flag is `barcodeBatch.Enabled`.
17. **No `BarcodeScanned` event** — `BarcodeBatch` is tracking, not single-scan. Use `SessionUpdated` or the listener interface.
