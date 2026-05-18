# BarcodeCapture .NET MAUI Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On .NET MAUI you wire it up by combining the cross-platform `Scandit.DataCapture.Core` / `Scandit.DataCapture.Barcode` APIs (a `DataCaptureContext`, a `Camera`, a `BarcodeCapture` mode with the `BarcodeScanned` event) with two MAUI-specific pieces: the `<scandit:DataCaptureView>` XAML control from `Scandit.DataCapture.Core.UI.Maui`, and a `BarcodeCaptureOverlay` that is created **after** the view's platform handler has been attached.

`BarcodeCapture` itself does **not** have a dedicated MAUI handler (unlike `BarcodeArView`, `BarcodeCountView`, `BarcodeFindView`, `BarcodePickView`, `SparkScanView`). The MAUI integration always uses the generic `<scandit:DataCaptureView>` plus a `BarcodeCaptureOverlay`.

The examples below follow the structure of the official Scandit MAUI BarcodeCapture sample: a `MainPage` (ContentPage) wired to a `MainPageViewModel` through `BindingContext`, with a `DataCaptureManager` that owns the SDK objects. You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `barcode-capture-net-android` (for `net*-android`) or `barcode-capture-net-ios` (for `net*-ios`). Those skills cover the non-MAUI workloads.

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
All four are needed. The `*.Maui` packages provide the MAUI builder extensions, handlers, and XAML controls; the plain packages provide the platform bindings they delegate to.

### Other prerequisites

- A `<UseMaui>true</UseMaui>` MAUI project targeting at least one of `net10.0-android` or `net10.0-ios`.
- **Android `SupportedOSPlatformVersion` must be at least `24`** — the MAUI template's default is `21`, which is below Scandit's minimum and will produce a `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library` build error. If the `.csproj` has a lower value for the Android `SupportedOSPlatformVersion`, **update it to `24.0`** as part of the integration. iOS minimum is `15.0` (matches the MAUI template default).
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - **Android target**: MAUI's `Permissions.Camera` adds `android.permission.CAMERA` automatically when requested at build time. You can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
  - **iOS target**: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` with a short user-facing description. Without it the app crashes on first camera access.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which `ContentPage` they'd like to integrate BarcodeCapture into. Then write the integration code directly into that page (and supporting files). Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**
1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` and read the latest **stable** version (skip `-beta.*`/`-preview.*`/`-rc.*`). Do not skip this step — versions from training data are stale and will fail `dotnet restore` with `NU1103`.
2. Add all four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Barcode.Maui`) to the `.csproj`, all pinned to that same version.
3. If the `.csproj` targets `net*-android` with `SupportedOSPlatformVersion` below `24`, bump it to `24.0`. The MAUI template defaults to `21.0`, which fails the build because Scandit's Android AAR requires API 24+.
4. Update `MauiProgram.cs` to call `.UseScanditCore(configure => configure.AddDataCaptureView()).UseScanditBarcode()`.
5. Add the `<scandit:...>` XAML namespace and the `<scandit:DataCaptureView>` element to the page.
6. For iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. For Android: rely on `Permissions.Camera` (MAUI auto-adds the manifest entry) or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Register MAUI builder extensions

In `MauiProgram.cs`, chain the Scandit builder extensions:

```csharp
using Scandit.DataCapture.Core;          // UseScanditCore
using Scandit.DataCapture.Core.UI.Maui;  // AddDataCaptureView
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

        builder.Services.AddSingleton<IDataCaptureManager, DataCaptureManager>();
        builder.Services.AddTransient<MainPageViewModel>();
        builder.Services.AddTransient<MainPage>();

        return builder.Build();
    }
}
```

- `UseScanditCore(configure => configure.AddDataCaptureView())` registers the `DataCaptureView` MAUI handler. **Required** for BarcodeCapture in MAUI.
- `UseScanditBarcode()` takes **no inner configure**. It exists only to call `ScanditBarcodeCapture.Initialize()`. **Required** for BarcodeCapture in MAUI.

> Do **not** write `.UseScanditBarcode(configure => configure.AddBarcodeCaptureView())` — `AddBarcodeCaptureView` does not exist. `BarcodeCapture` does not have a pre-built MAUI view; it uses the generic `<scandit:DataCaptureView>`.

## Step 2 — Create the DataCaptureContext, Camera, and BarcodeCapture mode

In a small app these can live directly on the page; in larger apps factor them into a `DataCaptureManager` service registered via DI.

```csharp
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

internal class DataCaptureManager : IDataCaptureManager
{
    public DataCaptureContext DataCaptureContext { get; }
    public Camera? CurrentCamera { get; } = Camera.GetCamera(CameraPosition.WorldFacing);
    public CameraSettings CameraSettings { get; } = BarcodeCapture.RecommendedCameraSettings;
    public BarcodeCapture BarcodeCapture { get; }
    public BarcodeCaptureSettings BarcodeCaptureSettings { get; }

    public DataCaptureManager()
    {
        this.CurrentCamera?.ApplySettingsAsync(this.CameraSettings);

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(App.SCANDIT_LICENSE_KEY);
        this.DataCaptureContext.SetFrameSourceAsync(this.CurrentCamera);

        this.BarcodeCaptureSettings = BarcodeCaptureSettings.Create();
        var symbologies = new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Ean8,
            Symbology.Upce,
            Symbology.Qr,
            Symbology.DataMatrix,
            Symbology.Code39,
            Symbology.Code128,
            Symbology.InterleavedTwoOfFive,
        };
        this.BarcodeCaptureSettings.EnableSymbologies(symbologies);

        this.BarcodeCapture = BarcodeCapture.Create(this.DataCaptureContext, this.BarcodeCaptureSettings);

        // Default feedback (beep + vibration) is enabled. To go silent, see "BarcodeCaptureFeedback" below.
        // this.BarcodeCapture.Feedback.Success = new Feedback(vibration: null, sound: null);
    }
}

public interface IDataCaptureManager
{
    DataCaptureContext DataCaptureContext { get; }
    Camera? CurrentCamera { get; }
    CameraSettings CameraSettings { get; }
    BarcodeCapture BarcodeCapture { get; }
    BarcodeCaptureSettings BarcodeCaptureSettings { get; }
}
```

### BarcodeCaptureSettings members

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeCaptureSettings.Create()` | static factory | Constructs a new settings instance with all symbologies disabled. There is no public constructor — always use `Create()`. |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `EnableSymbologies(CompositeType)` | method | Enable all symbologies required by the given composite types. |
| `GetSymbologySettings(Symbology)` | method | Returns the per-symbology `SymbologySettings` (e.g. `ActiveSymbolCounts` as `ICollection<short>`). |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `EnabledCompositeTypes` | `CompositeType` (get/set) | Bit-flag of enabled composite types. |
| `CodeDuplicateFilter` | `TimeSpan` (get/set) | Window to suppress duplicate scans. See the dedicated section below. |
| `LocationSelection` | `ILocationSelection?` (get/set) | Restricts where in the frame codes are accepted. |
| `BatterySaving` | `BatterySavingMode` (get/set) | `Auto` (default), `On`, `Off`. |
| `ScanIntention` | `ScanIntention` (get/set) | `Smart` (default from 7.0) or `Manual`. |
| `SetProperty(string, object)` / `GetProperty<T>(string)` / `TryGetProperty<T>(string, out T)` | methods | Read/write unstable/experimental engine flags. |

### BarcodeCapture members

| Member | Description |
|--------|-------------|
| `BarcodeCapture.Create(context, settings)` | Factory — creates the mode and attaches it to the context. |
| `BarcodeCapture.Create(settings)` | Factory — creates the mode without a context. |
| `Enabled` | `bool` (get/set) — pause / resume scanning without tearing down the camera. |
| `PointOfInterest` | `PointWithUnit?` (get/set) — overrides the data capture view's point of interest. |
| `Feedback` | `BarcodeCaptureFeedback` (get/set) — sound / vibration on success. |
| `BarcodeCaptureLicenseInfo` | `BarcodeCaptureLicenseInfo?` (get) — licensed symbologies (available after `IDataCaptureContextListener.OnModeAdded`). |
| `Context` | `DataCaptureContext?` (get) — the context the mode is attached to. |
| `BarcodeCapture.RecommendedCameraSettings` | static `CameraSettings` (get) — the recommended camera settings for barcode capture. |
| `ApplySettingsAsync(BarcodeCaptureSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(IBarcodeCaptureListener)` / `RemoveListener(IBarcodeCaptureListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeCaptureEventArgs> BarcodeScanned` | C# event raised after a successful scan. Equivalent to `IBarcodeCaptureListener.OnBarcodeScanned`. **Recommended in MAUI**. |
| `event EventHandler<BarcodeCaptureEventArgs> SessionUpdated` | C# event raised every processed frame. |

## Step 3 — Add the DataCaptureView in XAML

`Scandit.DataCapture.Core.UI.Maui.DataCaptureView` is a MAUI `View` with a `DataCaptureContext` bindable property. Add the XAML namespace and place it on the page; bind its `DataCaptureContext` to the view model.

```xml
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"
             x:Class="MyApp.Views.MainPage">
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
| `AddOverlay(IDataCaptureOverlay)` / `RemoveOverlay(IDataCaptureOverlay)` | Attach / detach overlays (e.g. `BarcodeCaptureOverlay`). |
| `HandlerChanged` | Inherited MAUI event — fires when the platform-specific native view has been created. Create overlays here. |

## Step 4 — Create the BarcodeCaptureOverlay after `HandlerChanged`

The overlay must be created **after** the MAUI handler has attached a native view. Subscribe to `dataCaptureView.HandlerChanged` and add the overlay there.

```csharp
using Scandit.DataCapture.Barcode.UI.Overlay;

public partial class MainPage : ContentPage
{
    private BarcodeCaptureOverlay? overlay;
    private readonly MainPageViewModel viewModel;

    public MainPage(MainPageViewModel viewModel)
    {
        this.viewModel = viewModel;
        this.InitializeComponent();
        this.BindingContext = viewModel;

        // Defer overlay creation until the platform handler is ready.
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeCaptureOverlay.Create(this.viewModel.BarcodeCapture);
        this.overlay.Viewfinder = new RectangularViewfinder(
            RectangularViewfinderStyle.Square,
            RectangularViewfinderLineStyle.Light);
        this.dataCaptureView.AddOverlay(this.overlay);
    }
}
```

> `BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView)` (the two-argument overload) is intended for native views and is **not** used in MAUI. Use the single-argument `Create(barcodeCapture)` overload and attach via `dataCaptureView.AddOverlay(overlay)`.

### BarcodeCaptureOverlay members

| Member | Description |
|--------|-------------|
| `BarcodeCaptureOverlay.Create(mode, view)` | Factory — for native (non-MAUI) views. |
| `BarcodeCaptureOverlay.Create(mode)` | Factory — creates the overlay detached. **Use this in MAUI**, then attach via `dataCaptureView.AddOverlay(overlay)`. |
| `Brush` | `Brush` (get/set) — fill / stroke for recognized-barcode highlights. |
| `BarcodeCaptureOverlay.DefaultBrush` | static `Brush` (get) — the default Scandit-blue stroke brush. |
| `Viewfinder` | `IViewfinder?` (get/set) — optional viewfinder drawn on the preview. |
| `ShouldShowScanAreaGuides` | `bool` (get/set) — development-only aid, defaults to `false`. |
| `SetProperty(string, object)` | Unstable/experimental flags. |

## Step 5 — Handle scans

The official MAUI sample uses the **event-based** API (`BarcodeScanned`) on the view model. Prefer this over `IBarcodeCaptureListener` in MAUI — it composes naturally with `MainThread.BeginInvokeOnMainThread` and async work.

```csharp
public class MainPageViewModel : BaseViewModel
{
    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeCapture BarcodeCapture { get; }

    public MainPageViewModel(IDataCaptureManager dataCaptureManager)
    {
        this.DataCaptureContext = dataCaptureManager.DataCaptureContext;
        this.BarcodeCapture = dataCaptureManager.BarcodeCapture;

        this.BarcodeCapture.BarcodeScanned += this.OnBarcodeScanned;
    }

    private void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        // Stop scanning until we are ready for the next one.
        this.BarcodeCapture.Enabled = false;

        MainThread.BeginInvokeOnMainThread(async () =>
        {
            // Handle barcode.Data, barcode.Symbology — typically show a dialog or navigate.
            // Re-enable scanning when ready, e.g. after the dialog is dismissed:
            // this.BarcodeCapture.Enabled = true;
        });
    }
}
```

#### Re-enabling after a delay

If you want to re-enable scanning after a fixed delay (rather than after a dialog is dismissed), use one of these patterns. Do **not** invent APIs like `MainThread.StartTimer` — that method does not exist on `MainThread`. `StartTimer` is an extension method on `IDispatcher`.

```csharp
// Option A — async/await with Task.Delay (simplest, idiomatic):
MainThread.BeginInvokeOnMainThread(async () =>
{
    // update UI from barcode.Data, barcode.Symbology
    await Task.Delay(TimeSpan.FromMilliseconds(500));
    this.BarcodeCapture.Enabled = true;
});

// Option B — Dispatcher.StartTimer (from inside a Page or anything with access to a Dispatcher):
Dispatcher.StartTimer(TimeSpan.FromMilliseconds(500), () =>
{
    this.BarcodeCapture.Enabled = true;
    return false; // return false to stop the timer after one tick
});

// Option C — Application.Current.Dispatcher.StartTimer (when no Page-level Dispatcher is in scope, e.g. a view model):
Application.Current!.Dispatcher.StartTimer(TimeSpan.FromMilliseconds(500), () =>
{
    this.BarcodeCapture.Enabled = true;
    return false;
});
```

For scans that trigger a network/database lookup, see [Async work after a scan](#async-work-after-a-scan) below — re-enable inside a `finally` block instead.

#### Displaying the scan result to the user

The idiomatic way to display a scanned barcode in MAUI is `Page.DisplayAlertAsync` — **not** a custom label / `VerticalStackLayout`. The alert blocks until the user dismisses it, which gives you a natural place to re-enable scanning.

> ⚠️ **The method name ends in `Async`.** Use `await this.DisplayAlertAsync(title, message, "OK")`. The unsuffixed `DisplayAlert(...)` overload is **obsolete** as of .NET MAUI 9 and produces a `CS0618: 'Page.DisplayAlert(string, string, string)' is obsolete: 'Use DisplayAlertAsync instead'` warning. Both compile, so this is easy to miss if you copy patterns from older code or pre-MAUI-9 samples — always type `DisplayAlertAsync`.

**Inline (code-behind) form** — simplest, fine for a single `MainPage`:

```csharp
private void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    // Stop scanning while the alert is visible.
    this.barcodeCapture.Enabled = false;

    MainThread.BeginInvokeOnMainThread(async () =>
    {
        var description = new SymbologyDescription(barcode.Symbology);
        var title = $"Scanned: {barcode.Data} ({description.ReadableName})";
        await this.DisplayAlertAsync(title, "Continue scanning?", "OK");
        // The await completes when the user dismisses the alert — safe to re-enable.
        this.barcodeCapture.Enabled = true;
    });
}
```

**Injectable `IMessageService` form** — recommended for MVVM apps where the scan handler lives on a view model that has no `Page` reference. This is the pattern used in the official Scandit MAUI BarcodeCapture sample. It wraps `DisplayAlertAsync` behind an interface so the view model can be unit-tested without a UI.

```csharp
// Services/IMessageService.cs
namespace MyApp.Services;

public interface IMessageService
{
    Task ShowAsync(string title, string message, string buttonText = "OK", Action? onDismiss = null);
}

// Services/Internals/MessageService.cs
namespace MyApp.Services.Internals;

internal class MessageService : IMessageService
{
    async Task IMessageService.ShowAsync(string title, string message, string buttonText, Action? onDismiss)
    {
        if (string.IsNullOrEmpty(message)) return;

        if (Application.Current?.Windows.Count > 0)
        {
            Page? page = Application.Current.Windows[0].Page;
            if (page != null)
            {
                await page.DisplayAlertAsync(title, message, buttonText);
                onDismiss?.Invoke();
            }
        }
    }
}
```

Register it in `MauiProgram.cs` alongside the `IDataCaptureManager`:

```csharp
builder.Services.AddSingleton<IMessageService, MessageService>();
```

Then inject and use it from the view model. The `onDismiss` callback fires after the user taps OK, which is the natural place to re-enable scanning:

```csharp
public MainPageViewModel(IDataCaptureManager dataCaptureManager, IMessageService messageService)
{
    this.messageService = messageService;
    /* … */
    this.BarcodeCapture.BarcodeScanned += this.OnBarcodeScanned;
}

private void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    this.BarcodeCapture.Enabled = false;

    var description = new SymbologyDescription(barcode.Symbology);
    var title = $"Scanned: {barcode.Data} ({description.ReadableName})";

    MainThread.BeginInvokeOnMainThread(async () =>
    {
        await this.messageService.ShowAsync(
            title: title,
            message: "Continue scanning?",
            buttonText: "OK",
            onDismiss: () => this.BarcodeCapture.Enabled = true);
    });
}
```

`SymbologyDescription` lives in `Scandit.DataCapture.Barcode.Data`; `ReadableName` returns the human-readable name (e.g. `"EAN-13"` instead of `Ean13Upca`).

### Listener interface alternative

If the project prefers `IBarcodeCaptureListener`, use the standard interface signatures (PascalCase methods). On iOS, remember to call `frameData.Dispose()` at the end of every callback (including early returns) — see the iOS-specific note in `SKILL.md`.

```csharp
public class BarcodeCaptureHandler : IBarcodeCaptureListener
{
    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) { frameData.Dispose(); return; }

        barcodeCapture.Enabled = false;
        MainThread.BeginInvokeOnMainThread(() => { /* update UI */ });

        frameData.Dispose();
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData) => frameData.Dispose();

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}

// then: this.BarcodeCapture.AddListener(handler);
```

### BarcodeCaptureEventArgs

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeCapture` | `BarcodeCapture` | The capture mode that raised the event. |
| `Session` | `BarcodeCaptureSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. |

### BarcodeCaptureSession

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `NewlyRecognizedBarcode` | `Barcode?` | The barcode just scanned in the most recent frame. |
| `NewlyLocalizedBarcodes` | `IList<LocalizedOnlyBarcode>` | Codes that were located but not decoded. |
| `FrameSequenceId` | `long` | Identifier of the current frame sequence (stable until camera interruption). |
| `Reset()` | method | Clears the session's duplicate-filter history. Only call inside the listener/event callbacks. |

### IBarcodeCaptureListener

| Callback | Description |
|----------|-------------|
| `OnBarcodeScanned(BarcodeCapture, BarcodeCaptureSession, IFrameData)` | A barcode was recognized. Called on a background thread. |
| `OnSessionUpdated(BarcodeCapture, BarcodeCaptureSession, IFrameData)` | Called for every processed frame. Keep work minimal. |
| `OnObservationStarted(BarcodeCapture)` | Listener was added. |
| `OnObservationStopped(BarcodeCapture)` | Listener was removed. |

## Step 6 — Lifecycle and camera permission

Drive the camera from the page's MAUI lifecycle. Request the camera permission inside the `ResumeAsync` path so the first frame is not requested before the user grants access.

```csharp
public abstract class BaseViewModel : INotifyPropertyChanged
{
    public virtual Task ResumeAsync() => Task.CompletedTask;
    public virtual Task SleepAsync() => Task.CompletedTask;

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged(string name) =>
        this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class MainPageViewModel : BaseViewModel
{
    private readonly Camera? camera;
    // ... DataCaptureContext, BarcodeCapture, etc. ...

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

        this.BarcodeCapture.Enabled = true;
        await this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On)!;
    }

    public override Task SleepAsync()
    {
        this.BarcodeCapture.Enabled = false;
        return this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off) ?? Task.CompletedTask;
    }
}

// in MainPage.xaml.cs:
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

If the project is small and does not justify a dedicated ViewModel/Manager, this is a compact `ContentPage.xaml.cs` that works end-to-end. The XAML is the same as in Step 3.

```csharp
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI.Viewfinder;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    private readonly Camera? camera;
    private readonly BarcodeCapture barcodeCapture;
    private BarcodeCaptureOverlay? overlay;

    public MainPage()
    {
        this.InitializeComponent();

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetCamera(CameraPosition.WorldFacing);
        this.camera?.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
        this.DataCaptureContext.SetFrameSourceAsync(this.camera);

        var settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeCapture = BarcodeCapture.Create(this.DataCaptureContext, settings);
        this.barcodeCapture.BarcodeScanned += this.OnBarcodeScanned;

        this.BindingContext = this;
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture);
        this.overlay.Viewfinder = new RectangularViewfinder(
            RectangularViewfinderStyle.Square,
            RectangularViewfinderLineStyle.Light);
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

        this.barcodeCapture.Enabled = true;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        this.barcodeCapture.Enabled = false;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    private void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        this.barcodeCapture.Enabled = false;
        MainThread.BeginInvokeOnMainThread(async () =>
        {
            await this.DisplayAlertAsync("Scanned", barcode.Data, "OK");
            this.barcodeCapture.Enabled = true;
        });
    }
}
```

## Optional configuration

### Async work after a scan

When the scan result requires a network or database call, disable scanning immediately on the scanner thread, then offload the work and re-enable in a `finally` block so scanning always resumes even if the lookup fails.

```csharp
private async void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
{
    var data = args.Session.NewlyRecognizedBarcode?.Data;
    if (data == null) return;

    this.barcodeCapture.Enabled = false;
    try
    {
        var result = await LookupAsync(data); // your async network call
        MainThread.BeginInvokeOnMainThread(() => UpdateUi(result));
    }
    finally
    {
        this.barcodeCapture.Enabled = true;
    }
}
```

### BarcodeCaptureFeedback

By default, BarcodeCapture beeps and vibrates on success. To customize feedback, modify `barcodeCapture.Feedback.Success` or replace the entire `Feedback` object:

```csharp
using Scandit.DataCapture.Core.Common.Feedback;

// Silent mode (no sound, no vibration):
barcodeCapture.Feedback.Success = new Feedback(vibration: null, sound: null);

// Reset to defaults:
barcodeCapture.Feedback = BarcodeCaptureFeedback.DefaultFeedback;
```

### Viewfinder

Attach a viewfinder to the overlay (inside `HandlerChanged`) to draw a guide on the preview:

```csharp
using Scandit.DataCapture.Core.UI.Viewfinder;

this.overlay.Viewfinder = new RectangularViewfinder(
    RectangularViewfinderStyle.Square,
    RectangularViewfinderLineStyle.Light);
```

### CodeDuplicateFilter

Suppress duplicate scans of the same code within a time window. The .NET API uses `TimeSpan` plus two sentinel helpers from `Scandit.DataCapture.Barcode.Data.CodeDuplicate`.

```csharp
using Scandit.DataCapture.Barcode.Data;

// Default: Smart (or Manual depending on ScanIntention)
settings.CodeDuplicateFilter = CodeDuplicate.DefaultDuplicateFilter;

// Report each unique code only once until scanning stops
settings.CodeDuplicateFilter = CodeDuplicate.ReportDataAndSymbologyOnlyOnce;

// Custom 500 ms window
settings.CodeDuplicateFilter = TimeSpan.FromMilliseconds(500);

// Custom 2.5 s window
settings.CodeDuplicateFilter = TimeSpan.FromSeconds(2.5);

// Disable filtering — every detection is reported
settings.CodeDuplicateFilter = TimeSpan.Zero;
```

Set this **before** calling `BarcodeCapture.Create(context, settings)`. To change at runtime, mutate the settings and call `barcodeCapture.ApplySettingsAsync(settings)`.

### ScanIntention

```csharp
settings.ScanIntention = ScanIntention.Smart; // default from 7.0
// or
settings.ScanIntention = ScanIntention.Manual;
```

### BatterySaving

```csharp
settings.BatterySaving = BatterySavingMode.Auto; // default
settings.BatterySaving = BatterySavingMode.Off;
settings.BatterySaving = BatterySavingMode.On;
```

### LocationSelection

To restrict scanning to a sub-area of the preview, set `BarcodeCaptureSettings.LocationSelection` to an `ILocationSelection` instance (e.g. `RectangularLocationSelection`). Fetch the [.NET Android Advanced Configurations](https://docs.scandit.com/sdks/net/android/barcode-capture/advanced/) or [.NET iOS Advanced Configurations](https://docs.scandit.com/sdks/net/ios/barcode-capture/advanced/) page for the exact constructor arguments — do not guess.

### Composite codes

Composite codes (linear + 2D companion) require both symbologies *and* composite types to be enabled:

```csharp
using Scandit.DataCapture.Barcode.Data;

settings.EnableSymbologies(CompositeType.A | CompositeType.B);
settings.EnabledCompositeTypes = CompositeType.A | CompositeType.B;
```

### BarcodeCaptureLicenseInfo

Once the mode has been attached to the context and the context has emitted `OnModeAdded`, you can inspect which symbologies the active license allows:

```csharp
using Scandit.DataCapture.Barcode.Capture;

BarcodeCaptureLicenseInfo? licenseInfo = barcodeCapture.BarcodeCaptureLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

`BarcodeCaptureLicenseInfo` is available from `Scandit.DataCapture.Barcode` 8.4 onwards on `dotnet.android` / `dotnet.ios`.

## Key rules

1. **Fetch the SDK version from NuGet, do not guess** — WebFetch `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/` for the latest stable version before editing the `.csproj`. Skip `-beta`/`-preview`/`-rc` suffixes. Versions from training data are stale.
2. **Android `SupportedOSPlatformVersion` ≥ 24** — the MAUI template defaults to `21`; Scandit's Android AAR requires 24. Bump the `.csproj` value if it's lower.
3. **Builder chain** — `MauiProgram.cs` must call `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`. `UseScanditBarcode` takes no inner configure.
4. **Four NuGet packages** — Core + Core.Maui + Barcode + Barcode.Maui. All four.
5. **DataCaptureView is XAML, and `DataCaptureContext="{Binding DataCaptureContext}"` is mandatory** — use `<scandit:DataCaptureView>` with the `xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"` namespace. The `DataCaptureContext` bindable property **must** be set; omitting it produces a black camera preview at runtime even though the code-behind compiles and runs. Bind it to a property of type `DataCaptureContext` on the page's `BindingContext` (view model or page itself).
6. **Overlay after HandlerChanged** — create `BarcodeCaptureOverlay.Create(barcodeCapture)` inside `dataCaptureView.HandlerChanged`, then attach with `dataCaptureView.AddOverlay(overlay)`. Don't use the two-argument `Create(mode, view)` overload in MAUI.
7. **MAUI lifecycle** — wire `OnAppearing` → start camera + `Enabled = true`; `OnDisappearing` → stop camera + `Enabled = false`.
8. **MainThread dispatch** — use `MainThread.BeginInvokeOnMainThread(() => …)`, not `RunOnUiThread` or `DispatchQueue.MainQueue.DispatchAsync`. **`MainThread.StartTimer` does not exist** — `StartTimer` is on `IDispatcher` (`Dispatcher.StartTimer(...)` / `Application.Current.Dispatcher.StartTimer(...)`), or use `await Task.Delay(...)` inside a `BeginInvokeOnMainThread(async () => …)` lambda.
9. **Camera permission** — `await Permissions.CheckStatusAsync<Permissions.Camera>()` + `await Permissions.RequestAsync<Permissions.Camera>()`. On iOS, set `NSCameraUsageDescription` in `Platforms/iOS/Info.plist`.
10. **Disable inside callback** — set `barcodeCapture.Enabled = false` at the start of `OnBarcodeScanned`. Re-enable when ready for the next scan.
11. **Event API is idiomatic** — prefer `barcodeCapture.BarcodeScanned += handler` over `AddListener` in MAUI. If using the listener interface, dispose `frameData` at the end of every callback.
12. **`DisplayAlertAsync` (with the `Async` suffix), not `DisplayAlert`** — use `await this.DisplayAlertAsync(title, message, "OK")` to show scan results. The non-`Async` `DisplayAlert(string, string, string)` overload is obsolete in MAUI 9 and produces `CS0618`. Both compile; the `Async` suffix is mandatory for new code.
13. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter` is `TimeSpan`. Use `CodeDuplicate.DefaultDuplicateFilter` / `CodeDuplicate.ReportDataAndSymbologyOnlyOnce` / `TimeSpan.FromMilliseconds(...)` / `TimeSpan.Zero`.
