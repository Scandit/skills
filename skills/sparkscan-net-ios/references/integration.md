# SparkScan .NET for iOS Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. The `SparkScanView` overlays a draggable trigger button (and an optional mini preview) on top of any screen, so the user can scan without leaving their current workflow. Unlike BarcodeCapture, you do **not** wire up a `Camera`, `DataCaptureView`, or `BarcodeCaptureOverlay` yourself — SparkScan owns its own camera and preview.

Examples below use C# 12 and a `UIViewController`. The same APIs work in storyboards, XIBs, or programmatically-instantiated controllers — adapt ownership of `DataCaptureContext`, `SparkScan`, and `SparkScanView` to the project's existing structure.

> **Scene-based vs storyboard instantiation — match the constructor to the instantiation path.** The `dotnet new ios` template that ships with modern .NET-iOS is **scene-based**: no `Main.storyboard`, no `UIMainStoryboardFile` in `Info.plist`, `AppDelegate` returns a `UISceneConfiguration` from `GetConfiguration`, and a `SceneDelegate.WillConnect` builds the window and sets `Window.RootViewController` programmatically. In that case the `UIViewController` must expose a **parameterless** constructor (`public ViewController() : base() { }`) and `SceneDelegate.WillConnect` calls `new ViewController()`. Do **not** call `new ViewController(IntPtr.Zero)` — the `(IntPtr handle)` constructor is a binding ctor used by storyboard / XIB inflation to wrap an *existing* native object. Calling it with `IntPtr.Zero` produces a managed wrapper with no native `UIViewController` underneath; the view never attaches to the window, `SparkScanView.Create(parentView: this.View, …)` ends up on a detached view, and the camera preview never appears. **Symptom: the app launches but shows a blank screen, no camera, no scans.** If the project *is* storyboard-based (older Scandit samples follow this pattern — `UIMainStoryboardFile` in `Info.plist`, `customClass="ViewController"` in `Main.storyboard`), keep the `public ViewController(IntPtr handle) : base(handle) { }` constructor instead, since storyboard inflation invokes that ctor with a real native handle.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, switch to the `sparkscan-maui` skill. The MAUI integration uses `<scandit:SparkScanView>` in XAML and the `UseScanditCore` / `UseScanditBarcode(c => c.AddSparkScanView())` builder, which are different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add both packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj` (matches the MAUI / .NET iOS template default):
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- **Camera usage description in `Info.plist`:**
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan barcodes.</string>
  ```
  Without this key the app crashes on first camera access. iOS prompts the user for permission automatically the first time the camera is opened; there is no separate runtime-request API to call (the Scandit SDK triggers the standard system prompt when the camera starts).
- **SDK initialization (Scandit 8.0+).** Initialize the Scandit DI container in `AppDelegate.FinishedLaunching` before any Scandit type is constructed. Without this, the first `new SparkScan(...)` / `SparkScanView.Create(...)` call crashes because the container has no registrations.

  ```csharp
  using Foundation;
  using Scandit.DataCapture.Barcode;
  using Scandit.DataCapture.Core;
  using UIKit;

  namespace MyApp;

  [Register("AppDelegate")]
  public class AppDelegate : UIResponder, IUIApplicationDelegate
  {
      [Export("window")]
      public UIWindow Window { get; set; } = null!;

      [Export("application:didFinishLaunchingWithOptions:")]
      public bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
      {
          ScanditCaptureCore.Initialize();
          ScanditBarcodeCapture.Initialize();
          return true;
      }
  }
  ```

  If the project already has an `AppDelegate`, add the two `Initialize()` calls at the top of `FinishedLaunching` rather than creating a second delegate. **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip this entirely.**

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which `UIViewController` they'd like to integrate SparkScan into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Ensure `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `NSCameraUsageDescription` to `Info.plist` with a short user-facing description.
4. Add `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` to `AppDelegate.FinishedLaunching` (SDK 8.0+).
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

private DataCaptureContext dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure SparkScanSettings

Choose which barcode symbologies to scan. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need; each extra symbology adds processing time.

`SparkScanSettings` is constructed with a plain `new` — **there is no `SparkScanSettings.Create()` factory** (unlike `BarcodeCaptureSettings.Create()`).

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;

SparkScanSettings settings = new SparkScanSettings();

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
```

### SparkScanSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new SparkScanSettings()` | constructor | All symbologies disabled. |
| `new SparkScanSettings(CapturePreset)` | constructor | Construct from a preset (e.g. for label use cases). |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `EnableSymbologies(CompositeType)` | method | Enable symbologies required for the given composite types. |
| `GetSymbologySettings(Symbology)` | method | Returns the per-symbology `SymbologySettings` (e.g. `ActiveSymbolCounts` as `ICollection<short>`). |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `EnabledCompositeTypes` | `CompositeType` (get/set) | Bit-flag of enabled composite types. |
| `CodeDuplicateFilter` | `TimeSpan` (get/set) | Window to suppress duplicate scans. See the dedicated section below. |
| `BatterySaving` | `BatterySavingMode` (get/set) | `Auto` (default), `On`, `Off`. |
| `ScanIntention` | `ScanIntention` (get/set) | `Smart` (default from 7.0) or `Manual`. |
| `SetProperty(string, object)` / `GetProperty<T>(string)` / `TryGetProperty<T>(string, out T)` | methods | Read/write unstable/experimental engine flags. |

> Unlike `BarcodeCaptureSettings`, `SparkScanSettings` does **not** expose a `LocationSelection` property — SparkScan controls scan location through its own `SparkScanScanningModeDefault` / `SparkScanScanningModeTarget` modes (see Step 7).

## Step 3 — Create the SparkScan mode

```csharp
this.sparkScan = new SparkScan(settings);
```

Or, with defaults:

```csharp
this.sparkScan = new SparkScan();
```

**Note:** `SparkScan` is **not** auto-attached to a `DataCaptureContext` from the constructor — the context is associated implicitly through `SparkScanView.Create(...)` in Step 5. Constructing `new SparkScan()` is enough to start configuring it.

### SparkScan members

| Member | Description |
|--------|-------------|
| `new SparkScan()` | Constructor — creates the mode with default settings. |
| `new SparkScan(SparkScanSettings settings)` | Constructor — creates the mode with the provided settings. |
| `Enabled` | `bool` (get/set) — pause / resume scanning without tearing down the camera. Toggling this from `true` to `false` puts the connected `SparkScanView` into idle mode. |
| `ApplySettingsAsync(SparkScanSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(ISparkScanListener)` / `RemoveListener(ISparkScanListener)` | Register or remove a listener. |
| `event EventHandler<SparkScanEventArgs> BarcodeScanned` | Raised on every successful scan. **Recommended** in idiomatic C#. |
| `event EventHandler<SparkScanEventArgs> SessionUpdated` | Raised on every processed frame (regardless of whether a code was found). |
| `SparkScanLicenseInfo` | `SparkScanLicenseInfo?` (get) — licensed symbologies (available after `IDataCaptureContextListener.OnModeAdded`). |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the events — not both for the same handler.** The official .NET iOS SparkScan sample uses the events.

## Step 4 — Configure SparkScanViewSettings (optional)

`SparkScanViewSettings` controls UI behavior of the SparkScan view: hold-to-scan, default torch state, scanning mode, mini preview behavior, toast text, and more. All fields have sensible defaults — only set what you need to change.

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Source;

SparkScanViewSettings viewSettings = new SparkScanViewSettings();

// Examples:
viewSettings.SoundEnabled = false;                                       // Mute success beep
viewSettings.HapticEnabled = true;                                       // Vibrate on success (default true)
viewSettings.TriggerButtonCollapseTimeout = TimeSpan.FromSeconds(-1);    // Don't auto-collapse the trigger
viewSettings.InactiveStateTimeout = TimeSpan.FromSeconds(15);            // Time before scanning becomes inactive
viewSettings.DefaultMiniPreviewSize = SparkScanMiniPreviewSize.Regular;  // or Expanded
viewSettings.DefaultCameraPosition = CameraPosition.WorldFacing;         // default; UserFacing for selfie camera
```

### SparkScanViewSettings members

| Member | Type | Description |
|--------|------|-------------|
| `TriggerButtonCollapseTimeout` | `TimeSpan` | Auto-collapse the trigger button after this delay. Default is 5 s in v7+. Set `-1` (or `TimeSpan.FromSeconds(-1)`) for "never". |
| `DefaultScanningMode` | `ISparkScanScanningMode` | Either `SparkScanScanningModeDefault` or `SparkScanScanningModeTarget`. See Step 7. |
| `DefaultTorchState` | `TorchState` | `Off` (default), `On`, `Auto`. If set to `Auto`, the torch control is hidden. |
| `SoundEnabled` | `bool` | Beep on success. Default true. |
| `HapticEnabled` | `bool` | Vibrate on success. Default true. |
| `HoldToScanEnabled` | `bool` | Tap-and-hold vs tap-toggle on the trigger. |
| `HardwareTriggerEnabled` | `bool` | Available on the .NET iOS binding but has no effect at runtime — hardware triggers are Android-only. Leave at default. |
| `ZoomFactorOut` / `ZoomFactorIn` | `float` | Zoom levels for the zoom-switch control. |
| `ToastSettings` | `SparkScanToastSettings` | Toast appearance and text — see Step 4b. |
| `VisualFeedbackEnabled` | `bool` | Show the green/red flash on success/error. |
| `InactiveStateTimeout` | `TimeSpan` | Time to wait before transitioning to `Inactive` view state. |
| `DefaultCameraPosition` | `CameraPosition` | `WorldFacing` (default) or `UserFacing`. |
| `DefaultMiniPreviewSize` | `SparkScanMiniPreviewSize` | `Regular` (default) or `Expanded`. |
| `SmartSelectionCandidateBrush` | `Brush?` | Brush used for the smart-selection candidate highlight. |

> `HardwareTriggerKeyCode` is **not surfaced** on dotnet.ios — it is an Android-only property in the .NET binding. Referencing it in iOS code will not compile.

### Step 4b — Toast text (SparkScanToastSettings)

The mini preview shows a toast banner for several state transitions; SparkScan provides default English text. To override:

```csharp
viewSettings.ToastSettings = new SparkScanToastSettings
{
    ToastEnabled = true,
    ToastBackgroundColor = Color.FromArgb(204, 18, 22, 25),
    ToastTextColor = Color.White,
    TargetModeEnabledMessage = "Target mode on",
    TargetModeDisabledMessage = "Target mode off",
    ContinuousModeEnabledMessage = "Continuous mode",
    ContinuousModeDisabledMessage = "Single-scan mode",
    ScanPausedMessage = "Scanning paused",
    ZoomedInMessage = "Zoomed in",
    ZoomedOutMessage = "Zoomed out",
    TorchEnabledMessage = "Torch on",
    TorchDisabledMessage = "Torch off",
    UserFacingCameraEnabledMessage = "Front camera",
    WorldFacingCameraEnabledMessage = "Back camera",
};
```

Set `ToastEnabled = false` to suppress all toasts. Individual message strings default to `null` — when `null`, the SDK falls back to its built-in text.

## Step 5 — Create the SparkScanView

`SparkScanView.Create(parentView, context, sparkScan, settings)` creates the view and **adds it to `parentView` automatically**. The parent is just the view controller's `View` — there is no coordinator-layout container on iOS (that's Android-only).

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;
using UIKit;

if (this.View == null)
{
    throw new InvalidOperationException("Cannot initialize view");
}

this.sparkScanView = SparkScanView.Create(
    parentView: this.View,
    context: this.dataCaptureContext,
    sparkScan: this.sparkScan,
    settings: viewSettings);
```

Do **not** call `this.View.AddSubview(this.sparkScanView)` — the factory has already done it.

### SparkScanView members (iOS)

| Member | Description |
|--------|-------------|
| `SparkScanView.Create(parentView, context, sparkScan, settings)` | Static factory — creates the view and adds it to `parentView`. |
| `PrepareScanning()` | Call from `ViewWillAppear`. **Required** for correct camera lifecycle. |
| `StopScanning()` | Call from `ViewWillDisappear`. **Required** — turns the camera off and stops scanning. |
| `StartScanning()` | Programmatically start scanning (no user trigger tap). The view must be in the hierarchy. |
| `PauseScanning()` | Programmatically pause scanning. The view stays attached. |
| `ShowToast(string)` | Show a custom toast in the mini preview. |
| `Feedback` | `ISparkScanFeedbackDelegate?` — set to an instance of `ISparkScanFeedbackDelegate` to customize per-scan feedback. |
| `BarcodeCountButtonVisible` / `BarcodeFindButtonVisible` / `LabelCaptureButtonVisible` / `TargetModeButtonVisible` / `ScanningBehaviorButtonVisible` | `bool` — toolbar button visibility. All default `false`. |
| `ZoomSwitchControlVisible` / `PreviewSizeControlVisible` / `CameraSwitchButtonVisible` / `TriggerButtonVisible` / `PreviewCloseControlVisible` / `TorchControlVisible` | `bool` — other UI control visibility. Defaults vary; `TriggerButtonVisible` defaults to `true`. |
| `ToolbarBackgroundColor` / `ToolbarIconActiveTintColor` / `ToolbarIconInactiveTintColor` | `Color?` — toolbar color customization. |
| `TriggerButtonCollapsedColor` / `TriggerButtonExpandedColor` / `TriggerButtonAnimationColor` / `TriggerButtonTintColor` | `Color?` — trigger button color customization. |
| `TriggerButtonImage` | `Image?` — replace the trigger button icon. |
| `static DefaultBrush` | `Brush` — the default brush used by the success-feedback overlay. |
| `event EventHandler<SparkScanViewEventArgs> BarcodeCountButtonTapped` | Fires when the Barcode Count toolbar button is tapped. |
| `event EventHandler<SparkScanViewEventArgs> BarcodeFindButtonTapped` | Fires when the Barcode Find toolbar button is tapped. |
| `event EventHandler<SparkScanViewEventArgs> LabelCaptureButtonTapped` | Fires when the Label Capture toolbar button is tapped (dotnet.ios 8.3+). |
| `event EventHandler<SparkScanViewStateEventArgs> ViewStateChanged` | Fires whenever `SparkScanViewState` transitions (Initial → Idle → Inactive → Active → Error). |

> `OnPause` / `OnResume` and `HardwareTriggerSupported` are **Android-only**. They are not surfaced on dotnet.ios — referencing them in an iOS source file will not compile.

## Step 6 — Handle scans

The official .NET iOS SparkScan sample uses the **event API**. The handler receives `SparkScanEventArgs` with `Session` (containing `NewlyRecognizedBarcode`), `FrameData`, and `SparkScan`.

```csharp
using CoreFoundation;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;

// In ViewDidLoad / setup, after creating sparkScan:
this.sparkScan.BarcodeScanned += this.BarcodeScanned;

private void BarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    // Optional: pull a thumbnail out of the frame data. Always wrap in `using` so the
    // image buffer is released — otherwise the preview will freeze.
    using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();
    using var frame = imageBuffer?.ToImage();
    var location = barcode.GetBarcodeLocation(frame);
    var thumbnail = frame?.CropImage(
        (int)location.X, (int)location.Y, (int)location.Width, (int)location.Height);

    // BarcodeScanned runs on a background thread — dispatch UI work.
    DispatchQueue.MainQueue.DispatchAsync(() =>
    {
        var description = new SymbologyDescription(barcode.Symbology).ReadableName;
        // update list / database / UI here
    });
}
```

If you only need the barcode itself (no frame data), the body collapses to:

```csharp
private void BarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;
    DispatchQueue.MainQueue.DispatchAsync(() => { /* update UI */ });
}
```

If you prefer the listener interface, implement `ISparkScanListener` directly on the view controller:

```csharp
public partial class ViewController : UIViewController, ISparkScanListener
{
    public void OnBarcodeScanned(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;
        DispatchQueue.MainQueue.DispatchAsync(() => /* update UI */);
        // If you accessed frameData, dispose any image buffers you used.
    }

    public void OnSessionUpdated(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData) { }
}

// In ViewDidLoad:
this.sparkScan.AddListener(this);
```

> **Heads-up:** `ISparkScanListener` has **only two** methods — `OnBarcodeScanned` and `OnSessionUpdated`. There are no `OnObservationStarted` / `OnObservationStopped` callbacks (unlike `IBarcodeCaptureListener`).

### SparkScanSession members

| Member | Type | Description |
|--------|------|-------------|
| `NewlyRecognizedBarcode` | `Barcode?` | The barcode that was just scanned in the most recent frame. `null` outside `OnBarcodeScanned`. |
| `FrameSequenceId` | `long` | Identifier of the current frame sequence (stable until camera interruption). |
| `Reset()` | method | Resets the session state. Only call from inside a listener / event callback. |

### SparkScanEventArgs

| Member | Type | Description |
|--------|------|-------------|
| `SparkScan` | `SparkScan` | The capture mode that raised the event. |
| `Session` | `SparkScanSession` | The active session. |
| `FrameData` | `IFrameData?` | The frame that produced the event. May be `null`. **Always wrap any image buffers you read from it in `using`.** |

## Step 7 — Customize feedback (optional)

Implement `ISparkScanFeedbackDelegate` to return per-barcode feedback (success or error). Assign it to `sparkScanView.Feedback`. The delegate is called on a **background thread** — build the feedback objects once and return them, don't dispatch to the UI thread inside the delegate.

```csharp
using Scandit.DataCapture.Barcode.Spark.Feedback;

public partial class ViewController : UIViewController, ISparkScanFeedbackDelegate
{
    private SparkScanBarcodeSuccessFeedback successFeedback = null!;
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;

    private void SetupSparkScanFeedback()
    {
        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));

        this.sparkScanView.Feedback = this;
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode)
    {
        return IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;
    }

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
```

### Feedback classes

`SparkScanBarcodeFeedback` is an abstract base; the two concrete types are:

| Type | Constructors |
|------|--------------|
| `SparkScanBarcodeSuccessFeedback` | `()` (default), `(Color visualFeedbackColor)`, `(Color visualFeedbackColor, Brush brush)`, `(Color visualFeedbackColor, Brush brush, Feedback? feedback)` — read-only properties `VisualFeedbackColor`, `Brush`, `Feedback`. |
| `SparkScanBarcodeErrorFeedback` | `(string message, TimeSpan resumeCapturingDelay)`, `(string, TimeSpan, Color)`, `(string, TimeSpan, Color, Brush)`, `(string, TimeSpan, Color, Brush, Feedback?)` — read-only properties `Message`, `ResumeCapturingDelay`, `VisualFeedbackColor`, `Brush`, `Feedback`. |

Returning `null` from `GetFeedbackForBarcode` falls back to the default success feedback. The `Feedback` parameter is `Scandit.DataCapture.Core.Common.Feedback.Feedback` (the same type used by `BarcodeCaptureFeedback`).

## Step 8 — Lifecycle management

Forward the view controller's `ViewWillAppear` / `ViewWillDisappear` calls into `PrepareScanning()` / `StopScanning()`. **Both calls are required** — without them, the camera and preview won't behave correctly across navigation transitions.

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    this.sparkScanView.PrepareScanning();
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);
    this.sparkScanView.StopScanning();
}
```

`SparkScanView` handles the camera switching internally — you don't need to call `Camera.GetDefaultCamera()` / `SwitchToDesiredStateAsync(...)` yourself, and you do **not** call `OnPause` / `OnResume` (those are Android-only and not surfaced on dotnet.ios).

iOS automatically shows the system camera permission dialog the first time the camera starts. There is no separate runtime-request API to call.

## Complete minimal example

```csharp
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

public partial class ViewController : UIViewController, ISparkScanFeedbackDelegate
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

    private SparkScanBarcodeSuccessFeedback successFeedback = null!;
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;

    // Parameterless ctor for scene-based / programmatic instantiation
    // (the `dotnet new ios` default). If the project is storyboard-based
    // (Info.plist has `UIMainStoryboardFile`), replace this with
    // `public ViewController(IntPtr handle) : base(handle) { }` so storyboard
    // inflation can pass the native handle. Do not call `new ViewController(IntPtr.Zero)`
    // from SceneDelegate — it produces a managed wrapper with no native object
    // and the camera preview will never appear.
    public ViewController() : base() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.SetupSparkScan();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.sparkScanView.PrepareScanning();
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.sparkScanView.StopScanning();
    }

    private void SetupSparkScan()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

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

        this.sparkScan = new SparkScan(settings);
        this.sparkScan.BarcodeScanned += this.BarcodeScanned;

        SparkScanViewSettings viewSettings = new();

        if (this.View == null)
        {
            throw new InvalidOperationException("Cannot initialize view");
        }

        this.sparkScanView = SparkScanView.Create(
            parentView: this.View,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        this.SetupSparkScanFeedback();
    }

    private void SetupSparkScanFeedback()
    {
        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));

        this.sparkScanView.Feedback = this;
    }

    private void BarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        // Optional thumbnail extraction — always wrap in `using` for proper disposal.
        using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();
        using var frame = imageBuffer?.ToImage();
        var location = barcode.GetBarcodeLocation(frame);
        var thumbnail = frame?.CropImage(
            (int)location.X, (int)location.Y, (int)location.Width, (int)location.Height);

        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // Update UI on the main thread.
        });
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
```

## Optional configuration

### Build a results list (UITableView pattern)

The minimal Step 6 handler just receives the scan — it doesn't display anything. The official .NET iOS `ListBuildingSample` displays scans in a `UITableView` floating beneath the `SparkScanView` overlay. This subsection is the complete recipe; drop it in if your UI needs to show the scanned barcodes.

No extra NuGet packages are needed — `UITableView`, `UITableViewSource`, and `UITableViewCell` all ship with UIKit.

**Z-order matters.** Add the table view to `this.View` **before** calling `SparkScanView.Create(parentView: this.View, …)`. Subviews added later sit on top, and `SparkScanView` must float on top of the table to remain interactive (the draggable trigger button, toolbar, and mini preview have to overlay your content, not sit underneath it). The official sample's `ViewDidLoad` orders calls as `SetupHeaderView → SetupTableView → SetupClearView → SetupSparkScan` for exactly this reason — `SparkScanView` is created last.

**1. `Models/ListItem.cs`** — the row data:

```csharp
using Scandit.DataCapture.Barcode.Data;

namespace MyApp.Models;

public class ListItem(int number, Symbology symbology, string? data)
{
    public int Number { get; } = number;
    public string Symbology { get; } = new SymbologyDescription(symbology).ReadableName;
    public string Data { get; } = data ?? string.Empty;
}
```

**2. `Models/ListItemManager.cs`** — thread-safe singleton with a change event:

```csharp
namespace MyApp.Models;

public class ListItemManager
{
    private static readonly Lazy<ListItemManager> instance =
        new(() => new ListItemManager(), LazyThreadSafetyMode.PublicationOnly);

    public static ListItemManager Instance => instance.Value;

    private readonly List<ListItem> items = new();

    public event EventHandler? ListsChanged;

    public IEnumerable<ListItem> Inventory => this.items;
    public int TotalItemsCount => this.items.Count;

    public void AddItem(ListItem item)
    {
        this.items.Add(item);
        this.ListsChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Clear()
    {
        this.items.Clear();
        this.ListsChanged?.Invoke(this, EventArgs.Empty);
    }

    private ListItemManager() { }
}
```

**3. `Views/ItemTableViewCell.cs`** — a minimal two-label cell:

```csharp
using Foundation;
using MyApp.Models;
using UIKit;

namespace MyApp.Views;

public class ItemTableViewCell : UITableViewCell
{
    public static readonly NSString Key = new("ItemTableViewCell");

    private UILabel title = null!;
    private UILabel subtitle = null!;

    // `RegisterClassForCellReuse` + `DequeueReusableCell` instantiate cells via this
    // `(IntPtr handle)` ctor with a real native handle. This is the same storyboard-inflation
    // path described in the "Scene-based vs storyboard instantiation" callout above —
    // do NOT call this ctor manually with `IntPtr.Zero`; UIKit's cell pool owns construction.
    public ItemTableViewCell(IntPtr handle) : base(handle) { }

    public void Configure(ListItem item)
    {
        if (this.title == null) this.CreateLabels();
        this.title.Text = $"Item {item.Number}";
        this.subtitle.Text = $"{item.Symbology}: {item.Data}";
    }

    private void CreateLabels()
    {
        this.title = new UILabel
        {
            TranslatesAutoresizingMaskIntoConstraints = false,
            Font = UIFont.BoldSystemFontOfSize(16),
        };
        this.subtitle = new UILabel
        {
            TranslatesAutoresizingMaskIntoConstraints = false,
            Font = UIFont.SystemFontOfSize(14),
            TextColor = UIColor.Gray,
        };
        this.ContentView.AddSubview(this.title);
        this.ContentView.AddSubview(this.subtitle);
        NSLayoutConstraint.ActivateConstraints(new[]
        {
            this.title.LeadingAnchor.ConstraintEqualTo(this.ContentView.LayoutMarginsGuide.LeadingAnchor),
            this.title.TrailingAnchor.ConstraintEqualTo(this.ContentView.LayoutMarginsGuide.TrailingAnchor),
            this.title.TopAnchor.ConstraintEqualTo(this.ContentView.LayoutMarginsGuide.TopAnchor),
            this.subtitle.LeadingAnchor.ConstraintEqualTo(this.title.LeadingAnchor),
            this.subtitle.TrailingAnchor.ConstraintEqualTo(this.title.TrailingAnchor),
            this.subtitle.TopAnchor.ConstraintEqualTo(this.title.BottomAnchor, 4),
            this.subtitle.BottomAnchor.ConstraintEqualTo(this.ContentView.LayoutMarginsGuide.BottomAnchor),
        });
    }
}
```

**4. `Views/TableSource.cs`** — bridges `ListItemManager` to the table:

```csharp
using Foundation;
using MyApp.Models;
using UIKit;

namespace MyApp.Views;

public class TableSource(IEnumerable<ListItem> items) : UITableViewSource
{
    public override nint RowsInSection(UITableView tableView, nint section) => items.Count();

    public override UITableViewCell GetCell(UITableView tableView, NSIndexPath indexPath)
    {
        var cell = tableView.DequeueReusableCell(ItemTableViewCell.Key, indexPath) as ItemTableViewCell
            ?? throw new InvalidOperationException("Cannot retrieve cell");
        cell.Configure(items.ElementAt(indexPath.Row));
        return cell;
    }
}
```

Note: the source holds a reference to `ListItemManager.Instance.Inventory`, which is `IEnumerable<ListItem>` over the manager's live `List<ListItem>`. Every `ReloadData` re-reads the live list — that's why the source itself never needs an `Add`/`Clear` API of its own.

**5. Wire the table into the view controller.** Build it before `SparkScanView.Create(...)` so the SparkScan overlay lands on top:

```csharp
private UITableView tableView = null!;

private void SetupTableView()
{
    this.tableView = new UITableView
    {
        TranslatesAutoresizingMaskIntoConstraints = false,
        Source = new TableSource(ListItemManager.Instance.Inventory),
        RowHeight = 70,
    };
    this.tableView.RegisterClassForCellReuse(typeof(ItemTableViewCell), ItemTableViewCell.Key);

    this.View!.AddSubview(this.tableView);
    NSLayoutConstraint.ActivateConstraints(new[]
    {
        this.tableView.LeadingAnchor.ConstraintEqualTo(this.View.LeadingAnchor),
        this.tableView.TrailingAnchor.ConstraintEqualTo(this.View.TrailingAnchor),
        this.tableView.TopAnchor.ConstraintEqualTo(this.View.SafeAreaLayoutGuide.TopAnchor),
        this.tableView.BottomAnchor.ConstraintEqualTo(this.View.SafeAreaLayoutGuide.BottomAnchor),
    });

    ListItemManager.Instance.ListsChanged += (_, _) =>
        DispatchQueue.MainQueue.DispatchAsync(this.tableView.ReloadData);
}
```

Call `SetupTableView` from `ViewDidLoad` **before** `SetupSparkScan`:

```csharp
public override void ViewDidLoad()
{
    base.ViewDidLoad();
    this.SetupTableView();
    this.SetupSparkScan();
}
```

**6. Update the Step 6 scan handler** to append to the manager. `BarcodeScanned` runs on a background thread, but `SetupTableView` already dispatches `ReloadData` to the main queue via the `ListsChanged` subscription, so the handler itself just calls `AddItem`:

```csharp
private void BarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    var number = ListItemManager.Instance.TotalItemsCount + 1;
    ListItemManager.Instance.AddItem(new ListItem(number, barcode.Symbology, barcode.Data));
}
```

That's the complete pattern — text-only rows, no thumbnails. **Want a thumbnail of the scanned barcode in each row?** The official `ListBuildingSample` extracts one from the frame buffer using two helpers it defines locally (the SDK does not ship them):

```csharp
// Inside BarcodeScanned, after retrieving `barcode`:
using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();
using var frame = imageBuffer?.ToImage();
var location = barcode.GetBarcodeLocation(frame); // custom extension method
var thumbnail = frame?.CropImage(
    (int)location.X, (int)location.Y, (int)location.Width, (int)location.Height); // custom extension method
// then pass `thumbnail` to ListItem
```

`Barcode.GetBarcodeLocation(UIImage?)` and `UIImage.CropImage(int, int, int, int)` are **extension methods defined in the sample**, not SDK APIs — see `Extensions/BarcodeExtensions.cs` and `Extensions/UIImageExtensions.cs` in `ListBuildingSample` and copy them into your project. `IFrameData`, the image buffer, and the produced `UIImage` **must all be disposed** — the `using` declarations above are mandatory. Failing to dispose causes the preview to stutter or freeze (this is the same disposal rule called out in the iOS gotchas in `SKILL.md`). To render the thumbnail, add a `UIImage? Image` property to `ListItem`, add a `UIImageView` to `ItemTableViewCell` and bind it in `Configure`, and pass the cropped image when calling `AddItem(new ListItem(thumbnail, …))`.

### Target Mode (aim-to-scan)

For precise scanning in crowded environments, change `SparkScanViewSettings.DefaultScanningMode` from the default `SparkScanScanningModeDefault` to `SparkScanScanningModeTarget`:

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;

viewSettings.DefaultScanningMode = new SparkScanScanningModeTarget(
    scanningBehavior: SparkScanScanningBehavior.Single,
    previewBehavior: SparkScanPreviewBehavior.Default);
```

`SparkScanScanningModeDefault` and `SparkScanScanningModeTarget` are constructed with `new`. There is no parameterless constructor in the .NET binding — the `(SparkScanScanningBehavior, SparkScanPreviewBehavior)` constructor is required.

To let users switch modes from the toolbar at runtime:

```csharp
this.sparkScanView.TargetModeButtonVisible = true;
```

### Tracking view state

`SparkScanView.ViewStateChanged` fires every time the view transitions between `Initial`, `Idle`, `Inactive`, `Active`, and `Error`:

```csharp
this.sparkScanView.ViewStateChanged += (sender, args) =>
{
    DispatchQueue.MainQueue.DispatchAsync(() =>
    {
        switch (args.State)
        {
            case SparkScanViewState.Active:
                this.myButton.SetTitle("STOP SCANNING", UIControlState.Normal);
                break;
            default:
                this.myButton.SetTitle("START SCANNING", UIControlState.Normal);
                break;
        }
    });
};
```

### Custom trigger button (hide built-in, control programmatically)

```csharp
this.sparkScanView.TriggerButtonVisible = false;

// Start scanning from a custom button:
myStartButton.TouchUpInside += (_, _) => this.sparkScanView.StartScanning();

// Pause:
myPauseButton.TouchUpInside += (_, _) => this.sparkScanView.PauseScanning();
```

### Showing toolbar buttons

All toolbar buttons default to invisible (except the torch). Enable them through `SparkScanView` properties, and listen for taps through the corresponding events:

```csharp
this.sparkScanView.BarcodeCountButtonVisible = true;
this.sparkScanView.BarcodeCountButtonTapped += (s, e) => { /* open Barcode Count screen */ };

this.sparkScanView.BarcodeFindButtonVisible = true;
this.sparkScanView.BarcodeFindButtonTapped += (s, e) => { /* open Barcode Find screen */ };

this.sparkScanView.LabelCaptureButtonVisible = true;   // dotnet.ios 8.3+
this.sparkScanView.LabelCaptureButtonTapped += (s, e) => { /* open Label Capture screen */ };

this.sparkScanView.ScanningBehaviorButtonVisible = true; // toggle Single ↔ Continuous from toolbar
```

### Custom toast on a scan

```csharp
this.sparkScanView.ShowToast("Item added");
```

`ShowToast` is fire-and-forget — the toast lifetime is controlled by the SDK.

### CodeDuplicateFilter

Suppress duplicate scans of the same code within a time window. The .NET SparkScan API uses `TimeSpan` directly — there are no `CodeDuplicate.DefaultDuplicateFilter` / `CodeDuplicate.ReportDataAndSymbologyOnlyOnce` sentinels here (those live on `BarcodeCaptureSettings`).

```csharp
// Custom 500 ms window
settings.CodeDuplicateFilter = TimeSpan.FromMilliseconds(500);

// Custom 2.5 s window
settings.CodeDuplicateFilter = TimeSpan.FromSeconds(2.5);

// Disable filtering — every detection is reported
settings.CodeDuplicateFilter = TimeSpan.Zero;
```

Set this **before** constructing the `SparkScan`. To change at runtime, mutate the settings and call `sparkScan.ApplySettingsAsync(settings)`.

### ScanIntention

```csharp
settings.ScanIntention = ScanIntention.Smart;   // default from 7.0
settings.ScanIntention = ScanIntention.Manual;  // legacy v6 behavior
```

### BatterySaving

```csharp
settings.BatterySaving = BatterySavingMode.Auto;  // default
settings.BatterySaving = BatterySavingMode.Off;
settings.BatterySaving = BatterySavingMode.On;
```

### SparkScanLicenseInfo

Once the SparkScan mode has been associated with a `DataCaptureContext` and the context emits `OnModeAdded`, inspect which symbologies the active license allows:

```csharp
SparkScanLicenseInfo? licenseInfo = this.sparkScan.SparkScanLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

Available from `Scandit.DataCapture.Barcode` 6.22 onwards on `dotnet.ios`.

### Async work after a scan (Task-based)

When the scan result requires a network or database call, do not block the scanner thread:

```csharp
private async void BarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var data = args.Session.NewlyRecognizedBarcode?.Data;
    using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();
    using var frame = imageBuffer?.ToImage();
    if (data == null) return;

    try
    {
        var result = await LookupAsync(data);
        DispatchQueue.MainQueue.DispatchAsync(() => this.UpdateUi(result));
    }
    catch (Exception ex)
    {
        // Log; SparkScan keeps scanning regardless.
    }
}
```

> `async void` is acceptable here because the event handler signature is `void`. Always dispose any frame-data image buffers up front before the `await` so the SDK can recycle them.

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **`SparkScan` uses `new`, `SparkScanView` uses `Create`** — `new SparkScan(settings)`, `new SparkScanSettings()`, but `SparkScanView.Create(parent, context, sparkScan, settings)`. Don't write `SparkScan.Create(...)` — it doesn't exist.
3. **Parent is `this.View`, no coordinator layout** — iOS does not use `SparkScanCoordinatorLayout` (that's Android-only). The factory adds the view to the parent automatically; do not also call `AddSubview`.
4. **Forward `ViewWillAppear` / `ViewWillDisappear` into `PrepareScanning()` / `StopScanning()`** — these are the iOS-specific lifecycle methods on `SparkScanView`. `OnPause` / `OnResume` are Android-only.
5. **Event API is idiomatic** — prefer `sparkScan.BarcodeScanned += handler` over `AddListener`. Both work, but the official sample uses events.
6. **Listener has only two callbacks** — `ISparkScanListener.OnBarcodeScanned` and `OnSessionUpdated`. No `OnObservation*`.
7. **Background thread + main-queue dispatch** — `BarcodeScanned` / `OnBarcodeScanned` and `GetFeedbackForBarcode` both run off the UI thread. `DispatchQueue.MainQueue.DispatchAsync(() => …)` is required for UI updates.
8. **Always `using` frame-data image buffers** — `using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault(); using var frame = imageBuffer?.ToImage();`. Failing to dispose causes a frozen / stuttering preview.
9. **Feedback delegate, eager construction** — build `SparkScanBarcodeSuccessFeedback` / `SparkScanBarcodeErrorFeedback` once in `SetupSparkScan`, return cached instances from `GetFeedbackForBarcode`.
10. **SDK 8.0+ requires `AppDelegate` init** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` at the top of `FinishedLaunching`.
11. **`NSCameraUsageDescription` in `Info.plist`** is mandatory.
12. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter`, `TriggerButtonCollapseTimeout`, `InactiveStateTimeout`, and `SparkScanBarcodeErrorFeedback.resumeCapturingDelay` are all `TimeSpan`.
13. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, not `.ean13UPCA`.
