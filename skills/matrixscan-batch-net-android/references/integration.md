# MatrixScan Batch .NET for Android Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks every barcode visible in the camera feed, reporting additions, position updates, and removals on every frame. Unlike `BarcodeCapture` (which scans one barcode at a time), `BarcodeBatch` continuously tracks every barcode in view — it does not stop or disable after a detection. Camera and lifecycle are managed manually, exactly like `BarcodeCapture` on .NET Android.

Examples below use C# 12 and an `AppCompatActivity`. The same APIs work identically in a Fragment — adapt ownership of `DataCaptureContext`, `BarcodeBatch`, and the `Camera` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, switch to the `matrixscan-batch-maui` skill. The MAUI integration uses XAML and a `UseScanditBarcode` builder, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

> MatrixScan Batch on `dotnet.android` was first published in **6.16**. Anything older does not have a BarcodeBatch API on this platform.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add both packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- `Xamarin.AndroidX.AppCompat` — required because the `CameraPermissionActivity` helper below inherits from `AppCompatActivity`, and the AppCompat manifest theme resolves through this package. The `dotnet new android` template already pulls it in transitively; for manually scaffolded projects add it explicitly:
  ```xml
  <PackageReference Include="Xamarin.AndroidX.AppCompat" Version="<latest-version-with-xamarin-suffix>" />
  ```
  **When fetching the latest version, pick the highest available including any Xamarin-revision suffix — e.g. `1.7.0.5`, not bare `1.7.0`.** The `.X` suffix marks Xamarin-binding patch revisions and carries critical transitive-dep updates.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. Without this, the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeBatch.Create(...)` / `DataCaptureView.Create(...)` call crashes because the container has no registrations.

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
- `AndroidManifest.xml` setup — three concerns, all required:

  1. **Camera entries** (top-level, sibling to `<application>`):
     ```xml
     <uses-feature android:name="android.hardware.camera" android:required="true" />
     <uses-permission android:name="android.permission.CAMERA" />
     ```

  2. **AppCompat theme on `<application>`** — set `android:theme="@style/Theme.AppCompat.DayNight.NoActionBar"` (or another `Theme.AppCompat` descendant) on the `<application>` element:
     ```xml
     <application
         ...
         android:theme="@style/Theme.AppCompat.DayNight.NoActionBar">
     </application>
     ```
     Required because `AppCompatActivity` throws `java.lang.IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity` at instant launch otherwise. `dotnet new android` does not set this attribute, so it must be added explicitly. `Theme.AppCompat.DayNight.NoActionBar` is the right default for a full-screen camera preview; `Theme.AppCompat.Light.NoActionBar` is also fine.

  3. **Do not add `<activity>` declarations** for `MainActivity` (or any other class decorated with `[Activity]`). The attribute is the canonical registration in .NET for Android — the build merges a correctly-named entry into the final manifest using the .NET-derived Java class name. A manual `<activity android:name=".MainActivity">` resolves against `<ApplicationId>` and won't match the generated class, producing `ClassNotFoundException` at launch.

  Request the camera permission at runtime using `RequestPermissions` before scanning starts (Android API 23+). The `CameraPermissionActivity` helper at the bottom of this guide encapsulates that flow.
- **`SupportedOSPlatformVersion` must be at least `24`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>
  ```
  Lower values fail the build because Scandit's Android AAR has `minSdkVersion=24`.

### Project scaffolding (new projects only)

If a .NET Android project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add MatrixScan Batch on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

This produces a project with the correct `OutputType`, an `AndroidManifest.xml` with an `<application>` declared, a `Resources/values/strings.xml`, and a `Resources/mipmap-*/ic_launcher.*` set. Add the Scandit and `Xamarin.AndroidX.AppCompat` packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `24`, set the AppCompat theme on `<application>`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies they actually need improves tracking performance and accuracy.

Once the user responds, ask them which Activity (or Fragment) they'd like to integrate BarcodeBatch into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts (the example below uses a `CameraPermissionActivity` helper).
4. If targeting SDK 8.0+, create a `MainApplication.cs` that calls `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` from `OnCreate()`.
5. Set `android:theme="@style/Theme.AppCompat.DayNight.NoActionBar"` (or another `Theme.AppCompat` descendant) on the `<application>` element in `AndroidManifest.xml`.
6. Add an `activity_main.axml` (or use an existing layout) containing a `FrameLayout` with `android:id="@+id/data_capture_view_container"`.
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
| `Camera`, `FrameSourceState`, `VideoResolution` | `Scandit.DataCapture.Core.Source` |
| `DataCaptureView` | `Scandit.DataCapture.Core.UI` |
| `IFrameData` | `Scandit.DataCapture.Core.Data` |
| `Brush` | `Scandit.DataCapture.Core.UI.Style` |
| `Anchor`, `PointWithUnit`, `Quadrilateral` | `Scandit.DataCapture.Core.Common.Geometry` |

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

private DataCaptureContext dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure BarcodeBatchSettings

All symbologies are disabled by default. Enable each one explicitly; enabling only what is needed reduces tracking overhead.

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Data;

BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
settings.EnableSymbology(Symbology.Ean13Upca, true);
settings.EnableSymbology(Symbology.Ean8, true);
settings.EnableSymbology(Symbology.Code128, true);
```

You can also enable a set of symbologies at once:

```csharp
settings.EnableSymbologies(new HashSet<Symbology>
{
    Symbology.Ean13Upca,
    Symbology.Code128
});
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

> Symbology names are C# PascalCase. The full set includes `Ean13Upca`, `Ean8`, `Upce`, `Code39`, `Code93`, `Code128`, `InterleavedTwoOfFive`, `Qr`, `DataMatrix`, `Pdf417`, `Aztec`, `Codabar`, and more. Don't use Kotlin-style underscored names (`EAN13_UPCA`).

## Step 3 — Camera setup

`Camera.GetDefaultCamera()` returns the back camera. The canonical pattern (matching the official .NET Android `MatrixScanSimpleSample`) is to obtain the camera, apply `BarcodeBatch.RecommendedCameraSettings` via `ApplySettingsAsync`, and attach it as the frame source.

```csharp
using Scandit.DataCapture.Core.Source;

private Camera? camera;

private void SetUpCamera()
{
    this.camera = Camera.GetDefaultCamera();

    if (this.camera != null)
    {
        // BarcodeBatch.RecommendedCameraSettings is a static PROPERTY — not a method.
        // The Kotlin form `createRecommendedCameraSettings()` does not exist in .NET.
        CameraSettings cameraSettings = BarcodeBatch.RecommendedCameraSettings;

        // Optional: tweak before applying. The official sample bumps to Full HD.
        // cameraSettings.PreferredResolution = VideoResolution.FullHd;

        this.camera.ApplySettingsAsync(cameraSettings);
        this.dataCaptureContext.SetFrameSourceAsync(this.camera);
    }
}
```

Switch the camera on / off:

```csharp
await this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);   // start preview / tracking
await this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);  // release the camera
```

> `Camera.GetCamera(CameraPosition.WorldFacing)` also returns the back camera explicitly. `GetDefaultCamera()` returns the recommended camera for the device.

## Step 4 — Create the BarcodeBatch mode

```csharp
this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
```

`Create(context, settings)` is the factory — the constructor is `private`. When the `context` argument is non-null, the mode is automatically added to the context (you do not need a separate `dataCaptureContext.SetMode(...)` call). Passing `null` for the context creates a detached mode, which you can later attach by passing it to a context.

Re-applying settings at runtime:

```csharp
await this.barcodeBatch.ApplySettingsAsync(newSettings);
```

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
| `BarcodeBatchLicenseInfo` (`BarcodeBatchLicenseInfo?` get) | Licensed symbologies. **Available from 8.4+ on `dotnet.android`.** Value is populated after `IDataCaptureContextListener.OnModeAdded`. |
| `Dispose()` | Releases native resources. |

> Use **either** `AddListener` **or** the `SessionUpdated` event — not both for the same handler. There is **no** `BarcodeScanned` event on `BarcodeBatch` (batch is tracking, not single-scan).

## Step 5 — DataCaptureView

`DataCaptureView.Create(dataCaptureContext)` creates the camera preview as an Android `View`. Place it inside a `FrameLayout` container in the activity layout with `MatchParent` for both dimensions.

```csharp
using Scandit.DataCapture.Core.UI;
using Android.Widget;

// In OnCreate, after SetContentView(Resource.Layout.activity_main):
this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);

var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
container?.AddView(
    this.dataCaptureView,
    new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MatchParent,
        ViewGroup.LayoutParams.MatchParent));
```

The activity layout should contain a `FrameLayout` (or `CoordinatorLayout`) with an id, e.g. `Resources/layout/activity_main.axml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
             android:layout_width="match_parent"
             android:layout_height="match_parent">

    <FrameLayout android:id="@+id/data_capture_view_container"
                 android:layout_width="match_parent"
                 android:layout_height="match_parent" />

</FrameLayout>
```

> Unlike Kotlin's `DataCaptureView.newInstance(context, dataCaptureContext)`, the .NET `Create` overload takes only the `DataCaptureContext`. There is no `Context` parameter.

## Step 6 — BarcodeBatchBasicOverlay

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. The `Create(barcodeBatch, dataCaptureView, ...)` factory **auto-adds the overlay to the view** — no separate `AddOverlay` call needed.

```csharp
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;

// Default style (Frame):
BarcodeBatchBasicOverlay overlay =
    BarcodeBatchBasicOverlay.Create(this.barcodeBatch, this.dataCaptureView);

// Or choose a style explicitly:
BarcodeBatchBasicOverlay overlay = BarcodeBatchBasicOverlay.Create(
    this.barcodeBatch,
    this.dataCaptureView,
    BarcodeBatchBasicOverlayStyle.Frame);
```

### BarcodeBatchBasicOverlay members

| Member | Description |
|--------|-------------|
| `Create(BarcodeBatch, DataCaptureView?, BarcodeBatchBasicOverlayStyle)` | Factory — creates the overlay with a specific style and adds it to the view when non-null. |
| `Create(BarcodeBatch, DataCaptureView?)` | Factory — same, with default `Frame` style. |
| `Create(BarcodeBatch, BarcodeBatchBasicOverlayStyle)` | Factory — creates the overlay detached from a view. |
| `Create(BarcodeBatch)` | Factory — creates the overlay with default `Frame` style, detached from a view. |
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

### Per-barcode brush customization (requires MatrixScan AR add-on)

Implement `IBarcodeBatchBasicOverlayListener` to return a different brush per barcode. `BrushForTrackedBarcode` is called from the rendering thread.

```csharp
using Android.Graphics; // Color
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Brush = Scandit.DataCapture.Core.UI.Style.Brush;

public class BatchScanActivity : CameraPermissionActivity,
    IBarcodeBatchListener,
    IBarcodeBatchBasicOverlayListener
{
    // ... other fields / setup ...

    public Brush? BrushForTrackedBarcode(BarcodeBatchBasicOverlay overlay, TrackedBarcode trackedBarcode)
    {
        // Return null to use the overlay's default brush.
        // Return a fully transparent brush to hide the barcode highlight.
        return trackedBarcode.Barcode.Symbology switch
        {
            Symbology.Ean13Upca => new Brush(
                Color.Argb(100, 0, 200, 68),
                Color.Rgb(0, 200, 68),
                strokeWidth: 2f),
            _ => null,
        };
    }

    public void OnTrackedBarcodeTapped(BarcodeBatchBasicOverlay overlay, TrackedBarcode trackedBarcode)
    {
        // React to the user tapping a barcode highlight.
    }
}
```

Assign the listener after creating the overlay:

```csharp
overlay.Listener = this;
```

> **MatrixScan AR add-on required** for `BrushForTrackedBarcode` and `SetBrushForTrackedBarcode`. A uniform default brush (no listener) does not require the add-on.

## Step 7 — IBarcodeBatchListener (or subscribe to SessionUpdated)

Implement `IBarcodeBatchListener` to receive per-frame session updates. `OnSessionUpdated` is called on a **background recognition thread** — do not hold session references outside the callback, and dispatch any UI work via `RunOnUiThread`.

### Listener interface (parity with the Kotlin / iOS native APIs)

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Core.Data;

public class BatchScanActivity : CameraPermissionActivity, IBarcodeBatchListener
{
    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        // Called on a recognition thread. Copy the data you need…
        var addedData = session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();

        // …then dispatch UI updates.
        RunOnUiThread(() =>
        {
            foreach (var data in addedData)
            {
                // handle data
            }
        });
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}

// In InitializeAndStartBarcodeScanning:
this.barcodeBatch.AddListener(this);
```

### Event handler (idiomatic C#)

```csharp
this.barcodeBatch.SessionUpdated += (sender, args) =>
{
    var addedData = args.Session.AddedTrackedBarcodes
        .Select(tb => tb.Barcode.Data)
        .ToList();

    RunOnUiThread(() =>
    {
        foreach (var data in addedData)
        {
            // handle data
        }
    });
};
```

### IBarcodeBatchListener

| Callback | Description |
|----------|-------------|
| `OnSessionUpdated(BarcodeBatch, BarcodeBatchSession, IFrameData)` | Called every processed frame. **Background recognition thread.** Copy data and dispatch UI work. |
| `OnObservationStarted(BarcodeBatch)` | Listener was registered. |
| `OnObservationStopped(BarcodeBatch)` | Listener was removed. |

### BarcodeBatchEventArgs (for the event-based API)

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeBatch` | `BarcodeBatch` | The mode that raised the event. |
| `Session` | `BarcodeBatchSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. |

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
| `Location` | `Quadrilateral` | Barcode position in image-space coordinates. |
| `GetAnchorPosition(Anchor)` | `Point` | Returns the position of the given anchor on the tracked barcode. |

## Step 8 — Lifecycle management

Drive the camera and the `Enabled` flag from `OnResume` and `OnPause`. The camera must not be active while the activity is in the background.

```csharp
protected override void OnResume()
{
    base.OnResume();

    // Request the runtime permission on Android M+, then resume the frame source.
    if (Build.VERSION.SdkInt >= BuildVersionCodes.M)
    {
        this.RequestCameraPermission();
    }
    else
    {
        this.ResumeFrameSource();
    }
}

protected override void OnCameraPermissionGranted() => this.ResumeFrameSource();

private void ResumeFrameSource()
{
    this.barcodeBatch.Enabled = true;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

protected override void OnPause()
{
    base.OnPause();
    this.barcodeBatch.Enabled = false;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}

protected override void OnDestroy()
{
    this.barcodeBatch.RemoveListener(this);
    this.dataCaptureContext.RemoveCurrentMode();
    base.OnDestroy();
}
```

## Complete minimal example

This mirrors the structure of the official `MatrixScanSimpleSample` for .NET Android.

```csharp
using Android.OS;
using Android.Runtime;
using Android.Widget;

using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class BatchScanActivity : CameraPermissionActivity, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;

    private readonly HashSet<string> scannedData = new();

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.InitializeAndStartBatchScanning();
    }

    protected override void OnResume()
    {
        base.OnResume();
        if (Build.VERSION.SdkInt >= BuildVersionCodes.M)
        {
            this.RequestCameraPermission();
        }
        else
        {
            this.ResumeFrameSource();
        }
    }

    protected override void OnCameraPermissionGranted() => this.ResumeFrameSource();

    private void ResumeFrameSource()
    {
        this.barcodeBatch.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeBatch.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    protected override void OnDestroy()
    {
        this.barcodeBatch.RemoveListener(this);
        this.dataCaptureContext.RemoveCurrentMode();
        base.OnDestroy();
    }

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            CameraSettings cameraSettings = BarcodeBatch.RecommendedCameraSettings;
            this.camera.ApplySettingsAsync(cameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        BarcodeBatchBasicOverlay.Create(
            this.barcodeBatch,
            this.dataCaptureView,
            BarcodeBatchBasicOverlayStyle.Frame);

        var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        // Copy the data we need off the recognition thread before dispatching.
        var addedData = session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .Where(d => d != null)
            .Cast<string>()
            .ToList();

        RunOnUiThread(() =>
        {
            foreach (var data in addedData)
            {
                this.scannedData.Add(data);
            }
        });
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}
```

## Optional: BarcodeBatchAdvancedOverlay (requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom Android `View` to each tracked barcode in real time, retaining its relative position as the barcode moves. The `Create` factory auto-adds the overlay to the view when given a non-null `DataCaptureView`.

```csharp
using Android.Views;
using Android.Widget;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Core.Common.Geometry;

public class BatchScanActivity : CameraPermissionActivity,
    IBarcodeBatchListener,
    IBarcodeBatchAdvancedOverlayListener
{
    private BarcodeBatchAdvancedOverlay advancedOverlay = null!;

    // In InitializeAndStartBatchScanning, after creating dataCaptureView:
    private void SetUpAdvancedOverlay()
    {
        this.advancedOverlay = BarcodeBatchAdvancedOverlay.Create(
            this.barcodeBatch,
            this.dataCaptureView);
        this.advancedOverlay.Listener = this;
    }

    // Called on the main thread for each tracked barcode.
    // Return an Android View to anchor to this barcode, or null to show nothing.
    public View? ViewForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        var label = new TextView(this)
        {
            Text = trackedBarcode.Barcode.Data,
        };
        label.SetBackgroundColor(Android.Graphics.Color.White);
        label.SetPadding(8, 4, 8, 4);
        return label;
    }

    public Anchor AnchorForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode) => Anchor.TopCenter;

    public PointWithUnit OffsetForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode) =>
        new PointWithUnit(
            new FloatWithUnit(0f, MeasureUnit.Fraction),
            new FloatWithUnit(-1f, MeasureUnit.Fraction));
}
```

To update the view for a specific tracked barcode imperatively (e.g. after an async lookup completes), call the `Set*ForTrackedBarcode` methods. They are thread-safe.

```csharp
this.advancedOverlay.SetViewForTrackedBarcode(trackedBarcode, updatedView);
this.advancedOverlay.SetAnchorForTrackedBarcode(trackedBarcode, Anchor.TopCenter);
this.advancedOverlay.SetOffsetForTrackedBarcode(trackedBarcode, offset);
this.advancedOverlay.ClearTrackedBarcodeViews(); // remove all views
```

### BarcodeBatchAdvancedOverlay members

| Member | Description |
|--------|-------------|
| `Create(BarcodeBatch, DataCaptureView?)` | Factory — creates the overlay and adds it to the view when non-null. |
| `Create(BarcodeBatch)` | Factory — creates a detached overlay; attach later by passing it to a `DataCaptureView`. |
| `Listener` (`IBarcodeBatchAdvancedOverlayListener?` get/set) | Per-barcode view / anchor / offset provider. |
| `SetViewForTrackedBarcode(TrackedBarcode, View?)` | Set or update the Android `View` for a barcode. Pass `null` to remove. Thread-safe. |
| `SetAnchorForTrackedBarcode(TrackedBarcode, Anchor)` | Override the anchor for a barcode. Thread-safe. |
| `SetOffsetForTrackedBarcode(TrackedBarcode, PointWithUnit)` | Override the offset for a barcode. Thread-safe. |
| `ClearTrackedBarcodeViews()` | Remove all anchored views. Thread-safe. |
| `ShouldShowScanAreaGuides` (`bool` get/set) | Debug: show the active scan-area outline. |
| `Dispose()` | Releases native resources. |

### IBarcodeBatchAdvancedOverlayListener

| Callback | Description |
|----------|-------------|
| `ViewForTrackedBarcode(overlay, trackedBarcode)` → `View?` | Return the Android `View` to anchor to this barcode, or `null` for none. Called on the main thread. |
| `AnchorForTrackedBarcode(overlay, trackedBarcode)` → `Anchor` | Return the anchor for this barcode's view (e.g. `Anchor.TopCenter`). |
| `OffsetForTrackedBarcode(overlay, trackedBarcode)` → `PointWithUnit` | Return a `PointWithUnit` offset to fine-tune the view position. |

> For tap callbacks and additional advanced-overlay options, fetch the [Adding AR Overlays](https://docs.scandit.com/sdks/net/android/matrixscan/advanced/) page.

## Optional: scan feedback (sound / vibration)

`BarcodeBatch` has **no automatic feedback** — unlike `SparkScan` or `BarcodeCapture`, the mode does not expose a feedback setting and never beeps or vibrates on its own. If you want a sound or vibration when barcodes are tracked, create a `Feedback` and `Emit()` it yourself from `OnSessionUpdated`.

```csharp
using Scandit.DataCapture.Core.Common.Feedback;

// Hold one Feedback instance for the lifetime of the activity.
// Default = default beep + default vibration:
private readonly Feedback feedback = Feedback.DefaultFeedback;

// …or build a custom one:
// private readonly Feedback feedback =
//     new Feedback(Vibration.DefaultVibration, Sound.DefaultSound);
```

Emit it when new barcodes appear. `OnSessionUpdated` runs on the recognition thread; read `session.AddedTrackedBarcodes` there and emit:

```csharp
public void OnSessionUpdated(
    BarcodeBatch barcodeBatch,
    BarcodeBatchSession session,
    IFrameData frameData)
{
    if (session.AddedTrackedBarcodes.Count > 0)
    {
        // Emit() is influenced by the device ring mode / volume settings.
        this.feedback.Emit();
    }
}
```

> `Feedback.DefaultFeedback` is a **static property** in the .NET binding (no parentheses) — not a `DefaultFeedback()` method. `Vibration.DefaultVibration` and `Sound.DefaultSound` are likewise static properties.

### Feedback members (`Scandit.DataCapture.Core.Common.Feedback`)

| Member | Description |
|--------|-------------|
| static `Feedback.DefaultFeedback` (`Feedback` get) | Default sound + default vibration. |
| `Feedback(Vibration?, Sound?)` | Construct with a specific vibration and sound; either may be `null`. |
| `Feedback(Vibration?)` / `Feedback(Sound?)` | Vibration-only / sound-only. |
| `Feedback()` | No sound, no vibration. |
| `Emit()` | Plays the sound and emits the vibration. Subject to device ring mode / volume. |
| `EmitSound()` / `EmitVibration()` | Emit only one component (8.2+). |
| `Sound` (`Sound?` get) / `Vibration` (`Vibration?` get) | The configured components. |
| `Dispose()` | Free native resources. |

> `Feedback`, `Vibration`, and `Sound` all implement `IDisposable` in the .NET binding (the native-only `Release()` method is **not** exposed here). Because this feedback is not owned by a capture mode, call `Dispose()` when the activity is destroyed.

## Optional: pause / reset tracking

| Action | How |
|--------|-----|
| Pause tracking without releasing the camera | `barcodeBatch.Enabled = false` |
| Resume tracking | `barcodeBatch.Enabled = true` |
| Reset the tracker (clear all tracked barcodes) | Inside `OnSessionUpdated`, call `session.Reset()`. **Do not access `session` outside the callback.** |

## Optional: BarcodeBatchLicenseInfo (8.4+)

Once the mode has been attached to the context and the context has emitted `OnModeAdded`, you can inspect which symbologies the active license allows:

```csharp
using Scandit.DataCapture.Barcode.Batch.Capture;

// After IDataCaptureContextListener.OnModeAdded fires:
BarcodeBatchLicenseInfo? licenseInfo = this.barcodeBatch.BarcodeBatchLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

`BarcodeBatchLicenseInfo` is available from Scandit `dotnet.android` 8.4 onwards. On earlier versions the property does not exist.

## Camera permission helper

The official .NET Android `MatrixScanSimpleSample` factors the runtime permission flow into a base activity. Reuse it verbatim:

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

Then derive the scanning activity from `CameraPermissionActivity` and call `RequestCameraPermission()` from `OnResume` (after `base.OnResume()`).

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **Factory, not constructor** — `BarcodeBatch.Create(context, settings)` is the factory. Both `new BarcodeBatch(...)` and `BarcodeBatch.ForDataCaptureContext(...)` are compile errors in the .NET binding.
3. **Settings factory too** — `BarcodeBatchSettings.Create()` is the factory; `new BarcodeBatchSettings()` is a compile error.
4. **Manual camera** — `Camera.GetDefaultCamera()` → `camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings)` → `dataCaptureContext.SetFrameSourceAsync(camera)`. `RecommendedCameraSettings` is a static **property**, not a method.
5. **Recognition thread** — `OnSessionUpdated` runs on a background thread. Copy the data you need, then dispatch UI work via `RunOnUiThread(() => …)`.
6. **Don't retain the session** — the session and its collections are only safe within `OnSessionUpdated`. Copy data out before the callback returns.
7. **Overlay auto-adds** — `BarcodeBatchBasicOverlay.Create(mode, view, ...)` and `BarcodeBatchAdvancedOverlay.Create(mode, view)` both add themselves to the `DataCaptureView` automatically when `view` is non-null.
8. **AR add-on gates** — per-barcode brush customization (`IBarcodeBatchBasicOverlayListener` / `SetBrushForTrackedBarcode`) and `BarcodeBatchAdvancedOverlay` both require the MatrixScan AR add-on license.
9. **`Enabled` for pause/resume** — toggle `barcodeBatch.Enabled` to pause and resume tracking without removing the mode or releasing the camera.
10. **Lifecycle cleanup** — turn the camera off in `OnPause()`, back on in `OnResume()`. Call `barcodeBatch.RemoveListener(this)` and `dataCaptureContext.RemoveCurrentMode()` in `OnDestroy()`.
11. **Symbologies** — all disabled by default; enable only what is needed. Names are PascalCase (`Ean13Upca`, not `EAN13_UPCA`).
12. **Runtime permission** — add `CAMERA` to the manifest and request it at runtime before the first scan.
13. **SDK 8.0+ initialization** — `MainApplication.cs` calling `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` is mandatory on 8.0+.
14. **`IFrameData`, not `FrameData`** — the .NET listener signature passes an `IFrameData`. Don't import `FrameData` (that's a Kotlin type).
