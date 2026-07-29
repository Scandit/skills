# SparkScan .NET MAUI Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. The `SparkScanView` overlays a draggable trigger button (and an optional mini preview) on top of any screen, so the user can scan without leaving their current workflow. In MAUI you use it through the `<scandit:SparkScanView>` XAML control, which has its own pre-built handler — no separate camera, `DataCaptureView`, or overlay wiring is needed.

The examples below follow the structure of the official Scandit MAUI SparkScan sample: a `MainPage` (ContentPage) wired to a `MainPageViewModel` through `BindingContext`, with a `ScannerModel` singleton that owns the `DataCaptureContext` and `SparkScan`. The MAUI page itself implements `ISparkScanFeedbackDelegate` because the feedback delegate runs on a background thread and benefits from staying close to where the cached success/error feedback objects live. You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `sparkscan-net-android` (for `net*-android`) or `sparkscan-net-ios` (for `net*-ios`). Those skills cover the non-MAUI workloads.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all four packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.4.0` if only `8.4.0-beta.1` is published. The latest stable version changes regularly — only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix) before proceeding.

Then add **four** NuGet packages, pinned to that same version:
```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="<latest-stable-from-nuget>" />
</ItemGroup>
```
All four are required. The `*.Maui` packages provide the MAUI builder extensions and the `<scandit:SparkScanView>` XAML control; the plain packages provide the platform bindings they delegate to.

### Other prerequisites

- A `<UseMaui>true</UseMaui>` MAUI project targeting at least one of `net10.0-android` or `net10.0-ios`.
- **Android `SupportedOSPlatformVersion` must be at least `24`** — the MAUI template's default is `21`, which is below Scandit's minimum and will produce a `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library` build error. iOS minimum is `15.0` (matches the MAUI template default):
  ```xml
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'ios'">15.0</SupportedOSPlatformVersion>
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">24.0</SupportedOSPlatformVersion>
  ```
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - **Android**: MAUI's `Permissions.Camera` adds `android.permission.CAMERA` automatically when requested at build time. You can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
  - **iOS**: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` with a short user-facing description. Without it the app crashes on first camera access.

> **Do not** add a manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` call in `Platforms/Android/MainApplication.cs` or `Platforms/iOS/AppDelegate.cs`. The `UseScanditCore()` and `UseScanditBarcode(...)` builder extensions perform initialization. The standard MAUI platform shims (`MainApplication.cs` / `AppDelegate.cs` calling `MauiProgram.CreateMauiApp()`) should remain unchanged.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which `ContentPage` they'd like to integrate SparkScan into. Then write the integration code directly into that page (and supporting files). Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**
1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version (skip `-beta.*`/`-preview.*`/`-rc.*`). Do not skip this step — versions from training data are stale and will fail `dotnet restore` with `NU1103`.
2. Add all four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`) to the `.csproj`, all pinned to the same version.
3. If the `.csproj` targets `net*-android` with `SupportedOSPlatformVersion` below `24`, bump it to `24.0`. The MAUI template defaults to `21.0`, which fails the build because Scandit's Android AAR requires API 24+.
4. Update `MauiProgram.cs` to call `.UseScanditCore().UseScanditBarcode(configure => configure.AddSparkScanView())`. (**This is different from the BarcodeCapture MAUI builder — see Step 1.**)
5. Add the `<scandit:...>` XAML namespace and the `<scandit:SparkScanView>` element to the page, bound to `DataCaptureContext`, `SparkScan`, and `SparkScanViewSettings` on the view model.
6. For iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. For Android: rely on `Permissions.Camera` (MAUI auto-adds the manifest entry) or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Register MAUI builder extensions

In `MauiProgram.cs`, chain the Scandit builder extensions:

```csharp
using Scandit.DataCapture.Core;     // UseScanditCore (extension)
using Scandit.DataCapture.Barcode;  // UseScanditBarcode (extension); ConfigureBarcode.AddSparkScanView()

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
                fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
            })
            .UseScanditCore()
            .UseScanditBarcode(configure =>
            {
                configure.AddSparkScanView();
            });

        return builder.Build();
    }
}
```

- `UseScanditCore()` takes **no** configure lambda for SparkScan. (BarcodeCapture's MAUI integration uses `UseScanditCore(c => c.AddDataCaptureView())` — that's a different mode and the shape does not apply here.)
- `UseScanditBarcode(c => c.AddSparkScanView())` registers the SparkScan MAUI handler. The `configure` lambda is **required** for SparkScan.

> **Common mistake:** writing `UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`. That is the BarcodeCapture MAUI builder chain — `AddSparkScanView()` is not on the `UseScanditCore` configure surface, and SparkScan does not use `<scandit:DataCaptureView>`. If both BarcodeCapture and SparkScan coexist in the same app, you need both `AddDataCaptureView()` (under `UseScanditCore`) **and** `AddSparkScanView()` (under `UseScanditBarcode`):
>
> ```csharp
> .UseScanditCore(c => c.AddDataCaptureView())
> .UseScanditBarcode(c => c.AddSparkScanView());
> ```

> **Do not** add `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` calls separately — `UseScanditCore()` / `UseScanditBarcode(...)` handle initialization through the builder.

## Step 2 — Build a ScannerModel (DataCaptureContext + SparkScan)

In MAUI it's idiomatic to factor SparkScan creation into a singleton service so the same `SparkScan` instance is shared across page lifecycles. The official sample uses a `Lazy<ScannerModel>` initialized on first access.

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Models;

public class ScannerModel
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private static readonly Lazy<ScannerModel> instance =
        new(() => new ScannerModel(), LazyThreadSafetyMode.PublicationOnly);

    public static ScannerModel Instance => instance.Value;

    public DataCaptureContext DataCaptureContext { get; }
    public SparkScan SparkScan { get; }

    private ScannerModel()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        SparkScanSettings settings = new();
        HashSet<Symbology> symbologies = new()
        {
            Symbology.Ean13Upca,
            Symbology.Ean8,
            Symbology.Upce,
            Symbology.Code39,
            Symbology.Code128,
            Symbology.InterleavedTwoOfFive,
        };
        settings.EnableSymbologies(symbologies);

        // Optional: adjust active symbol counts for variable-length 1D symbologies.
        settings.GetSymbologySettings(Symbology.Code39).ActiveSymbolCounts =
            new short[] { 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };

        this.SparkScan = new SparkScan(settings);
    }
}
```

Alternative: register `ScannerModel` (or an `IScannerModel` interface) via DI in `MauiProgram.cs` with `builder.Services.AddSingleton<ScannerModel>()` and inject it into the view model constructor. Both approaches work.

### SparkScanSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new SparkScanSettings()` | constructor | All symbologies disabled. |
| `new SparkScanSettings(CapturePreset)` | constructor | Construct from a preset. |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `EnableSymbologies(CompositeType)` | method | Enable symbologies required for the given composite types. |
| `GetSymbologySettings(Symbology)` | method | Returns the per-symbology `SymbologySettings`. |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `EnabledCompositeTypes` | `CompositeType` (get/set) | Bit-flag of enabled composite types. |
| `CodeDuplicateFilter` | `TimeSpan` (get/set) | Window to suppress duplicate scans. |
| `BatterySaving` | `BatterySavingMode` (get/set) | `Auto` (default), `On`, `Off`. |
| `ScanIntention` | `ScanIntention` (get/set) | `Smart` (default from 7.0) or `Manual`. |
| `SetProperty(string, object)` / `GetProperty<T>(string)` / `TryGetProperty<T>(string, out T)` | methods | Read/write unstable/experimental engine flags. |

> Unlike `BarcodeCaptureSettings`, `SparkScanSettings` does **not** expose `LocationSelection` — SparkScan controls scan location through its own `SparkScanScanningModeDefault` / `SparkScanScanningModeTarget` modes (see "Target Mode" below).

## Step 3 — Build a ViewModel that exposes the three bindables

The `<scandit:SparkScanView>` XAML control requires three bindable properties: `DataCaptureContext`, `SparkScan`, and `SparkScanViewSettings`. The view model wires the `BarcodeScanned` event on the cross-platform `SparkScan` mode.

```csharp
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

using MyApp.Models;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.ViewModels;

public class MainPageViewModel : INotifyPropertyChanged
{
    public DataCaptureContext DataCaptureContext { get; } = ScannerModel.Instance.DataCaptureContext;
    public SparkScan SparkScan { get; } = ScannerModel.Instance.SparkScan;
    public SparkScanViewSettings ViewSettings { get; } = new();

    public ObservableCollection<string> ScanResults { get; } = new();
    public string ItemCount => $"{this.ScanResults.Count} items";

    // Only needed if you implement the BaseViewModel / SleepAsync pattern from Step 8.
    // For single-page apps that just forward OnAppearing/OnDisappearing, this event
    // and the matching subscription in MainPage.xaml.cs can be omitted entirely.
    public event EventHandler? PauseScanning;
    public event PropertyChangedEventHandler? PropertyChanged;

    public MainPageViewModel()
    {
        this.SparkScan.BarcodeScanned += this.OnBarcodeScanned;
    }

    public void ClearScannedItems()
    {
        this.ScanResults.Clear();
        this.OnPropertyChanged(nameof(this.ItemCount));
    }

    public static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";

    private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        // BarcodeScanned runs on a background thread — marshal back to the main thread.
        MainThread.BeginInvokeOnMainThread(() =>
        {
            if (!IsBarcodeValid(barcode)) return;
            this.ScanResults.Add($"{new SymbologyDescription(barcode.Symbology).ReadableName} — {barcode.Data}");
            this.OnPropertyChanged(nameof(this.ItemCount));
        });
    }

    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
```

> **Pause from the view model:** the official sample exposes a `public event EventHandler? PauseScanning;` on the view model, raised from `SleepAsync`. The page subscribes to it and forwards to `this.SparkScanView.PauseScanning()`. This avoids leaking a `SparkScanView` reference into the view model.

### SparkScan members

| Member | Description |
|--------|-------------|
| `new SparkScan()` | Constructor — creates the mode with default settings. |
| `new SparkScan(SparkScanSettings settings)` | Constructor — creates the mode with the provided settings. |
| `Enabled` | `bool` (get/set) — pause / resume scanning without tearing down the camera. |
| `ApplySettingsAsync(SparkScanSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(ISparkScanListener)` / `RemoveListener(ISparkScanListener)` | Register or remove a listener. |
| `event EventHandler<SparkScanEventArgs> BarcodeScanned` | Raised on every successful scan. **Recommended** in MAUI. |
| `event EventHandler<SparkScanEventArgs> SessionUpdated` | Raised on every processed frame. |
| `SparkScanLicenseInfo` | `SparkScanLicenseInfo?` (get) — licensed symbologies (available after the context's `OnModeAdded`). |
| `Dispose()` | Releases native resources. |

### ISparkScanListener (alternative to the event)

If the project prefers a listener interface over the event:

```csharp
public class ScanHandler : ISparkScanListener
{
    public void OnBarcodeScanned(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;
        MainThread.BeginInvokeOnMainThread(() => { /* update UI */ });
    }

    public void OnSessionUpdated(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData) { }
}

// then: this.SparkScan.AddListener(handler);
```

> `ISparkScanListener` has **only two** methods — `OnBarcodeScanned` and `OnSessionUpdated`. No `OnObservationStarted` / `OnObservationStopped` (unlike `IBarcodeCaptureListener`).

## Step 4 — Configure SparkScanViewSettings

The view settings live on the view model so XAML can bind to them. Tweak only what you need to change.

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Source;

public SparkScanViewSettings ViewSettings { get; } = new()
{
    SoundEnabled = true,
    HapticEnabled = true,
    DefaultMiniPreviewSize = SparkScanMiniPreviewSize.Regular,
    HardwareTriggerEnabled = false, // Android-only behavior; harmless on iOS
    DefaultCameraPosition = CameraPosition.WorldFacing,
};
```

### SparkScanViewSettings members

| Member | Type | Description |
|--------|------|-------------|
| `TriggerButtonCollapseTimeout` | `TimeSpan` | Auto-collapse the trigger button after this delay. Default 5 s in v7+. Use `TimeSpan.FromSeconds(-1)` for "never". |
| `DefaultScanningMode` | `ISparkScanScanningMode` | Either `SparkScanScanningModeDefault` or `SparkScanScanningModeTarget`. |
| `DefaultTorchState` | `TorchState` | `Off` (default), `On`, `Auto`. If `Auto`, the torch control is hidden. |
| `SoundEnabled` | `bool` | Beep on success. |
| `HapticEnabled` | `bool` | Vibrate on success. |
| `HoldToScanEnabled` | `bool` | Tap-and-hold vs tap-toggle on the trigger. |
| `HardwareTriggerEnabled` | `bool` | Listen for hardware-button presses (Android only — has no effect on iOS). |
| `ZoomFactorOut` / `ZoomFactorIn` | `float` | Zoom levels for the zoom-switch control. |
| `ToastSettings` | `SparkScanToastSettings` | Toast appearance and text. |
| `VisualFeedbackEnabled` | `bool` | Show the green/red flash on success/error. |
| `InactiveStateTimeout` | `TimeSpan` | Time before transitioning to `Inactive` view state. |
| `DefaultCameraPosition` | `CameraPosition` | `WorldFacing` (default) or `UserFacing`. |
| `DefaultMiniPreviewSize` | `SparkScanMiniPreviewSize` | `Regular` (default) or `Expanded`. |
| `SmartSelectionCandidateBrush` | `Brush?` | Brush used for the smart-selection candidate highlight. |

> `HardwareTriggerKeyCode` is gated behind `#if __ANDROID__` in the .NET binding and is **not visible** to cross-platform MAUI code. For per-platform key-code customization, use a compiler-conditional helper in the Android-specific code path.

## Step 5 — Add the SparkScanView in XAML

`Scandit.DataCapture.Barcode.Spark.UI.Maui.SparkScanView` is a MAUI `View` with bindable properties `DataCaptureContext`, `SparkScan`, `SparkScanViewSettings`, and `Feedback`. Add the XAML namespace and place the control on the page; bind its three required properties to the view model.

`Views/MainPage.xaml`:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Barcode.Spark.UI.Maui;assembly=ScanditBarcodeCaptureMaui"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage"
             x:DataType="vm:MainPageViewModel">
    <ContentPage.BindingContext>
        <vm:MainPageViewModel x:Name="ViewModel" />
    </ContentPage.BindingContext>
    <ContentPage.Content>
        <AbsoluteLayout>
            <!-- Your screen content (results list, header, buttons, etc.) -->

            <scandit:SparkScanView
                x:Name="SparkScanView"
                AbsoluteLayout.LayoutBounds="0,0,1,1"
                AbsoluteLayout.LayoutFlags="All"
                DataCaptureContext="{Binding DataCaptureContext}"
                SparkScan="{Binding SparkScan}"
                SparkScanViewSettings="{Binding ViewSettings}">
            </scandit:SparkScanView>
        </AbsoluteLayout>
    </ContentPage.Content>
</ContentPage>
```

> ⚠️ **All three of `DataCaptureContext`, `SparkScan`, and `SparkScanViewSettings` are mandatory.** Without any one of them bound, the preview is black and scanning never starts. Setting `x:Name="SparkScanView"` does **not** wire anything by itself — the bindings are separate and required.

> ⚠️ **Namespace assembly is `ScanditBarcodeCaptureMaui`, not `Scandit.DataCapture.Barcode.Maui`.** The NuGet package id has dots; the produced assembly file does not. Easy to get wrong by copy-pasting the package id.

> ⚠️ **`x:Name="SparkScanView"` auto-generates a code-behind field — do not redeclare it.** MAUI's XAML source generator produces a strongly-typed field for any element with `x:Name`, so the code-behind can already write `this.SparkScanView.Feedback = …` and `this.SparkScanView.OnAppearing()` directly. Adding your own `private SparkScanView SparkScanView` (or property) in `MainPage.xaml.cs` produces a `CS0102` "type already contains a definition" error.

> The official sample places the `<scandit:SparkScanView>` **last** inside an `AbsoluteLayout` covering the full page (`LayoutBounds="0,0,1,1"`, `LayoutFlags="All"`) so the SparkScan UI floats on top of the rest of the screen content. Reproduce that layout structure unless the user explicitly wants a different placement.

### SparkScanView (MAUI control) members

| Member | Description |
|--------|-------------|
| `DataCaptureContext` | Bindable property — set to the page/VM's `DataCaptureContext`. **Required.** |
| `SparkScan` | Bindable property — set to the page/VM's `SparkScan`. **Required.** |
| `SparkScanViewSettings` | Bindable property — set to the page/VM's `SparkScanViewSettings`. **Required.** |
| `Feedback` | Bindable property — set to an `ISparkScanFeedbackDelegate` for per-barcode feedback. Optional. |
| `OnAppearing()` | Call from the page's `OnAppearing` override. **Required** for correct camera lifecycle. |
| `OnDisappearing()` | Call from the page's `OnDisappearing` override. **Required.** |
| `StartScanning()` | Programmatically start scanning (no user trigger tap). |
| `PauseScanning()` | Programmatically pause scanning. |
| `ShowToast(string)` | Show a custom toast in the mini preview. |
| `BarcodeCountButtonVisible` / `BarcodeFindButtonVisible` / `LabelCaptureButtonVisible` / `TargetModeButtonVisible` / `ScanningBehaviorButtonVisible` | `bool` — toolbar button visibility. All default `false`. |
| `ZoomSwitchControlVisible` / `PreviewSizeControlVisible` / `CameraSwitchButtonVisible` / `TriggerButtonVisible` / `PreviewCloseControlVisible` / `TorchControlVisible` | `bool` — other UI control visibility. `TriggerButtonVisible` defaults to `true`. |
| `ToolbarBackgroundColor` / `ToolbarIconActiveTintColor` / `ToolbarIconInactiveTintColor` | `Color?` — toolbar color customization. |
| `TriggerButtonCollapsedColor` / `TriggerButtonExpandedColor` / `TriggerButtonAnimationColor` / `TriggerButtonTintColor` | `Color?` — trigger button color customization. |
| `TriggerButtonImage` | `Image?` — replace the trigger button icon. |
| `event EventHandler<SparkScanViewEventArgs> BarcodeCountButtonTapped` / `BarcodeFindButtonTapped` / `LabelCaptureButtonTapped` | Toolbar button taps. |
| `event EventHandler<SparkScanViewStateEventArgs> ViewStateChanged` | View state transitions (Initial → Idle → Inactive → Active → Error). |

## Step 6 — Page code-behind: lifecycle + feedback delegate

The page implements `ISparkScanFeedbackDelegate` so it can hold cached success / error feedback objects. The page forwards `OnAppearing` / `OnDisappearing` into the SparkScan control. The view model's `PauseScanning` event is forwarded into `this.SparkScanView.PauseScanning()`.

`Views/MainPage.xaml.cs`:

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using MyApp.ViewModels;

namespace MyApp.Views;

public partial class MainPage : ISparkScanFeedbackDelegate
{
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;
    private SparkScanBarcodeSuccessFeedback successFeedback = null!;

    public MainPage()
    {
        this.InitializeComponent();
        this.SetupSparkScanFeedback();
        this.SubscribeToViewModelEvents();
    }

    private void SetupSparkScanFeedback()
    {
        // `resumeCapturingDelay` is how long the error state holds before scanning re-arms.
        // 60 s is a production value (the error stays until the user explicitly retriggers).
        // For demos / manual testing, drop it to a few seconds so iteration is bearable.
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));
        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.SparkScanView.Feedback = this;
    }

    private void SubscribeToViewModelEvents()
    {
        this.ViewModel.PauseScanning += (_, _) => this.SparkScanView.PauseScanning();
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();
        this.SparkScanView.OnAppearing();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.SparkScanView.OnDisappearing();
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        MainPageViewModel.IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;
}
```

> **`GetFeedbackForBarcode` runs on a background thread.** Build the feedback objects in the page constructor and return cached instances — do not allocate inside the delegate, and do not dispatch to the main thread inside it.

### Feedback classes

`SparkScanBarcodeFeedback` is an abstract base; the two concrete types are:

| Type | Constructors |
|------|--------------|
| `SparkScanBarcodeSuccessFeedback` | `()` (default), `(Color visualFeedbackColor)`, `(Color visualFeedbackColor, Brush brush)`, `(Color visualFeedbackColor, Brush brush, Feedback? feedback)` — read-only properties `VisualFeedbackColor`, `Brush`, `Feedback`. |
| `SparkScanBarcodeErrorFeedback` | `(string message, TimeSpan resumeCapturingDelay)`, `(string, TimeSpan, Color)`, `(string, TimeSpan, Color, Brush)`, `(string, TimeSpan, Color, Brush, Feedback?)` — read-only properties `Message`, `ResumeCapturingDelay`, `VisualFeedbackColor`, `Brush`, `Feedback`. |

Returning `null` from `GetFeedbackForBarcode` falls back to the default success feedback. The `Feedback` parameter is `Scandit.DataCapture.Core.Common.Feedback.Feedback` (the same type used by `BarcodeCaptureFeedback`).

## Step 7 — Camera permission

Request the camera permission inside `OnAppearing` (or a `ResumeAsync` path on the view model). MAUI's `Permissions.Camera` handles both platforms transparently.

```csharp
protected override async void OnAppearing()
{
    base.OnAppearing();
    this.SparkScanView.OnAppearing();

    var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
    if (status != PermissionStatus.Granted)
    {
        await Permissions.RequestAsync<Permissions.Camera>();
    }
}
```

On Android this triggers a runtime permission prompt; on iOS the system permission dialog is shown automatically the first time the camera starts (which is what `SparkScanView.OnAppearing()` does internally).

## Step 8 — Lifecycle management beyond `OnAppearing`/`OnDisappearing`

For a single-page app, forwarding `OnAppearing` and `OnDisappearing` is enough. For multi-page apps where the camera should release while another tab/page is foregrounded, use a `BaseViewModel` pattern with `ResumeAsync` / `SleepAsync` (the MAUI sample uses `CommunityToolkit.Mvvm.Messaging.WeakReferenceMessenger` for app-level start/sleep/resume messages):

```csharp
public abstract class BaseViewModel : INotifyPropertyChanged
{
    protected virtual Task StartAsync() => Task.CompletedTask;
    protected virtual Task ResumeAsync() => Task.CompletedTask;
    protected virtual Task SleepAsync() => Task.CompletedTask;
    // ... PropertyChanged + Receive(ApplicationMessage) plumbing ...
}
```

In the view model:

```csharp
public event EventHandler? PauseScanning;

protected override Task SleepAsync()
{
    this.PauseScanning?.Invoke(this, EventArgs.Empty);
    return Task.CompletedTask;
}
```

…and the page forwards the event into `this.SparkScanView.PauseScanning()` (see Step 6).

For most projects, the lighter pattern in Step 6 (just forwarding `OnAppearing` / `OnDisappearing`) is sufficient.

## Complete minimal example (single-page variant)

If the project is small and does not justify a dedicated view model, a compact `ContentPage.xaml.cs` works end-to-end. The XAML is the same as Step 5; the code-behind owns the SDK objects directly.

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Views;

public partial class MainPage : ContentPage, ISparkScanFeedbackDelegate
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public SparkScan SparkScan { get; }
    public SparkScanViewSettings ViewSettings { get; } = new();

    private readonly SparkScanBarcodeSuccessFeedback successFeedback = new();
    private readonly SparkScanBarcodeErrorFeedback errorFeedback =
        new(message: "Wrong barcode", resumeCapturingDelay: TimeSpan.FromSeconds(60));

    public MainPage()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        SparkScanSettings settings = new();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });
        this.SparkScan = new SparkScan(settings);
        this.SparkScan.BarcodeScanned += this.OnBarcodeScanned;

        this.InitializeComponent();
        this.BindingContext = this;
        this.SparkScanView.Feedback = this;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        this.SparkScanView.OnAppearing();

        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            await Permissions.RequestAsync<Permissions.Camera>();
        }
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.SparkScanView.OnDisappearing();
    }

    private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        MainThread.BeginInvokeOnMainThread(async () =>
        {
            await this.DisplayAlertAsync("Scanned", barcode.Data, "OK");
        });
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        barcode.Data == "123456789" ? this.errorFeedback : this.successFeedback;
}
```

> **`DisplayAlertAsync`, not `DisplayAlert`.** Use `await this.DisplayAlertAsync(title, message, "OK")`. The unsuffixed `DisplayAlert(...)` overload is obsolete in MAUI 9 and produces a `CS0618` warning.

## Optional configuration

### Target Mode (aim-to-scan)

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;

viewSettings.DefaultScanningMode = new SparkScanScanningModeTarget(
    scanningBehavior: SparkScanScanningBehavior.Single,
    previewBehavior: SparkScanPreviewBehavior.Default);
```

`SparkScanScanningModeDefault` and `SparkScanScanningModeTarget` are constructed with `new` and both require `(SparkScanScanningBehavior, SparkScanPreviewBehavior)`. There is no parameterless constructor in the .NET binding.

To let users switch modes from the toolbar at runtime:

```csharp
sparkScanView.TargetModeButtonVisible = true;
```

### Tracking view state

```csharp
this.SparkScanView.ViewStateChanged += (sender, args) =>
{
    MainThread.BeginInvokeOnMainThread(() =>
    {
        switch (args.State)
        {
            case SparkScanViewState.Active:
                this.statusLabel.Text = "Scanning";
                break;
            default:
                this.statusLabel.Text = "Idle";
                break;
        }
    });
};
```

### Custom trigger button

Hide the built-in trigger and call `StartScanning()` / `PauseScanning()` from your own button:

```csharp
this.SparkScanView.TriggerButtonVisible = false;
this.myStartButton.Clicked += (_, _) => this.SparkScanView.StartScanning();
this.myPauseButton.Clicked += (_, _) => this.SparkScanView.PauseScanning();
```

### Showing toolbar buttons

All toolbar buttons default to invisible (except the torch). Enable each one, then listen for the corresponding event:

```csharp
this.SparkScanView.BarcodeCountButtonVisible = true;
this.SparkScanView.BarcodeCountButtonTapped += (s, e) => { /* navigate to Barcode Count page */ };

this.SparkScanView.BarcodeFindButtonVisible = true;
this.SparkScanView.BarcodeFindButtonTapped += (s, e) => { /* navigate to Barcode Find page */ };

this.SparkScanView.LabelCaptureButtonVisible = true; // dotnet.android 8.3+ / dotnet.ios 8.3+
this.SparkScanView.LabelCaptureButtonTapped += (s, e) => { /* navigate to Label Capture page */ };

this.SparkScanView.ScanningBehaviorButtonVisible = true; // toggle Single ↔ Continuous from toolbar
```

### Custom toast text

```csharp
viewSettings.ToastSettings = new SparkScanToastSettings
{
    ToastEnabled = true,
    TargetModeEnabledMessage = "Target mode on",
    ContinuousModeEnabledMessage = "Continuous mode",
    ScanPausedMessage = "Scanning paused",
};
```

Or show an ad-hoc toast:

```csharp
this.SparkScanView.ShowToast("Item added");
```

### CodeDuplicateFilter

The .NET SparkScan API uses `TimeSpan` directly — there are no `CodeDuplicate.DefaultDuplicateFilter` / `CodeDuplicate.ReportDataAndSymbologyOnlyOnce` sentinels here (those live on `BarcodeCaptureSettings`).

```csharp
settings.CodeDuplicateFilter = TimeSpan.FromMilliseconds(500);
settings.CodeDuplicateFilter = TimeSpan.FromSeconds(2.5);
settings.CodeDuplicateFilter = TimeSpan.Zero;  // every detection is reported
```

Set this **before** constructing the `SparkScan`. To change at runtime, mutate the settings and call `sparkScan.ApplySettingsAsync(settings)`.

### ScanIntention

```csharp
settings.ScanIntention = ScanIntention.Smart;   // default from 7.0
settings.ScanIntention = ScanIntention.Manual;
```

### BatterySaving

```csharp
settings.BatterySaving = BatterySavingMode.Auto;  // default
settings.BatterySaving = BatterySavingMode.Off;
settings.BatterySaving = BatterySavingMode.On;
```

### SparkScanLicenseInfo

After the SparkScan mode has been associated with a `DataCaptureContext` and the context has emitted `OnModeAdded`:

```csharp
SparkScanLicenseInfo? licenseInfo = this.SparkScan.SparkScanLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

Available from 6.22 onwards on both dotnet.android and dotnet.ios.

### Async work after a scan

```csharp
private async void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var data = args.Session.NewlyRecognizedBarcode?.Data;
    if (data == null) return;

    try
    {
        var result = await LookupAsync(data);
        MainThread.BeginInvokeOnMainThread(() => this.UpdateUi(result));
    }
    catch (Exception)
    {
        // Log; SparkScan keeps scanning regardless.
    }
}
```

> Unlike `BarcodeCapture`, you do **not** need to toggle `Enabled = false` around the lookup — SparkScan controls re-arm timing via the feedback delegate's `resumeCapturingDelay`.

### Re-enabling after a delay

If you want to pause scanning programmatically for a fixed delay (not via `SparkScanBarcodeErrorFeedback`), use one of:

```csharp
// Option A — async/await with Task.Delay:
MainThread.BeginInvokeOnMainThread(async () =>
{
    await Task.Delay(TimeSpan.FromMilliseconds(500));
    this.SparkScan.Enabled = true;
});

// Option B — Dispatcher.StartTimer (from inside a Page or anything with access to a Dispatcher):
Dispatcher.StartTimer(TimeSpan.FromMilliseconds(500), () =>
{
    this.SparkScan.Enabled = true;
    return false;
});

// Option C — Application.Current.Dispatcher.StartTimer (when no Page-level Dispatcher is in scope):
Application.Current!.Dispatcher.StartTimer(TimeSpan.FromMilliseconds(500), () =>
{
    this.SparkScan.Enabled = true;
    return false;
});
```

> **`MainThread.StartTimer` does not exist.** `StartTimer` is an extension method on `IDispatcher`.

## Key rules

1. **Fetch the SDK version from NuGet, do not guess** — WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` for the latest stable version before editing the `.csproj`. Skip `-beta`/`-preview`/`-rc` suffixes.
2. **Android `SupportedOSPlatformVersion` ≥ 24** — the MAUI template defaults to `21`; Scandit's Android AAR requires 24.
3. **Four NuGet packages** — `Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`. All four. Same version.
4. **Builder chain for SparkScan is `.UseScanditCore().UseScanditBarcode(c => c.AddSparkScanView())`** — `UseScanditCore` takes **no** configure lambda; `UseScanditBarcode` takes a configure lambda with `AddSparkScanView()` inside. This is the **opposite** of the BarcodeCapture MAUI builder.
5. **XAML namespace is `clr-namespace:Scandit.DataCapture.Barcode.Spark.UI.Maui;assembly=ScanditBarcodeCaptureMaui`** — assembly is `ScanditBarcodeCaptureMaui` (no dots), not the package id `Scandit.DataCapture.Barcode.Maui`.
6. **`<scandit:SparkScanView>` requires three bindable properties: `DataCaptureContext`, `SparkScan`, `SparkScanViewSettings`** — without all three the preview is black. The `Feedback` bindable property is optional.
7. **MAUI lifecycle on the SparkScan control** — call `this.SparkScanView.OnAppearing()` from the page's `OnAppearing`, `this.SparkScanView.OnDisappearing()` from `OnDisappearing`. Do **not** call the dotnet.android-only `OnPause`/`OnResume` or the dotnet.ios-only `PrepareScanning`/`StopScanning` from MAUI code — those are platform-specific and not surfaced on the MAUI control.
8. **`SparkScan` and `SparkScanSettings` use `new`** — `new SparkScan(settings)`, `new SparkScanSettings()`. Not `SparkScan.Create(...)`.
9. **Event API on the view model** — `sparkScan.BarcodeScanned += handler`. Listener has only two callbacks (`OnBarcodeScanned`, `OnSessionUpdated`); no `OnObservation*`.
10. **Background thread + `MainThread.BeginInvokeOnMainThread`** — `BarcodeScanned` and `GetFeedbackForBarcode` both run off the UI thread. Use `MainThread.BeginInvokeOnMainThread(() => …)` for UI updates. `MainThread.StartTimer` does not exist — `StartTimer` is on `IDispatcher`.
11. **Feedback delegate, eager construction** — build `SparkScanBarcodeSuccessFeedback` / `SparkScanBarcodeErrorFeedback` once in the page constructor, return cached instances from `GetFeedbackForBarcode`. Implementing `ISparkScanFeedbackDelegate` on the page (the MAUI sample's pattern) keeps things colocated.
12. **Camera permission** — `await Permissions.CheckStatusAsync<Permissions.Camera>()` + `await Permissions.RequestAsync<Permissions.Camera>()`. On iOS, set `NSCameraUsageDescription` in `Platforms/iOS/Info.plist`.
13. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter`, `TriggerButtonCollapseTimeout`, `InactiveStateTimeout`, `SparkScanBarcodeErrorFeedback.resumeCapturingDelay`.
14. **`DisplayAlertAsync`, not `DisplayAlert`** — the non-`Async` overload is obsolete in MAUI 9.
