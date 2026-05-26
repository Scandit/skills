# SparkScan .NET for Android Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. The `SparkScanView` overlays a draggable trigger button (and an optional mini preview) on top of any screen, so the user can scan without leaving their current workflow. Unlike BarcodeCapture, you do **not** wire up a `Camera`, `DataCaptureView`, or `BarcodeCaptureOverlay` yourself — SparkScan owns its own camera and preview.

Examples below use C# 12 and an `AppCompatActivity`. The same APIs work identically in a Fragment — adapt ownership of `DataCaptureContext`, `SparkScan`, and `SparkScanView` to the project's existing structure.

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
- `Xamarin.AndroidX.AppCompat` — required because the `CameraPermissionActivity` helper inherits from `AppCompatActivity`. The `dotnet new android` template already pulls it in transitively; for manually scaffolded projects add it explicitly:
  ```xml
  <PackageReference Include="Xamarin.AndroidX.AppCompat" Version="<latest-version-with-xamarin-suffix>" />
  ```
  **When fetching the latest version, pick the highest available including any Xamarin-revision suffix — e.g. `1.7.0.5`, not bare `1.7.0`.** The `.X` suffix marks Xamarin-binding patch revisions and carries critical transitive-dep updates.
- **`Theme.AppCompat` descendant required on the activity.** Because the activity inherits from `AppCompatActivity`, its theme must be a `Theme.AppCompat` descendant or `SetContentView` crashes at launch with `IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity`. The `dotnet new android` template's default theme is **not** AppCompat-based, so set one explicitly on the `[Activity]` attribute (`NoActionBar` since `SparkScanView` overlays its own UI):
  ```csharp
  [Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
  ```
  Or apply it app-wide via `android:theme="@style/Theme.AppCompat.Light.NoActionBar"` on the `<application>` element in `AndroidManifest.xml`.
- The official .NET Android SparkScan sample also references `Xamarin.AndroidX.RecyclerView`, `Xamarin.AndroidX.ConstraintLayout`, `Xamarin.AndroidX.Activity`, `Xamarin.AndroidX.Fragment`, `Xamarin.AndroidX.Lifecycle.ViewModel`, and `Xamarin.Google.Android.Material` — only add the ones the activity layout actually uses. The minimum set needed for SparkScan itself is just `Xamarin.AndroidX.AppCompat`.
- **`SupportedOSPlatformVersion` must be at least `24`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>
  ```
  Lower values fail the build because Scandit's Android AAR has `minSdkVersion=24`.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. Without this, the first `new SparkScan(...)` / `SparkScanView.Create(...)` call crashes because the container has no registrations.

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

  2. **Do not add `<activity>` declarations** for `MainActivity` (or any other class decorated with `[Activity]`). The attribute is the canonical registration in .NET for Android — the build merges a correctly-named entry into the final manifest. A manual `<activity android:name=".MainActivity">` resolves against `<ApplicationId>` and won't match the generated class, producing `ClassNotFoundException` at launch.

  Request the camera permission at runtime using `RequestPermissions` before scanning starts (Android API 23+). The `CameraPermissionActivity` helper at the bottom of this guide encapsulates that flow.

### Project scaffolding (new projects only)

If a .NET Android project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add SparkScan on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

Add the Scandit and `Xamarin.AndroidX.AppCompat` packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `24.0`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which Activity (or Fragment) they'd like to integrate SparkScan into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Ensure `<SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
4. Request the `CAMERA` permission at runtime before scanning starts (the `CameraPermissionActivity` helper below).
5. Create `MainApplication.cs` with `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` (SDK 8.0+).
6. Set `Theme = "@style/Theme.AppCompat.Light.NoActionBar"` on the `[Activity]` attribute (required by `AppCompatActivity`).
7. Wrap the activity layout in `<com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout>` (see Step 5 for the full XML).
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

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

**Note:** `SparkScan` is **not** auto-attached to a `DataCaptureContext` from the constructor — the context is associated implicitly through `SparkScanView.Create(...)` in Step 5. Constructing `new SparkScan()` is enough to start configuring it; you don't need a context-attached factory.

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

> **Use either `AddListener` or the events — not both for the same handler.** The official .NET Android SparkScan sample uses the events.

## Step 4 — Configure SparkScanViewSettings (optional)

`SparkScanViewSettings` controls UI behavior of the SparkScan view: hand mode, hardware trigger, scanning mode, mini preview behavior, toast text, and more. All fields have sensible defaults — only set what you need to change.

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;

SparkScanViewSettings viewSettings = new SparkScanViewSettings();

// Examples:
viewSettings.HardwareTriggerEnabled = true;                              // Enable hardware trigger (gloved hands)
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
| `HardwareTriggerEnabled` | `bool` | Listen for hardware-button presses (Android only — see `SparkScanView.HardwareTriggerSupported`). |
| `HardwareTriggerKeyCode` | `int?` (Android-only) | Override the hardware key code. `null` uses the system default. |
| `ZoomFactorOut` / `ZoomFactorIn` | `float` | Zoom levels for the zoom-switch control. |
| `ToastSettings` | `SparkScanToastSettings` | Toast appearance and text — see Step 4b. |
| `VisualFeedbackEnabled` | `bool` | Show the green/red flash on success/error. |
| `InactiveStateTimeout` | `TimeSpan` | Time to wait before transitioning to `Inactive` view state. |
| `DefaultCameraPosition` | `CameraPosition` | `WorldFacing` (default) or `UserFacing`. |
| `DefaultMiniPreviewSize` | `SparkScanMiniPreviewSize` | `Regular` (default) or `Expanded`. |
| `SmartSelectionCandidateBrush` | `Brush?` | Brush used for the smart-selection candidate highlight. |

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

## Step 5 — Add SparkScanCoordinatorLayout to the activity layout

The activity layout must be wrapped in (or contain) a `SparkScanCoordinatorLayout`. SparkScan uses this container to host the trigger button and mini preview at the correct positions relative to the rest of the layout.

`Resources/layout/activity_main.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:id="@+id/spark_scan_coordinator"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <!-- Place the rest of your activity's layout inside this container. -->
    <androidx.constraintlayout.widget.ConstraintLayout
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="@android:color/white">

        <!-- Your screen content here (results list, header, etc.) -->

    </androidx.constraintlayout.widget.ConstraintLayout>

</com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout>
```

In code, get the container with `FindViewById<SparkScanCoordinatorLayout>(Resource.Id.spark_scan_coordinator)` and pass it to `SparkScanView.Create(...)`:

```csharp
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Barcode.Spark.UI.Platform.Android;

SparkScanCoordinatorLayout container =
    this.FindViewById<SparkScanCoordinatorLayout>(Resource.Id.spark_scan_coordinator)!;

this.sparkScanView = SparkScanView.Create(
    parentView: container,
    context: this.dataCaptureContext,
    sparkScan: this.sparkScan,
    settings: viewSettings);
```

The trigger button, mini preview, and toolbar are added to the coordinator layout automatically — you don't add the `sparkScanView` to the view hierarchy yourself.

### SparkScanView members

| Member | Description |
|--------|-------------|
| `SparkScanView.Create(parent, context, sparkScan, settings)` | Static factory — creates the view and attaches it to `parent` (a `SparkScanCoordinatorLayout`). |
| `OnPause()` | Call from the activity's `OnPause()`. **Required** for correct camera lifecycle. |
| `OnResume()` | Call from the activity's `OnResume()`. **Required**. |
| `StartScanning()` | Programmatically start scanning (no user trigger tap). The view must be in the hierarchy. |
| `PauseScanning()` | Programmatically pause scanning. The view stays attached. |
| `ShowToast(string)` | Show a custom toast in the mini preview. |
| `Feedback` | `ISparkScanFeedbackDelegate?` — set to an instance of `ISparkScanFeedbackDelegate` to customize per-scan feedback. |
| `BarcodeCountButtonVisible` / `BarcodeFindButtonVisible` / `LabelCaptureButtonVisible` / `TargetModeButtonVisible` / `ScanningBehaviorButtonVisible` | `bool` — toolbar button visibility. All default `false`. |
| `ZoomSwitchControlVisible` / `PreviewSizeControlVisible` / `CameraSwitchButtonVisible` / `TriggerButtonVisible` / `PreviewCloseControlVisible` / `TorchControlVisible` | `bool` — other UI control visibility. Defaults vary; `TriggerButtonVisible` defaults to `true`, `CameraSwitchButtonVisible` defaults to `false`. |
| `ToolbarBackgroundColor` / `ToolbarIconActiveTintColor` / `ToolbarIconInactiveTintColor` | `Color?` — toolbar color customization. |
| `TriggerButtonCollapsedColor` / `TriggerButtonExpandedColor` / `TriggerButtonAnimationColor` / `TriggerButtonTintColor` | `Color?` — trigger button color customization. |
| `TriggerButtonImage` | `Image?` — replace the trigger button icon. |
| `static DefaultBrush` | `Brush` — the default brush used by the success-feedback overlay. |
| `static HardwareTriggerSupported` | `bool` (Android-only) — `true` on API 28+. |
| `event EventHandler<SparkScanViewEventArgs> BarcodeCountButtonTapped` | Fires when the Barcode Count toolbar button is tapped. |
| `event EventHandler<SparkScanViewEventArgs> BarcodeFindButtonTapped` | Fires when the Barcode Find toolbar button is tapped. |
| `event EventHandler<SparkScanViewEventArgs> LabelCaptureButtonTapped` | Fires when the Label Capture toolbar button is tapped (dotnet.android 8.3+). |
| `event EventHandler<SparkScanViewStateEventArgs> ViewStateChanged` | Fires whenever `SparkScanViewState` transitions (Initial → Idle → Inactive → Active → Error). |

> The .NET binding does **not** expose `SparkScanView.SetListener(ISparkScanViewUiListener)` — the Kotlin/Java listener interface is not surfaced. Use the C# events instead.

## Step 6 — Handle scans

The official .NET Android SparkScan sample uses the **event API**. The handler receives `SparkScanEventArgs` with `Session` (containing `NewlyRecognizedBarcode`), `FrameData`, and `SparkScan`.

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;

// In OnCreate / setup, after creating sparkScan:
this.sparkScan.BarcodeScanned += this.OnBarcodeScanned;

private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    // OnBarcodeScanned runs on a background thread — dispatch UI work.
    this.RunOnUiThread(() =>
    {
        var description = new SymbologyDescription(barcode.Symbology).ReadableName;
        // Forward to your app: append to a list, send to a backend, etc.
        // For a full RecyclerView-backed results list (item count + clear button), see
        // the "Build a results list (RecyclerView pattern)" subsection under Optional configuration.
    });
}
```

If you prefer the listener interface, implement `ISparkScanListener` directly on the activity:

```csharp
public class MainActivity : CameraPermissionActivity, ISparkScanListener
{
    public void OnBarcodeScanned(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;
        this.RunOnUiThread(() => /* update UI */);
    }

    public void OnSessionUpdated(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        // Called every processed frame; keep this fast.
    }
}

// In OnCreate:
this.sparkScan.AddListener(this);
```

> **Heads-up:** `ISparkScanListener` has **only two** methods — `OnBarcodeScanned` and `OnSessionUpdated`. There are no `OnObservationStarted` / `OnObservationStopped` callbacks (unlike `IBarcodeCaptureListener`). Trying to implement them will produce a compile error.

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
| `FrameData` | `IFrameData?` | The frame that produced the event. May be `null`. |

## Step 7 — Customize feedback (optional)

Implement `ISparkScanFeedbackDelegate` to return per-barcode feedback (success or error). Assign it to `sparkScanView.Feedback`. The delegate is called on a **background thread** — build the feedback objects once and return them, don't dispatch to the UI thread inside the delegate.

```csharp
using Scandit.DataCapture.Barcode.Spark.Feedback;

public class MainActivity : CameraPermissionActivity, ISparkScanFeedbackDelegate
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

Forward the activity's `OnPause` / `OnResume` calls into the SparkScan view. **Both calls are required** — without them, the camera and preview won't behave correctly across backgrounding.

```csharp
protected override void OnPause()
{
    base.OnPause();
    this.sparkScanView.OnPause();
}

protected override void OnResume()
{
    base.OnResume();
    this.sparkScanView.OnResume();
    this.RequestCameraPermission();   // see CameraPermissionActivity below
}

protected override void OnCameraPermissionGranted()
{
    // SparkScanView starts the camera on its own once the view is resumed and enabled.
}
```

`SparkScanView` handles the camera switching internally — you don't need to call `Camera.GetDefaultCamera()` / `SwitchToDesiredStateAsync(...)` yourself.

## Camera permission helper

The official Scandit .NET Android SparkScan sample factors the runtime permission flow into a base activity. Reuse it verbatim:

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

## Complete minimal example

```csharp
using Android.Content.PM;
using Android.OS;
using AndroidX.AppCompat.App;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Barcode.Spark.UI.Platform.Android;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity, ISparkScanFeedbackDelegate
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

    private SparkScanBarcodeSuccessFeedback successFeedback = null!;
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);

        this.Initialize();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.sparkScanView.OnPause();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.sparkScanView.OnResume();
        this.RequestCameraPermission();
    }

    protected override void OnCameraPermissionGranted() { }

    private void Initialize()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Configure SparkScan.
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

        this.sparkScan = new SparkScan(settings);
        this.sparkScan.BarcodeScanned += this.OnBarcodeScanned;

        // Configure the view.
        SparkScanCoordinatorLayout container =
            this.FindViewById<SparkScanCoordinatorLayout>(Resource.Id.spark_scan_coordinator)!;
        SparkScanViewSettings viewSettings = new SparkScanViewSettings();

        this.sparkScanView = SparkScanView.Create(
            parentView: container,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        // Custom feedback delegate.
        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));
        this.sparkScanView.Feedback = this;
    }

    private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        this.RunOnUiThread(() =>
        {
            // Update list / database / UI.
        });
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
```

## Optional configuration

### Build a results list (RecyclerView pattern)

The minimal Step 6 handler just receives the scan — it doesn't display anything. The official .NET Android `ListBuildingSample` displays scans in a `RecyclerView` with a per-item count and a clear button. This subsection is the complete recipe; drop it in if your UI needs to show the scanned barcodes.

**Extra NuGet packages** (in addition to the Prerequisites set):

```xml
<PackageReference Include="Xamarin.AndroidX.ConstraintLayout" Version="<latest-with-xamarin-suffix>" />
<PackageReference Include="Xamarin.AndroidX.RecyclerView" Version="<latest-with-xamarin-suffix>" />
```

Fetch the latest from NuGet the same way as Scandit (Step 0) and AppCompat — keep the Xamarin patch suffix.

**1. Replace the placeholder layout** from Step 5 with the full list-building layout. Keep the `SparkScanCoordinatorLayout` wrapper — only the inner `ConstraintLayout` changes:

```xml
<?xml version="1.0" encoding="utf-8"?>
<com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:id="@+id/spark_scan_coordinator"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <androidx.constraintlayout.widget.ConstraintLayout
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="@android:color/white">

        <TextView
            android:id="@+id/item_count"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_margin="16dp"
            android:textSize="12sp"
            android:textStyle="bold"
            app:layout_constraintTop_toTopOf="parent"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintBottom_toTopOf="@id/result_recycler" />

        <androidx.recyclerview.widget.RecyclerView
            android:id="@+id/result_recycler"
            android:layout_width="match_parent"
            android:layout_height="0dp"
            android:layout_marginBottom="8dp"
            app:layout_constraintTop_toBottomOf="@id/item_count"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintBottom_toTopOf="@id/clear_list" />

        <Button
            android:id="@+id/clear_list"
            style="?android:attr/borderlessButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_marginStart="32dp"
            android:layout_marginEnd="32dp"
            android:layout_marginBottom="8dp"
            android:textStyle="bold"
            android:text="@string/clear_button"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintBottom_toBottomOf="parent" />

    </androidx.constraintlayout.widget.ConstraintLayout>

</com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout>
```

**2. Row layout** at `Resources/layout/result_item.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:paddingStart="?android:attr/listPreferredItemPaddingStart"
    android:paddingEnd="?android:attr/listPreferredItemPaddingEnd"
    android:paddingTop="12dp"
    android:paddingBottom="12dp">

    <TextView
        android:id="@+id/item_title"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:textColor="@android:color/black"
        android:textSize="16sp"
        android:textStyle="bold"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toTopOf="@id/item_description"
        app:layout_constraintVertical_chainStyle="packed" />

    <TextView
        android:id="@+id/item_description"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_marginTop="4dp"
        android:textSize="12sp"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toBottomOf="@id/item_title"
        app:layout_constraintBottom_toBottomOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

**3. String resources** — add to `Resources/values/strings.xml`:

```xml
<string name="clear_button">CLEAR LIST</string>
<plurals name="results_amount">
    <item quantity="one">%d item</item>
    <item quantity="other">%d items</item>
</plurals>
```

**4. `Models/ListItem.cs`** — the row data:

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

**5. `Views/ListItemViewHolder.cs`** — binds the row:

```csharp
using Android.Views;
using AndroidX.RecyclerView.Widget;
using MyApp.Models;

namespace MyApp.Views;

public class ListItemViewHolder(View itemView) : RecyclerView.ViewHolder(itemView)
{
    private readonly TextView title = itemView.FindViewById<TextView>(Resource.Id.item_title)!;
    private readonly TextView description = itemView.FindViewById<TextView>(Resource.Id.item_description)!;

    public void Bind(ListItem item)
    {
        this.title.Text = $"Item {item.Number}";
        this.description.Text = $"{item.Symbology}: {item.Data}";
    }
}
```

**6. `Views/ResultListAdapter.cs`** — the `RecyclerView.Adapter`:

```csharp
using Android.Views;
using AndroidX.RecyclerView.Widget;
using MyApp.Models;

namespace MyApp.Views;

public class ResultListAdapter : RecyclerView.Adapter
{
    private readonly List<ListItem> items = new();

    public override int ItemCount => this.items.Count;

    public event EventHandler? ListChanged;

    public override RecyclerView.ViewHolder OnCreateViewHolder(ViewGroup parent, int viewType) =>
        new ListItemViewHolder(
            LayoutInflater.From(parent.Context)!.Inflate(Resource.Layout.result_item, parent, false)!);

    public override void OnBindViewHolder(RecyclerView.ViewHolder holder, int position)
    {
        if (holder is ListItemViewHolder vh) vh.Bind(this.items[position]);
    }

    public void AddListItem(ListItem item)
    {
        this.items.Add(item);
        this.NotifyItemInserted(this.ItemCount - 1);
        this.ListChanged?.Invoke(this, EventArgs.Empty);
    }

    public void ClearResults()
    {
        this.items.Clear();
        this.NotifyDataSetChanged();
        this.ListChanged?.Invoke(this, EventArgs.Empty);
    }
}
```

**7. Wire it up in `MainActivity.OnCreate`** (after `SetContentView` and `Initialize()`):

```csharp
private readonly ResultListAdapter resultListAdapter = new();
private TextView itemCountText = null!;

protected override void OnCreate(Bundle? savedInstanceState)
{
    base.OnCreate(savedInstanceState);
    this.SetContentView(Resource.Layout.activity_main);
    this.Initialize();

    var recycler = this.FindViewById<RecyclerView>(Resource.Id.result_recycler)!;
    recycler.SetLayoutManager(new LinearLayoutManager(this));
    recycler.SetAdapter(this.resultListAdapter);

    this.itemCountText = this.FindViewById<TextView>(Resource.Id.item_count)!;
    this.UpdateItemCount(0);
    this.resultListAdapter.ListChanged += (_, _) => this.UpdateItemCount(this.resultListAdapter.ItemCount);

    this.FindViewById<Button>(Resource.Id.clear_list)!.Click +=
        (_, _) => this.resultListAdapter.ClearResults();
}

private void UpdateItemCount(int count) => this.RunOnUiThread(() =>
    this.itemCountText.Text = this.Resources?.GetQuantityString(Resource.Plurals.results_amount, count, count));
```

**8. Update the Step 6 handler** to append to the adapter:

```csharp
private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    this.RunOnUiThread(() =>
    {
        var number = this.resultListAdapter.ItemCount + 1;
        this.resultListAdapter.AddListItem(new ListItem(number, barcode.Symbology, barcode.Data));
    });
}
```

That's the complete pattern — text-only rows, no thumbnails. **Want a thumbnail of the scanned barcode in each row?** Add an `ImageView` to `result_item.xml`, store a `Bitmap` on `ListItem`, and produce the bitmap in the scan handler with:

```csharp
var frame = args.FrameData?.ImageBuffers.First().ToImage();
// Crop to barcode.Location using barcode.Location.{TopLeft,TopRight,BottomLeft,BottomRight}
// (each is a Scandit.DataCapture.Core.Common.Geometry.Point in pixel coordinates) and pass
// the cropped Bitmap to ListItem. Do the crop on a background Task and dispatch the final
// AddListItem call via RunOnUiThread.
```

`ImageBuffer.ToImage()` lives in `Scandit.DataCapture.Core.Common.Graphics` and returns an `Android.Graphics.Bitmap` on .NET Android. The official sample's `BarcodeExtensions.GetBarcodeImage` shows a reference cropping implementation.

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

### Hardware trigger (gloved-hand workflows)

```csharp
if (SparkScanView.HardwareTriggerSupported)
{
    viewSettings.HardwareTriggerEnabled = true;
    // Optional: override the key code.
    // viewSettings.HardwareTriggerKeyCode = (int)Android.Views.Keycode.VolumeDown;
}
```

`HardwareTriggerSupported` is a static property that returns `true` on Android API 28+. `HardwareTriggerKeyCode` is `int?` and Android-only — leaving it `null` uses the system default.

### Tracking view state

`SparkScanView.ViewStateChanged` fires every time the view transitions between `Initial`, `Idle`, `Inactive`, `Active`, and `Error`:

```csharp
this.sparkScanView.ViewStateChanged += (sender, args) =>
{
    this.RunOnUiThread(() =>
    {
        switch (args.State)
        {
            case SparkScanViewState.Active:
                this.myButton.Text = "STOP SCANNING";
                break;
            default:
                this.myButton.Text = "START SCANNING";
                break;
        }
    });
};
```

### Custom trigger button (hide built-in, control programmatically)

```csharp
this.sparkScanView.TriggerButtonVisible = false;

// Start scanning from a custom button:
myStartButton.Click += (_, _) => this.sparkScanView.StartScanning();

// Pause:
myPauseButton.Click += (_, _) => this.sparkScanView.PauseScanning();
```

### Showing toolbar buttons

All toolbar buttons default to invisible (except the torch). Enable them through `SparkScanView` properties, and listen for taps through the corresponding events:

```csharp
this.sparkScanView.BarcodeCountButtonVisible = true;
this.sparkScanView.BarcodeCountButtonTapped += (s, e) => { /* open Barcode Count screen */ };

this.sparkScanView.BarcodeFindButtonVisible = true;
this.sparkScanView.BarcodeFindButtonTapped += (s, e) => { /* open Barcode Find screen */ };

this.sparkScanView.LabelCaptureButtonVisible = true;   // dotnet.android 8.3+
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

Available from `Scandit.DataCapture.Barcode` 6.22 onwards on `dotnet.android`.

### Async work after a scan (Task-based)

When the scan result requires a network or database call, do not block the scanner thread:

```csharp
private async void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
{
    var data = args.Session.NewlyRecognizedBarcode?.Data;
    if (data == null) return;

    try
    {
        var result = await LookupAsync(data);
        this.RunOnUiThread(() => this.UpdateUi(result));
    }
    catch (Exception ex)
    {
        // Log; SparkScan keeps scanning regardless.
    }
}
```

> `async void` is acceptable here because the event handler signature is `void`. Unlike `BarcodeCapture`, there is no need to toggle `Enabled = false` — SparkScan handles re-arm timing via the feedback delegate's `resumeCapturingDelay`.

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **`SparkScan` uses `new`, `SparkScanView` uses `Create`** — `new SparkScan(settings)`, `new SparkScanSettings()`, but `SparkScanView.Create(parent, context, sparkScan, settings)`. Don't write `SparkScan.Create(...)` — it doesn't exist.
3. **Wrap the activity layout in `SparkScanCoordinatorLayout`** — declared in XML as `<com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout>`. Pass it as the `parentView` argument.
4. **Forward `OnPause` / `OnResume` into `sparkScanView`** — `sparkScanView.OnPause()` / `OnResume()` are mandatory for correct camera lifecycle.
5. **Event API is idiomatic** — prefer `sparkScan.BarcodeScanned += handler` over `AddListener`. Both work, but the official sample uses events.
6. **Listener has only two callbacks** — `ISparkScanListener.OnBarcodeScanned` and `OnSessionUpdated`. No `OnObservation*`.
7. **Background thread** — `OnBarcodeScanned` and `GetFeedbackForBarcode` both run off the UI thread. `RunOnUiThread(() => …)` is required for UI updates.
8. **Feedback delegate, eager construction** — build `SparkScanBarcodeSuccessFeedback` / `SparkScanBarcodeErrorFeedback` once in `OnCreate`, return cached instances from `GetFeedbackForBarcode`.
9. **SDK 8.0+ requires `MainApplication`** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` in `OnCreate()` before any Scandit type is used.
10. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter`, `TriggerButtonCollapseTimeout`, `InactiveStateTimeout`, and `SparkScanBarcodeErrorFeedback.resumeCapturingDelay` are all `TimeSpan`.
11. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, not `EAN13_UPCA`.
12. **No `<activity>` in the manifest** — `[Activity(MainLauncher = true, …)]` is the canonical registration.
13. **Set a `Theme.AppCompat` descendant on the activity** — `[Activity(..., Theme = "@style/Theme.AppCompat.Light.NoActionBar")]`. Required because the activity inherits from `AppCompatActivity`; without it `SetContentView` throws `IllegalStateException` at launch.
