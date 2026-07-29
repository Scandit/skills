# MatrixScan AR .NET MAUI Integration Guide

`BarcodeAr` is the multi-barcode AR scanning mode. It simultaneously tracks every barcode visible in the camera feed and overlays interactive highlights and annotations on each one in real time. The MAUI integration wraps the per-TFM `BarcodeArView` in a XAML `View` control (`Scandit.DataCapture.Barcode.Ar.UI.Maui.BarcodeArView`), with its own pre-built MAUI handler. Unlike `BarcodeBatch` in MAUI — which uses the generic `<scandit:DataCaptureView>` plus an overlay — `BarcodeAr` has a **dedicated MAUI control**, so there is no `DataCaptureView`, no overlay, and no manual camera wiring to do. The `BarcodeArView` manages its own camera and rendering internally; you only have to bind the context, mode, and view settings, and forward the page lifecycle.

The examples below follow the structure of the official Scandit MAUI samples (`SparkScan` MAUI sample structure, since SparkScan is the closest analogue: a MAUI control with bindable properties and a `ScannerModel` singleton). A `MainPage` (`ContentPage`) is wired to a `MainPageViewModel` through `BindingContext`, and a `ScannerModel` owns the `DataCaptureContext` and the `BarcodeAr`. You can collapse this into a single `ContentPage.xaml.cs` for small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `matrixscan-ar-net-android` (for `net*-android`) or `matrixscan-ar-net-ios` (for `net*-ios`). Those skills cover the non-MAUI workloads where `BarcodeArView` is `IDisposable` and constructed via `BarcodeArView.Create(parentView, ...)`. The MAUI binding is a completely different class.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all four packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` if only `8.4.0` is the latest stable. The latest stable version changes regularly — only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode.maui/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeAr` was first shipped on `dotnet.android` / `dotnet.ios` in **7.2**. If the latest stable somehow predates 7.2 (extremely unlikely today), stop and tell the user — the integration cannot proceed.

Then add **four** NuGet packages, pinned to that same version:

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable-from-nuget>" />
  <PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="<latest-stable-from-nuget>" />
</ItemGroup>
```

All four are required. The `*.Maui` packages provide the MAUI builder extensions, handlers, and the `<scandit:BarcodeArView>` XAML control; the plain packages provide the platform bindings they delegate to.

### Other prerequisites

- A `<UseMaui>true</UseMaui>` MAUI project targeting at least one of `net10.0-android` or `net10.0-ios`.
- **Android `SupportedOSPlatformVersion` must be at least `24`** — the MAUI template defaults to `21`, which is below Scandit's Android AAR minimum and produces a `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library` build error. If the `.csproj` has a lower value for the Android `SupportedOSPlatformVersion`, **update it to `24.0`** as part of the integration. iOS minimum is `15.0` (matches the MAUI template default):
  ```xml
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'ios'">15.0</SupportedOSPlatformVersion>
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">24.0</SupportedOSPlatformVersion>
  ```
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - **Android target:** MAUI's `Permissions.Camera` adds `android.permission.CAMERA` automatically when requested at build time. You can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
  - **iOS target:** add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` with a short user-facing description. Without it the app crashes on first camera access.
- **No manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` call is needed** — the MAUI builder extensions (`UseScanditCore` / `UseScanditBarcode` below) perform this initialization on SDK 8.0+. This is different from the non-MAUI `matrixscan-ar-net-android` / `matrixscan-ar-net-ios` skills, which require the calls in `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`. In a MAUI app, leave `Platforms/Android/MainApplication.cs` and `Platforms/iOS/AppDelegate.cs` as the MAUI template generates them.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves tracking performance and accuracy.

Once the user responds, ask which `ContentPage` they'd like to integrate `BarcodeAr` into. Then write the integration code directly into that page (and supporting files). Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**
1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version (skip `-beta.*` / `-preview.*` / `-rc.*`). Do not skip this step — versions from training data are stale and will fail `dotnet restore` with `NU1103`.
2. Add all four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`) to the `.csproj`, all pinned to that same version.
3. If the `.csproj` targets `net*-android` with `SupportedOSPlatformVersion` below `24`, bump it to `24.0`. The MAUI template defaults to `21.0`, which fails the build because Scandit's Android AAR requires API 24+.
4. Update `MauiProgram.cs` to call `.UseScanditCore().UseScanditBarcode(configure => configure.AddBarcodeArView())`. (**This is the SparkScan-shaped MAUI builder, not the BarcodeBatch-shaped one — see Step 1.**)
5. Add the `<scandit:...>` XAML namespace and the `<scandit:BarcodeArView>` element to the page, with `DataCaptureContext`, `BarcodeAr`, and `BarcodeArViewSettings` all bound.
6. For iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. For Android: rely on `Permissions.Camera` (MAUI auto-adds the manifest entry) or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Forward `OnAppearing` → `barcodeArView.OnResume(); barcodeArView.Start();` and `OnDisappearing` → `barcodeArView.Stop(); barcodeArView.OnPause();` in the page code-behind.
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Namespaces

| Class | Namespace |
|-------|-----------|
| `BarcodeAr`, `BarcodeArSettings`, `IBarcodeArListener`, `BarcodeArSession`, `BarcodeArEventArgs` | `Scandit.DataCapture.Barcode.Ar.Capture` |
| `BarcodeArFeedback` | `Scandit.DataCapture.Barcode.Ar.Feedback` |
| `BarcodeArViewSettings`, `HighlightForBarcodeTappedEventArgs` | `Scandit.DataCapture.Barcode.Ar.UI` |
| `BarcodeArView` (MAUI XAML control) | `Scandit.DataCapture.Barcode.Ar.UI.Maui` |
| Highlights (`IBarcodeArHighlight`, `IBarcodeArHighlightProvider`, `BarcodeArRectangleHighlight`, `BarcodeArCircleHighlight`, `BarcodeArCircleHighlightPreset`) | `Scandit.DataCapture.Barcode.Ar.UI.Highlight` |
| Annotations base (`IBarcodeArAnnotation`, `IBarcodeArAnnotationProvider`, `BarcodeArStatusIconAnnotation`, `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArPopoverAnnotationButton`, `BarcodeArAnnotationTrigger`, `IBarcodeArPopoverAnnotationListener`) | `Scandit.DataCapture.Barcode.Ar.UI.Annotations` |
| Info-annotation sub-package (`BarcodeArInfoAnnotationBodyComponent`, `BarcodeArInfoAnnotationHeader`, `BarcodeArInfoAnnotationFooter`, `BarcodeArInfoAnnotationAnchor`, `BarcodeArInfoAnnotationWidthPreset`, `IBarcodeArInfoAnnotationListener`) | `Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info` |
| `TrackedBarcode` | `Scandit.DataCapture.Barcode.Batch.Data` |
| `Symbology`, `Barcode`, `SymbologyDescription` | `Scandit.DataCapture.Barcode.Data` |
| `DataCaptureContext` | `Scandit.DataCapture.Core.Capture` |
| `CameraSettings`, `CameraPosition` | `Scandit.DataCapture.Core.Source` |
| `IFrameData` | `Scandit.DataCapture.Core.Data` |
| `Brush` | `Scandit.DataCapture.Core.UI.Style` |
| `Anchor` | `Scandit.DataCapture.Core.Common.Geometry` |
| `UseScanditCore`, `UseScanditBarcode` (extension methods) | bring in via `using Scandit.DataCapture.Core;` and `using Scandit.DataCapture.Barcode;` |

## Step 1 — Register MAUI builder extensions

In `MauiProgram.cs`, chain the Scandit builder extensions:

```csharp
using Scandit.DataCapture.Core;          // UseScanditCore (extension)
using Scandit.DataCapture.Barcode;       // UseScanditBarcode (extension); ScanditBarcodeCaptureMauiBuilder.AddBarcodeArView()

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
                configure.AddBarcodeArView();
            });

        return builder.Build();
    }
}
```

- `UseScanditCore()` takes **no** configure lambda for BarcodeAr. (`BarcodeBatch`'s MAUI integration uses `UseScanditCore(c => c.AddDataCaptureView())` — that's a different mode that needs the generic `DataCaptureView`. BarcodeAr has its own dedicated MAUI control, so this is unnecessary.)
- `UseScanditBarcode(c => c.AddBarcodeArView())` registers the BarcodeAr MAUI handler — without this call, the `<scandit:BarcodeArView>` element renders as a blank placeholder because MAUI has no handler to instantiate for it. The `configure` lambda is **required** for BarcodeAr.

> **Common mistake:** writing `UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`. That is the BarcodeBatch MAUI builder chain — `AddBarcodeArView()` is not on the `UseScanditCore` configure surface, and BarcodeAr does not use `<scandit:DataCaptureView>`. If both BarcodeBatch and BarcodeAr coexist in the same app, you need both `AddDataCaptureView()` (under `UseScanditCore`) **and** `AddBarcodeArView()` (under `UseScanditBarcode`):
>
> ```csharp
> .UseScanditCore(c => c.AddDataCaptureView())
> .UseScanditBarcode(c => c.AddBarcodeArView());
> ```

> **Do not** add `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` calls to `MainApplication.OnCreate` or `AppDelegate.FinishedLaunching`. `UseScanditCore()` / `UseScanditBarcode(...)` invoke them as part of the builder chain. The standard MAUI platform shims should remain untouched.

## Step 2 — Build a ScannerModel (DataCaptureContext + BarcodeAr)

In MAUI it's idiomatic to factor `BarcodeAr` creation into a singleton service so the same `BarcodeAr` instance is shared across page lifecycles. The official MAUI samples use a `Lazy<T>` initialized on first access — that pattern is reproduced here.

`Models/ScannerModel.cs`:

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Models;

public class ScannerModel
{
    // Enter your Scandit License key here.
    // Your Scandit License key is available via your Scandit SDK web account.
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private static readonly Lazy<ScannerModel> instance =
        new(() => new ScannerModel(), LazyThreadSafetyMode.PublicationOnly);

    public static ScannerModel Instance => instance.Value;

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeAr BarcodeAr { get; }
    public BarcodeArSettings BarcodeArSettings { get; }
    public BarcodeArViewSettings ViewSettings { get; } = new();

    private ScannerModel()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.BarcodeArSettings = new BarcodeArSettings();

        // The settings instance initially has all symbologies disabled.
        // Enable only what your app actually needs — fewer symbologies means faster tracking.
        HashSet<Symbology> symbologies = new()
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
            Symbology.Qr,
        };
        this.BarcodeArSettings.EnableSymbologies(symbologies);

        // Optional: adjust active symbol counts for variable-length 1D symbologies.
        this.BarcodeArSettings.GetSymbologySettings(Symbology.Code128).ActiveSymbolCounts =
            new short[] { 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };

        this.BarcodeAr = new BarcodeAr(this.DataCaptureContext, this.BarcodeArSettings);
    }
}
```

> `BarcodeAr` uses a **direct constructor** (`new BarcodeAr(context, settings)`), not a `Create(...)` factory. `BarcodeArSettings` is also a plain `new`. `DataCaptureContext.ForLicenseKey(key)` still uses the factory form — it lives in Core, not BarcodeAr.

> Alternative: register `ScannerModel` (or an `IScannerModel` interface) via DI in `MauiProgram.cs` with `builder.Services.AddSingleton<ScannerModel>()` and inject it into the view model constructor. Both approaches work.

### BarcodeArSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new BarcodeArSettings()` | constructor | All symbologies disabled. |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `GetSymbologySettings(Symbology)` | method | Returns the per-symbology `SymbologySettings` (`ActiveSymbolCounts`, checksum config, etc.). |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `ExpectsOnlyUniqueBarcodes` | `bool` (get/set) | When `true`, the engine assumes each barcode appears once and optimizes accordingly. |
| `SetProperty(string, object)` / `GetProperty(string)` / `GetProperty<T>(string)` / `TryGetProperty<T>(string, out T?)` | methods | Read/write experimental engine flags. |

> Symbology names are C# PascalCase. The full set includes `Ean13Upca`, `Ean8`, `Upce`, `Code39`, `Code93`, `Code128`, `InterleavedTwoOfFive`, `Qr`, `DataMatrix`, `Pdf417`, `Aztec`, `Codabar`, and more. Don't use Kotlin-style underscore names (`EAN13_UPCA`) or Swift-style camelCase (`ean13UPCA`).

### BarcodeAr members

| Member | Description |
|--------|-------------|
| `new BarcodeAr(DataCaptureContext? context, BarcodeArSettings settings)` | Constructor — creates the mode and attaches it to the context. |
| `Feedback` | `BarcodeArFeedback` (get/set) — sound / vibration for scan and tap events. See Step 8. |
| `ApplySettingsAsync(BarcodeArSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(IBarcodeArListener)` / `RemoveListener(IBarcodeArListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeArEventArgs> SessionUpdated` | Raised on every processed frame. **Recommended** in idiomatic C#. |
| `static CameraSettings RecommendedCameraSettings` | Get the recommended camera settings (used implicitly when the MAUI view's `CameraSettings` is left null). |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the event — not both for the same handler.** They both fire `OnSessionUpdated`/`SessionUpdated`; subscribing to both leads to double-processing.

## Step 3 — Configure BarcodeArViewSettings (optional)

`BarcodeArViewSettings` is intentionally minimal. It only exposes three properties; if all you want is the defaults, you can leave the `ViewSettings = new();` line in the `ScannerModel` (or the view model) untouched.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Core.Source;

public BarcodeArViewSettings ViewSettings { get; } = new()
{
    SoundEnabled = true,                                  // beep on each tracked barcode (default true)
    HapticEnabled = true,                                 // vibrate on each tracked barcode (default true)
    DefaultCameraPosition = CameraPosition.WorldFacing,   // default; or UserFacing for the selfie camera
};
```

### BarcodeArViewSettings properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `SoundEnabled` | `bool` | `true` | Whether a beep plays on each tracked barcode. |
| `HapticEnabled` | `bool` | `true` | Whether haptics fire on each tracked barcode. |
| `DefaultCameraPosition` | `CameraPosition` | `WorldFacing` | Camera position to open on start. |

> `BarcodeArViewSettings` does **not** expose `TriggerButtonCollapseTimeout`, `InactiveStateTimeout`, `ToastSettings`, `DefaultMiniPreviewSize`, or `DefaultScanningMode` — those are SparkScan properties. Do not invent them on this type.

## Step 4 — Build a ViewModel that exposes the bindables

The `<scandit:BarcodeArView>` XAML control needs `DataCaptureContext`, `BarcodeAr`, and `BarcodeArViewSettings` to be bound. The view model wires the `SessionUpdated` event on the cross-platform `BarcodeAr` mode (or implements `IBarcodeArListener`).

`ViewModels/MainPageViewModel.cs`:

```csharp
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

using MyApp.Models;
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.ViewModels;

public class MainPageViewModel : INotifyPropertyChanged
{
    public DataCaptureContext DataCaptureContext { get; } = ScannerModel.Instance.DataCaptureContext;
    public BarcodeAr BarcodeAr { get; } = ScannerModel.Instance.BarcodeAr;
    public BarcodeArViewSettings ViewSettings { get; } = ScannerModel.Instance.ViewSettings;

    public ObservableCollection<string> ScanResults { get; } = new();
    public string ItemCount => $"{this.ScanResults.Count} items";

    public event PropertyChangedEventHandler? PropertyChanged;

    public MainPageViewModel()
    {
        // The SessionUpdated event runs on a background recognition thread.
        // We marshal UI work back to the main thread inside the handler.
        this.BarcodeAr.SessionUpdated += this.OnSessionUpdated;
    }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        // Copy the data you need before scheduling the main-thread dispatch.
        // Do not retain the session itself — it's only safe to read inside this callback.
        var added = args.Session.AddedTrackedBarcodes
            .Where(tb => tb.Barcode != null)
            .Select(tb => $"{new SymbologyDescription(tb.Barcode.Symbology).ReadableName} — {tb.Barcode.Data}")
            .ToList();

        if (added.Count == 0) return;

        MainThread.BeginInvokeOnMainThread(() =>
        {
            foreach (var line in added) this.ScanResults.Add(line);
            this.OnPropertyChanged(nameof(this.ItemCount));
        });
    }

    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
```

### IBarcodeArListener (alternative to the event)

If the project prefers the listener interface over the event, implement it on the view model. **`IBarcodeArListener` has only one method** — there are no `OnObservationStarted` / `OnObservationStopped` callbacks (unlike Kotlin / Swift):

```csharp
public class MainPageViewModel : INotifyPropertyChanged, IBarcodeArListener
{
    // …

    public void OnSessionUpdated(BarcodeAr barcodeAr, BarcodeArSession session, IFrameData frameData)
    {
        var added = session.AddedTrackedBarcodes.ToList();
        if (added.Count == 0) return;
        MainThread.BeginInvokeOnMainThread(() => { /* update UI */ });
    }
}

// In the constructor:
this.BarcodeAr.AddListener(this);
```

### BarcodeArSession members

| Member | Type | Description |
|--------|------|-------------|
| `AddedTrackedBarcodes` | `IReadOnlyList<TrackedBarcode>` | Barcodes that entered the view in this frame. |
| `RemovedTrackedBarcodes` | `IReadOnlyList<int>` | Tracking IDs of barcodes that left the view in this frame. |
| `TrackedBarcodes` | `IReadOnlyDictionary<int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `Reset()` | method | Reset all tracked state. Only call from inside a listener / event callback. |

> **Do not hold references to `BarcodeArSession` or its collections outside `OnSessionUpdated`.** The session is mutated by the recognition thread on the next frame. Copy any data you need out before dispatching to the main thread.

### BarcodeArEventArgs

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeAr` | `BarcodeAr` | The capture mode that raised the event. |
| `Session` | `BarcodeArSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. |

### TrackedBarcode

`TrackedBarcode` lives in `Scandit.DataCapture.Barcode.Batch.Data` (yes, in the **Batch** sub-namespace — it's reused across BarcodeBatch and BarcodeAr).

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` | The decoded barcode — access `.Data`, `.Symbology`, etc. |
| `Identifier` | `int` | Unique tracking ID for this barcode (stable across frames). |
| `Location` | `Quadrilateral` | Position in image-space coordinates. |

## Step 5 — Add the BarcodeArView in XAML

`Scandit.DataCapture.Barcode.Ar.UI.Maui.BarcodeArView` is a MAUI `View` with bindable properties `DataCaptureContext`, `BarcodeAr`, `BarcodeArViewSettings`, and (optionally) `CameraSettings`. Add the XAML namespace and place the control on the page; bind its three required properties to the view model.

`Views/MainPage.xaml`:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Barcode.Ar.UI.Maui;assembly=ScanditBarcodeCaptureMaui"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage"
             x:DataType="vm:MainPageViewModel"
             Title="MatrixScan AR">
    <ContentPage.BindingContext>
        <vm:MainPageViewModel x:Name="ViewModel" />
    </ContentPage.BindingContext>

    <ContentPage.Content>
        <AbsoluteLayout>
            <scandit:BarcodeArView
                x:Name="BarcodeArView"
                AbsoluteLayout.LayoutBounds="0,0,1,1"
                AbsoluteLayout.LayoutFlags="All"
                DataCaptureContext="{Binding DataCaptureContext}"
                BarcodeAr="{Binding BarcodeAr}"
                BarcodeArViewSettings="{Binding ViewSettings}" />
        </AbsoluteLayout>
    </ContentPage.Content>
</ContentPage>
```

> ⚠️ **All three of `DataCaptureContext`, `BarcodeAr`, and `BarcodeArViewSettings` are mandatory.** Without any one of them bound, the preview is black and tracking never starts. Setting `x:Name="BarcodeArView"` does **not** wire anything by itself — the bindings are separate and required.

> ⚠️ **Namespace assembly is `ScanditBarcodeCaptureMaui`, not `Scandit.DataCapture.Barcode.Maui`.** The NuGet package id has dots; the produced assembly file does not. Easy to get wrong by copy-pasting the package id.

> ⚠️ **`x:Name="BarcodeArView"` auto-generates a code-behind field — do not redeclare it.** MAUI's XAML source generator produces a strongly-typed field for any element with `x:Name`, so the code-behind can already write `this.BarcodeArView.OnAppearing()` / `this.BarcodeArView.HighlightProvider = …` directly. Adding your own `private BarcodeArView BarcodeArView` (or property) in `MainPage.xaml.cs` produces a `CS0102` "type already contains a definition" error.

> The bindable properties for `DataCaptureContext`, `BarcodeAr`, `BarcodeArViewSettings`, and `CameraSettings` are `BindingMode.OneTime`. They are read once during handler initialization and not re-read if the binding source raises `PropertyChanged` afterwards. The provider properties (`HighlightProvider`, `AnnotationProvider`) and the boolean / position properties for the built-in controls are `BindingMode.TwoWay` and can be reassigned at runtime.

### BarcodeArView (MAUI control) members

| Member | Description |
|--------|-------------|
| `DataCaptureContext` | Bindable property (OneTime) — set to the page/VM's `DataCaptureContext`. **Required.** |
| `BarcodeAr` | Bindable property (OneTime) — set to the page/VM's `BarcodeAr`. **Required.** |
| `BarcodeArViewSettings` | Bindable property (OneTime) — set to the page/VM's `BarcodeArViewSettings`. **Required.** |
| `CameraSettings` | Bindable property (OneTime) — optional `CameraSettings`. Leave unbound to use `BarcodeAr.RecommendedCameraSettings`. |
| `HighlightProvider` | Bindable property (TwoWay) — `IBarcodeArHighlightProvider?`. Supplies a highlight per tracked barcode. If `null`, a default rectangle highlight is shown. |
| `AnnotationProvider` | Bindable property (TwoWay) — `IBarcodeArAnnotationProvider?`. Supplies an annotation per tracked barcode. If `null`, no annotation is shown. |
| `ShouldShowTorchControl` | Bindable property (bool, default `false`) — render the built-in torch toggle button. |
| `ShouldShowZoomControl` | Bindable property (bool, default `false`) — render the built-in zoom switch button. |
| `ShouldShowCameraSwitchControl` | Bindable property (bool, default `false`) — render the camera-switch button. |
| `TorchControlPosition` / `ZoomControlPosition` / `CameraSwitchControlPosition` | Bindable properties (`Anchor`, default `TopRight`) — where each control sits. |
| `Start()` | Begin tracking. Safe to call before the handler attaches — the call is queued and replayed on `HandlerReady`. |
| `Stop()` | Stop tracking and clear all overlays. |
| `Pause()` | Pause tracking (keeps overlays and camera attached). |
| `Reset()` | Clear all current highlights/annotations and re-query the providers for each tracked barcode. |
| `OnResume()` | Android-only effect; safe no-op on iOS (gated by `#if __ANDROID__` in the handler's command-mapper). Required for correct camera lifecycle on Android. |
| `OnPause()` | Android-only effect; safe no-op on iOS. Required for correct camera lifecycle on Android. |
| `event HighlightForBarcodeTapped` | Fires when the user taps a highlight. See Step 9. |
| `event HandlerReady` | Fires when the MAUI handler has attached the native view. All queued commands are replayed before this fires. |
| `GetNotificationPresenter()` | Returns the `INotificationPresenter` for in-view notifications (8.5+). Throws if called before the handler is attached. |
| `PendingCommandCount` | `int` (get) — number of queued commands waiting for the handler. Diagnostic; rarely needed. |
| `ClearPendingCommands()` | Drops any queued `Start/Stop/Pause/Reset/OnResume/OnPause` commands without executing them. |

> ❌ **Not in MAUI:** `ShouldShowMacroModeControl` and `MacroModeControlPosition`. They exist on the iOS native binding but are **not** surfaced as MAUI bindable properties. Do not set them from MAUI XAML or MAUI code — there is no property to set. If macro-mode is required on iOS, the `matrixscan-ar-net-ios` skill (non-MAUI .NET iOS) is the right tool.

> ❌ **Not in MAUI:** `BarcodeArView.Create(parentView, ...)`. The factory lives in the per-TFM `Scandit.DataCapture.Barcode.Ar.UI` namespace — the MAUI `Scandit.DataCapture.Barcode.Ar.UI.Maui.BarcodeArView` uses constructors (`new BarcodeArView()`, `new BarcodeArView(context, barcodeAr, settings)`, `new BarcodeArView(context, barcodeAr, settings, cameraSettings)`) and is typically declared in XAML rather than instantiated in code.

## Step 6 — Page code-behind: lifecycle

The page forwards `OnAppearing` / `OnDisappearing` into the `BarcodeArView`. On both platforms, you need to call **both** `OnResume()` / `OnPause()` and `Start()` / `Stop()` to drive the camera and tracking lifecycle correctly. The `OnResume()` / `OnPause()` calls are no-ops on iOS (the handler's command-mapper gates them with `#if __ANDROID__`), so the same code is portable.

`Views/MainPage.xaml.cs`:

```csharp
namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public MainPage()
    {
        this.InitializeComponent();
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();

        // Request the camera permission BEFORE starting the BarcodeArView.
        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted)
            {
                // Surface a message to the user and do not start the view.
                return;
            }
        }

        // OnResume() is an Android-only effect (no-op on iOS) — call both anyway.
        this.BarcodeArView.OnResume();
        this.BarcodeArView.Start();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.BarcodeArView.Stop();
        this.BarcodeArView.OnPause();
    }
}
```

> The `BarcodeArView` queues `Start()` / `Stop()` / `OnResume()` / `OnPause()` calls until its handler attaches — calling them in `OnAppearing` (even on the very first navigation, before the handler has had a chance to spin up) is safe. The internal `ConcurrentQueue<PendingCommand>` flushes on `HandlerReady`.

## Step 7 — Highlights

Highlights are visual overlays drawn over each tracked barcode. Implement `IBarcodeArHighlightProvider` and assign it to `barcodeArView.HighlightProvider` (in code-behind) or bind to a view-model property (in XAML).

**The .NET provider is async.** It returns `Task<IBarcodeArHighlight?>` — there is **no** `Callback` parameter and **no** `callback.OnData(...)` method (those are the Kotlin pattern). Return `null` (or `Task.FromResult<IBarcodeArHighlight?>(null)`) to hide a barcode entirely.

Highlight constructors take only the `Barcode` — no `Context` / `UIView` argument.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Data;

public sealed class RectangleHighlightProvider : IBarcodeArHighlightProvider
{
    public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode)
    {
        IBarcodeArHighlight highlight = new BarcodeArRectangleHighlight(barcode);
        return Task.FromResult<IBarcodeArHighlight?>(highlight);
    }
}
```

Assign in code-behind (typical):

```csharp
public MainPage()
{
    this.InitializeComponent();
    this.BarcodeArView.HighlightProvider = new RectangleHighlightProvider();
}
```

…or expose the provider as a view-model property and bind it in XAML:

```csharp
// In the view model:
public IBarcodeArHighlightProvider HighlightProvider { get; } = new RectangleHighlightProvider();
```

```xml
<scandit:BarcodeArView
    DataCaptureContext="{Binding DataCaptureContext}"
    BarcodeAr="{Binding BarcodeAr}"
    BarcodeArViewSettings="{Binding ViewSettings}"
    HighlightProvider="{Binding HighlightProvider}" />
```

Either is fine — the bindable property is `BindingMode.TwoWay`. Choose the pattern that matches the rest of the project.

### Built-in highlight types

**`BarcodeArRectangleHighlight`** — rectangular overlay matched to the barcode shape:
```csharp
var highlight = new BarcodeArRectangleHighlight(barcode);
highlight.Brush = new Brush(fillColor, strokeColor, strokeWidth);  // optional
highlight.Icon = myScanditIcon;                                    // optional
```

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` (get) | The barcode this highlight is bound to. |
| `Brush` | `Brush` (get/set) | Fill / stroke style. |
| `Icon` | `ScanditIcon?` (get/set) | Optional icon rendered inside the rectangle. |

**`BarcodeArCircleHighlight`** — circular dot or icon overlay. Always takes a `BarcodeArCircleHighlightPreset` (no parameterless overload):
```csharp
var highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
// or BarcodeArCircleHighlightPreset.Icon for an icon-style circle
highlight.Size = 24f;                          // optional
highlight.Brush = new Brush(/* … */);          // optional
highlight.Icon = myScanditIcon;                // optional (used with the Icon preset)
```

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` (get) | |
| `Brush` | `Brush` (get/set) | |
| `Icon` | `ScanditIcon?` (get/set) | |
| `Size` | `float` (get/set) | Circle diameter in dp (minimum 18). |

`BarcodeArCircleHighlightPreset` is an enum: `Dot` (default-styled solid dot) or `Icon` (icon-centered circle).

Returning `null` from `HighlightForBarcodeAsync` hides the highlight for that specific barcode (the barcode is still tracked, just not visually marked).

## Step 8 — Annotations

Annotations are floating tooltips, status icons, or panels displayed alongside a tracked barcode. Implement `IBarcodeArAnnotationProvider` and assign it to `barcodeArView.AnnotationProvider`. The provider is **async**, the same pattern as highlights.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;
using Scandit.DataCapture.Barcode.Data;

public sealed class InfoAnnotationProvider : IBarcodeArAnnotationProvider
{
    public Task<IBarcodeArAnnotation?> AnnotationForBarcodeAsync(Barcode barcode)
    {
        var annotation = new BarcodeArInfoAnnotation(barcode)
        {
            Body = new List<BarcodeArInfoAnnotationBodyComponent>
            {
                new BarcodeArInfoAnnotationBodyComponent { Text = barcode.Data ?? string.Empty },
            },
        };
        return Task.FromResult<IBarcodeArAnnotation?>(annotation);
    }
}

// Assign:
this.BarcodeArView.AnnotationProvider = new InfoAnnotationProvider();
```

### Built-in annotation types

All three types take only the `Barcode` in the constructor (no `Context` / `UIViewController`).

| Type | Constructor | Description |
|------|-------------|-------------|
| `BarcodeArStatusIconAnnotation` | `(Barcode)` | Compact icon that expands to text on tap. |
| `BarcodeArInfoAnnotation` | `(Barcode)` | Structured tooltip with optional header, body rows, and footer. |
| `BarcodeArPopoverAnnotation` | `(Barcode, IList<BarcodeArPopoverAnnotationButton>)` | A row of icon+text action buttons. (See `references/advanced.md`.) |

**`BarcodeArStatusIconAnnotation` properties:**

| Property | Type | Description |
|----------|------|-------------|
| `Icon` | `ScanditIcon` (get/set) | Collapsed-state icon. |
| `Text` | `string?` (get/set) | Expanded-state text (max ~20 chars). `null` = no expand. |
| `BackgroundColor` | `Color` (get/set) | Annotation background color. |
| `TextColor` | `Color` (get/set) | Expanded text color. |
| `HasTip` | `bool` (get/set) | Show the pointer toward the barcode. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | When the annotation becomes visible: `HighlightTapAndBarcodeScan` (default) or `HighlightTap`. |
| `Barcode` | `Barcode` (get) | |

**`BarcodeArInfoAnnotation` properties:**

| Property | Type | Description |
|----------|------|-------------|
| `Body` | `IReadOnlyCollection<BarcodeArInfoAnnotationBodyComponent>` (get/set) | Body rows. |
| `Header` | `BarcodeArInfoAnnotationHeader?` (get/set) | Optional header. |
| `Footer` | `BarcodeArInfoAnnotationFooter?` (get/set) | Optional footer. |
| `Width` | `BarcodeArInfoAnnotationWidthPreset` (get/set) | `Small`, `Medium`, or `Large`. |
| `Anchor` | `BarcodeArInfoAnnotationAnchor` (get/set) | `Left`, `Right`, `Bottom`, or `Top`. |
| `HasTip` | `bool` (get/set) | Show the pointer toward the barcode. |
| `EntireAnnotationTappable` | `bool` (get/set) | If `true`, taps anywhere on the annotation fire `OnInfoAnnotationTapped`. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | |
| `BackgroundColor` | `Color` (get/set) | |
| `Listener` | `IBarcodeArInfoAnnotationListener?` (get/set) | Receives tap events for header / footer / icons / body. See `references/advanced.md`. |
| `Barcode` | `Barcode` (get) | |

`BarcodeArInfoAnnotationBodyComponent` (in the `Info` sub-package) has its own properties: `Text`, `TextColor`, `TextSize`, `Typeface`, `StyledTextFormatted`, `LeftIcon`, `RightIcon`, `LeftIconTappable`, `RightIconTappable`, `TextAlignment`.

`BarcodeArInfoAnnotationHeader`: `Text`, `TextSize`, `Typeface`, `TextColor`, `Icon`, `BackgroundColor`.
`BarcodeArInfoAnnotationFooter`: `Text`, `TextSize`, `Typeface`, `TextColor`, `Icon`, `BackgroundColor`.

For popover annotations, listener interfaces, and per-button tap routing → see `references/advanced.md`.

Returning `null` from `AnnotationForBarcodeAsync` simply omits the annotation for that barcode.

## Step 9 — Tap interactions on highlights

The MAUI `BarcodeArView` exposes tap events as a C# event. There is **no `UiListener` / `UIDelegate` property** — use the event:

```csharp
public MainPage()
{
    this.InitializeComponent();
    this.BarcodeArView.HighlightForBarcodeTapped += this.OnHighlightTapped;
}

private void OnHighlightTapped(object? sender, HighlightForBarcodeTappedEventArgs args)
{
    // args.BarcodeAr, args.Barcode, args.Highlight
    var data = args.Barcode.Data;
    MainThread.BeginInvokeOnMainThread(() =>
    {
        // open detail screen, navigate, show modal, etc.
    });
}
```

> The `HighlightForBarcodeTapped` event's `add` / `remove` accessors are gated by `#if __ANDROID__ || __IOS__` inside the MAUI control — on TFMs that don't ship a handler the accessors silently no-op rather than throwing. Subscribing from cross-platform code is always safe to compile.

`HighlightForBarcodeTappedEventArgs` exposes:

| Property | Type |
|----------|------|
| `BarcodeAr` | `BarcodeAr` |
| `Barcode` | `Barcode` |
| `Highlight` | `IBarcodeArHighlight` |

## Complete minimal example (single-page variant)

If the project is small and does not justify a dedicated ViewModel / Manager, this is a compact `ContentPage.xaml` + `.xaml.cs` that works end-to-end.

`Views/MainPage.xaml`:

```xml
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Barcode.Ar.UI.Maui;assembly=ScanditBarcodeCaptureMaui"
             x:Class="MyApp.Views.MainPage">
    <AbsoluteLayout>
        <scandit:BarcodeArView
            x:Name="BarcodeArView"
            AbsoluteLayout.LayoutBounds="0,0,1,1"
            AbsoluteLayout.LayoutFlags="All"
            DataCaptureContext="{Binding DataCaptureContext}"
            BarcodeAr="{Binding BarcodeAr}"
            BarcodeArViewSettings="{Binding ViewSettings}" />
    </AbsoluteLayout>
</ContentPage>
```

`Views/MainPage.xaml.cs`:

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeAr BarcodeAr { get; }
    public BarcodeArViewSettings ViewSettings { get; } = new();

    public MainPage()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        var settings = new BarcodeArSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
            Symbology.Qr,
        });

        this.BarcodeAr = new BarcodeAr(this.DataCaptureContext, settings);
        this.BarcodeAr.SessionUpdated += this.OnSessionUpdated;

        this.BindingContext = this;
        this.InitializeComponent();

        this.BarcodeArView.HighlightProvider = new RectangleProvider();
        this.BarcodeArView.HighlightForBarcodeTapped += (s, e) =>
            MainThread.BeginInvokeOnMainThread(() => { /* react to tap */ _ = e.Barcode.Data; });
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

        this.BarcodeArView.OnResume();
        this.BarcodeArView.Start();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.BarcodeArView.Stop();
        this.BarcodeArView.OnPause();
    }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        var added = args.Session.AddedTrackedBarcodes.ToList();
        if (added.Count == 0) return;

        MainThread.BeginInvokeOnMainThread(() =>
        {
            foreach (TrackedBarcode tracked in added)
            {
                _ = tracked.Barcode.Data;
            }
        });
    }

    private sealed class RectangleProvider : IBarcodeArHighlightProvider
    {
        public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
            Task.FromResult<IBarcodeArHighlight?>(new BarcodeArRectangleHighlight(barcode));
    }
}
```

## Optional configuration

### Customize feedback (BarcodeArFeedback)

`BarcodeAr` plays a beep and vibrates by default. To customize:

```csharp
using Scandit.DataCapture.Barcode.Ar.Feedback;

// Silent — no beep, no vibration:
this.BarcodeAr.Feedback = new BarcodeArFeedback();

// Restore defaults:
this.BarcodeAr.Feedback = BarcodeArFeedback.DefaultFeedback;
```

`BarcodeArFeedback` exposes two `Core.Common.Feedback.Feedback` slots:

| Property | Type | Description |
|----------|------|-------------|
| `Scanned` | `Feedback` | Played when a barcode enters tracking. |
| `Tapped` | `Feedback` | Played when a highlight is tapped. |

For custom compositions (e.g. silent-on-scan but vibrate-on-tap), see `references/advanced.md`.

> `BarcodeArFeedback.DefaultFeedback` is a **static property** in .NET — not the Kotlin `defaultFeedback()` method or the Swift `default()` method. Calling it with parentheses (`BarcodeArFeedback.DefaultFeedback()`) is a compile error.

### Show built-in controls (torch, zoom, camera switch)

You can set these from XAML (the bindable properties are `TwoWay`):

```xml
<scandit:BarcodeArView
    x:Name="BarcodeArView"
    DataCaptureContext="{Binding DataCaptureContext}"
    BarcodeAr="{Binding BarcodeAr}"
    BarcodeArViewSettings="{Binding ViewSettings}"
    ShouldShowTorchControl="True"
    TorchControlPosition="TopLeft"
    ShouldShowZoomControl="True"
    ZoomControlPosition="BottomRight"
    ShouldShowCameraSwitchControl="True"
    CameraSwitchControlPosition="TopRight" />
```

…or from code-behind:

```csharp
using Scandit.DataCapture.Core.Common.Geometry;

this.BarcodeArView.ShouldShowTorchControl = true;
this.BarcodeArView.TorchControlPosition = Anchor.TopLeft;
```

`ShouldShowTorchControl`, `ShouldShowZoomControl`, and `ShouldShowCameraSwitchControl` all default to `false`. `*Position` properties default to `Anchor.TopRight` on the MAUI control.

> **No `ShouldShowMacroModeControl` on the MAUI control.** The macro-mode toggle exists on the native iOS binding but is not surfaced as a MAUI bindable property. Do not add `ShouldShowMacroModeControl="True"` to XAML — it will fail to resolve at runtime.

### Switch to circle highlights

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;

public sealed class DotProvider : IBarcodeArHighlightProvider
{
    public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
        Task.FromResult<IBarcodeArHighlight?>(
            new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot));
}

// Assign:
this.BarcodeArView.HighlightProvider = new DotProvider();
```

### Reset overlays

When the displayed information needs to be re-computed (e.g. the user switched filters in the app), call:

```csharp
this.BarcodeArView.Reset();
```

This clears all current highlights and annotations and re-invokes both providers for every currently tracked barcode.

### Apply settings at runtime

```csharp
var updated = new BarcodeArSettings();
updated.EnableSymbology(Symbology.Qr, true);
await this.BarcodeAr.ApplySettingsAsync(updated);
```

### Async work in the session handler

When responding to a scanned barcode requires a network or database call, do not block the recognition thread:

```csharp
private async void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
{
    foreach (TrackedBarcode tracked in args.Session.AddedTrackedBarcodes)
    {
        try
        {
            var info = await this.LookupAsync(tracked.Barcode.Data!);
            MainThread.BeginInvokeOnMainThread(() => this.UpdateUi(tracked.Identifier, info));
        }
        catch (Exception)
        {
            // Log; BarcodeAr keeps tracking regardless.
        }
    }
}
```

> `async void` is acceptable on event handlers (the signature is `void`). Provider methods (`HighlightForBarcodeAsync`, `AnnotationForBarcodeAsync`) return `Task<…>` and should themselves be `async Task<…>` or use `Task.FromResult(...)` — not `async void`.

## Troubleshooting

### Black / blank preview

**Symptom:** The page renders, but the camera area is completely black. No tracked-barcode events arrive even though the camera has permission and the code compiles.

**Possible causes (in priority order):**

1. **One of `DataCaptureContext`, `BarcodeAr`, or `BarcodeArViewSettings` is not bound on `<scandit:BarcodeArView>`.** All three are required. Setting `x:Name="BarcodeArView"` is not sufficient — the bindable properties are what wire the mode and context to the native view. Add all three `Binding` expressions to the XAML element.
2. **The MAUI handler for `BarcodeArView` was never registered.** `MauiProgram.cs` must call `.UseScanditBarcode(c => c.AddBarcodeArView())`. If only `UseScanditBarcode()` (no configure) is present, no handler is registered, and the `<scandit:BarcodeArView>` element renders as a blank placeholder. This is the most common cause when migrating from a BarcodeBatch MAUI sample, because BarcodeBatch uses `UseScanditBarcode()` without a configure.
3. **The page binding context does not expose the right properties.** The view model (or `this`, if `BindingContext = this`) must have public properties named `DataCaptureContext`, `BarcodeAr`, and `ViewSettings` (matching whatever names the XAML bindings reference) of the matching types.
4. The camera permission was denied. Check `await Permissions.CheckStatusAsync<Permissions.Camera>()` returns `Granted` and that `Platforms/iOS/Info.plist` contains `NSCameraUsageDescription`.

### `BarcodeArView` is not found in XAML

**Symptom:** Compile error like `The type or namespace 'BarcodeArView' does not exist in the namespace 'Scandit.DataCapture.Barcode.Ar.UI.Maui'`.

**Fix:** Confirm both `Scandit.DataCapture.Barcode` and `Scandit.DataCapture.Barcode.Maui` `<PackageReference>` entries are present, and that they share the same version. The `Scandit.DataCapture.Barcode.Maui` package is the one that ships the MAUI control class. Also confirm the XAML namespace declaration is exactly:

```xml
xmlns:scandit="clr-namespace:Scandit.DataCapture.Barcode.Ar.UI.Maui;assembly=ScanditBarcodeCaptureMaui"
```

(Assembly name is `ScanditBarcodeCaptureMaui` — no dots.)

### `BarcodeArView.Create(...)` does not exist

**Symptom:** Compile error `'BarcodeArView' does not contain a definition for 'Create'`.

**Fix:** The `Create(parentView, barcodeAr, dataCaptureContext, viewSettings, cameraSettings)` factory lives in the per-TFM `Scandit.DataCapture.Barcode.Ar.UI` namespace — it's the **non-MAUI** binding. In MAUI, use the XAML control: declare `<scandit:BarcodeArView ... />` in the page and bind `DataCaptureContext`, `BarcodeAr`, and `BarcodeArViewSettings`. Or, if instantiating from code (rare), use the constructors `new BarcodeArView(context, barcodeAr, settings)` or `new BarcodeArView(context, barcodeAr, settings, cameraSettings)`.

### Camera preview never starts after `OnAppearing`

**Symptom:** Permission is granted but the preview stays grey or freezes.

**Possible causes:**

1. **`Start()` was not called.** The `BarcodeArView` does not auto-start on `HandlerReady` — you must call `barcodeArView.Start()` (typically in `OnAppearing` after the permission check). Calling it before the handler is ready is safe — the command is queued.
2. **`OnPause()` was called but `OnResume()` was not.** Both `OnResume()` and `Start()` are required in `OnAppearing` (`OnResume()` is a no-op on iOS but mandatory on Android for the camera lifecycle).
3. **The page was navigated to multiple times without `Stop()` being called on the previous appearance.** Ensure `OnDisappearing` calls `Stop()` then `OnPause()`.

### `ShouldShowMacroModeControl` does not resolve in XAML

**Symptom:** XAML compile error `The property 'ShouldShowMacroModeControl' was not found in type 'BarcodeArView'`.

**Cause:** The macro-mode toggle exists on the iOS native binding (`Scandit.DataCapture.Barcode.Ar.UI.BarcodeArView`) but is **not** surfaced as a MAUI bindable property on `Scandit.DataCapture.Barcode.Ar.UI.Maui.BarcodeArView`.

**Workaround:** If macro mode is a hard requirement on iOS, drop down to a native handler customization or use the `matrixscan-ar-net-ios` skill in a non-MAUI .NET iOS app.

## Key rules

1. **Fetch the SDK version from NuGet, do not guess** — WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` for the latest stable version before editing the `.csproj`. Skip `-beta`/`-preview`/`-rc` suffixes.
2. **Android `SupportedOSPlatformVersion` ≥ 24** — the MAUI template defaults to `21`; Scandit's Android AAR requires 24. Bump the `.csproj` value if it's lower.
3. **Builder chain is `.UseScanditCore().UseScanditBarcode(c => c.AddBarcodeArView())`** — `UseScanditCore` takes **no** configure for BarcodeAr (unlike BarcodeBatch). `UseScanditBarcode` **requires** the `AddBarcodeArView()` configure. **No** manual `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()` in `MainApplication`/`AppDelegate`.
4. **Four NuGet packages** — Core + Core.Maui + Barcode + Barcode.Maui. All four.
5. **`<scandit:BarcodeArView>` is a XAML control with three mandatory bindable properties: `DataCaptureContext`, `BarcodeAr`, `BarcodeArViewSettings`.** Omit any one and the preview is blank.
6. **XAML namespace assembly is `ScanditBarcodeCaptureMaui`** — no dots in the assembly name (even though the NuGet id has them).
7. **Lifecycle is `OnAppearing` → `OnResume() + Start()`, `OnDisappearing` → `Stop() + OnPause()`** — call all four. `OnResume`/`OnPause` are no-ops on iOS (gated by `#if __ANDROID__` in the handler) but mandatory on Android. `Start`/`Stop` are required on both.
8. **`BarcodeArView` queues commands until handler attaches** — calling `Start()` etc. before the handler is ready is safe (the call is replayed on `HandlerReady`).
9. **`OnSessionUpdated` / `SessionUpdated` runs on a background thread** — use `MainThread.BeginInvokeOnMainThread(() => …)` or `MainThread.InvokeOnMainThreadAsync(...)` for UI updates. Not `RunOnUiThread` (Android-specific) and not `DispatchQueue.MainQueue.DispatchAsync` (iOS-specific).
10. **Providers are async** — `IBarcodeArHighlightProvider.HighlightForBarcodeAsync(barcode)` and `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync(barcode)` both return `Task<…?>`. Return `null` to suppress the overlay for a given barcode.
11. **Highlight/annotation constructors take only `Barcode`** — no `Context` / `UIViewController` argument.
12. **`IBarcodeArListener` has one callback** — `OnSessionUpdated`. No `OnObservationStarted` / `OnObservationStopped`.
13. **Tap events via `HighlightForBarcodeTapped`** — there is no `UiListener` property; subscribe to the event on `BarcodeArView`.
14. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Qr`, `Symbology.Code128`. Not Kotlin underscore or Swift camelCase.
15. **No `ShouldShowMacroModeControl` in MAUI** — iOS-only on the native binding, not exposed cross-platform.
16. **No `BarcodeArView.Create(...)` in MAUI** — the factory is per-TFM. In MAUI, use the XAML control or the `new BarcodeArView(...)` constructors.
17. **Camera permission** — `await Permissions.CheckStatusAsync<Permissions.Camera>()` + `await Permissions.RequestAsync<Permissions.Camera>()`. On iOS, set `NSCameraUsageDescription` in `Platforms/iOS/Info.plist`. There is no `CameraPermissionActivity` helper in MAUI.
