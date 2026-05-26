# MatrixScan Batch .NET for iOS Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks every barcode visible in the camera feed, reporting additions, position updates, and removals on every frame. Unlike `BarcodeCapture` (which scans one barcode at a time), `BarcodeBatch` continuously tracks every barcode in view — it does not stop or disable after a detection. Camera and lifecycle are managed manually, exactly like `BarcodeCapture` on .NET iOS.

Examples below use C# 12 and a `UIViewController`. The same APIs work in storyboards, XIBs, or programmatically-instantiated controllers — adapt ownership of `DataCaptureContext`, `BarcodeBatch`, and the `Camera` to the project's existing structure.

> **Constructor pattern depends on instantiation path.** Storyboard / XIB inflation uses `public MyVC(IntPtr handle) : base(handle) { }`. Programmatic instantiation (no `Main.storyboard`, root view controller set from `SceneDelegate.WillConnect` or `AppDelegate`) needs a parameterless `public MyVC() : base() { }` and `new MyVC()`. **Never construct a VC with `new MyVC(IntPtr.Zero)`** — the native peer is not initialized, `ViewDidLoad` may never fire, and you'll see a black screen with no preview and no scans. If you support both paths, declare both constructors.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, switch to the `matrixscan-batch-maui` skill. The MAUI integration uses XAML and a `UseScanditBarcode` builder, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

> MatrixScan Batch on `dotnet.ios` was first published in **6.16**. Anything older does not have a BarcodeBatch API on this platform.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add both packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- **Camera usage description in `Info.plist`:**
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan barcodes.</string>
  ```
  Without this key the app crashes on first camera access. iOS prompts the user for permission automatically the first time the camera is opened; there is no separate runtime-request API to call (the Scandit SDK triggers the standard system prompt when the camera starts). This is different from .NET for Android, which needs a manual `RequestPermissions` call.
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
  Matches the official `MatrixScanSimpleSample` `Info.plist` `MinimumOSVersion`.
- **SDK initialization (Scandit 8.0+).** Initialize the Scandit DI container in `AppDelegate.FinishedLaunching` before any Scandit type is constructed. Without this the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeBatch.Create(...)` / `DataCaptureView.Create(...)` call crashes because the container has no registrations.

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
      public UIWindow? Window { get; set; }

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

### Project scaffolding (new projects only)

If a .NET iOS project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add MatrixScan Batch on top:

```bash
dotnet new ios -o MyApp
cd MyApp
```

This produces a project with the correct `OutputType`, a working `AppDelegate` / `SceneDelegate`, an `Info.plist`, and storyboard-or-programmatic UI scaffolding. Add the Scandit packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `15.0` (or higher), add `NSCameraUsageDescription` to `Info.plist`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies they actually need improves tracking performance and accuracy.

Once the user responds, ask them which `UIViewController` they'd like to integrate BarcodeBatch into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Add `NSCameraUsageDescription` to `Info.plist` with a short user-facing description.
3. If targeting SDK 8.0+, ensure `AppDelegate.FinishedLaunching` calls `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before constructing any Scandit type.
4. Ensure `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` (or higher) is set in the `.csproj`.
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

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
| `Anchor`, `PointWithUnit`, `Quadrilateral`, `FloatWithUnit`, `MeasureUnit` | `Scandit.DataCapture.Core.Common.Geometry` |

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

> Symbology names are C# PascalCase. The full set includes `Ean13Upca`, `Ean8`, `Upce`, `Code39`, `Code93`, `Code128`, `InterleavedTwoOfFive`, `Qr`, `DataMatrix`, `Pdf417`, `Aztec`, `Codabar`, and more. Don't use Swift-style camelCase names (`ean13UPCA`).

## Step 3 — Camera setup

`Camera.GetDefaultCamera()` returns the back camera. The canonical pattern (matching the official .NET iOS `MatrixScanSimpleSample`) is to obtain the camera, **attach it as the frame source first**, **then** apply `BarcodeBatch.RecommendedCameraSettings` via `ApplySettingsAsync`, and drive it from `ViewWillAppear` / `ViewWillDisappear`.

> **Order matters.** `SetFrameSourceAsync(camera)` must be called **before** `camera.ApplySettingsAsync(cameraSettings)`. This matches the official sample. Reversing the order can leave the preview blank.

```csharp
using Scandit.DataCapture.Core.Source;

private Camera? camera;

private void SetUpCamera()
{
    this.camera = Camera.GetDefaultCamera();

    if (this.camera != null)
    {
        // 1. Bind the camera to the context FIRST.
        this.dataCaptureContext.SetFrameSourceAsync(this.camera);

        // 2. Then apply camera settings.
        // BarcodeBatch.RecommendedCameraSettings is a static PROPERTY — not a method.
        // The Swift form `recommendedCameraSettings` is a class var; the .NET binding
        // exposes it as a static property here.
        CameraSettings cameraSettings = BarcodeBatch.RecommendedCameraSettings;

        // The official iOS sample bumps to Full HD for better decode range.
        cameraSettings.PreferredResolution = VideoResolution.FullHd;

        this.camera.ApplySettingsAsync(cameraSettings);
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
| `BarcodeBatchLicenseInfo` (`BarcodeBatchLicenseInfo?` get) | Licensed symbologies. **Available from 8.4+ on `dotnet.ios`.** Value is populated after `IDataCaptureContextListener.OnModeAdded`. |
| `Dispose()` | Releases native resources. |

> Use **either** `AddListener` **or** the `SessionUpdated` event — not both for the same handler. There is **no** `BarcodeScanned` event on `BarcodeBatch` (batch is tracking, not single-scan).

## Step 5 — DataCaptureView

`DataCaptureView.Create(dataCaptureContext, frame)` creates the camera preview as a `UIView`. The iOS overload takes a `CGRect` (typically `this.View.Bounds`) as the second argument — different from the Android `Create(dataCaptureContext)` form.

```csharp
using Scandit.DataCapture.Core.UI;
using UIKit;

// In ViewDidLoad / InitializeAndStartBatchScanning, after this.View exists:
var dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);

UIView platformView = dataCaptureView;
platformView.AutoresizingMask = UIViewAutoresizing.FlexibleHeight |
                                UIViewAutoresizing.FlexibleWidth;

this.View.AddSubview(dataCaptureView);
this.View.SendSubviewToBack(dataCaptureView);
```

> `DataCaptureView` is a `UIView` and is not auto-attached to any parent. Call `AddSubview` explicitly, then `SendSubviewToBack` so any other subviews (UI chrome, buttons) sit on top of the camera preview. Setting `AutoresizingMask` ensures the preview resizes correctly on rotation and split-screen.

## Step 6 — BarcodeBatchBasicOverlay

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. The `Create(barcodeBatch, dataCaptureView, ...)` factory **auto-adds the overlay to the view** — no separate `AddOverlay` call needed.

```csharp
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;

// Default style (Frame):
BarcodeBatchBasicOverlay overlay =
    BarcodeBatchBasicOverlay.Create(this.barcodeBatch, dataCaptureView);

// Or choose a style explicitly:
BarcodeBatchBasicOverlay overlay = BarcodeBatchBasicOverlay.Create(
    this.barcodeBatch,
    dataCaptureView,
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
using UIKit;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Brush = Scandit.DataCapture.Core.UI.Style.Brush;

public partial class BatchScanViewController : UIViewController,
    IBarcodeBatchListener,
    IBarcodeBatchBasicOverlayListener
{
    // ... other fields / setup ...

    public Brush? BrushForTrackedBarcode(BarcodeBatchBasicOverlay overlay, TrackedBarcode trackedBarcode)
    {
        // Return null to use the overlay's default brush.
        // Return a fully transparent brush to hide the barcode highlight.
        // UIColor.FromRGBA on iOS takes normalized floats in the 0.0..1.0 range
        // (the official Scandit iOS samples use the `x / 255f` pattern).
        return trackedBarcode.Barcode.Symbology switch
        {
            Symbology.Ean13Upca => new Brush(
                fillColor: UIColor.Green.ColorWithAlpha(0.4f),
                strokeColor: UIColor.Green,
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

Implement `IBarcodeBatchListener` to receive per-frame session updates. `OnSessionUpdated` is called on a **background recognition queue** — do not hold session references outside the callback, dispatch any UI work via `DispatchQueue.MainQueue.DispatchAsync`, and **always call `frameData.Dispose()` before returning** (failing to dispose causes a frozen / stuttering preview).

### Listener interface (parity with the Swift / Android native APIs)

```csharp
using CoreFoundation;
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Core.Data;

public partial class BatchScanViewController : UIViewController, IBarcodeBatchListener
{
    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            // Called on a background recognition queue. Copy the data you need…
            var addedData = session.AddedTrackedBarcodes
                .Select(tb => tb.Barcode.Data)
                .Where(d => d != null)
                .Cast<string>()
                .ToList();

            // …then dispatch UI updates onto the main queue.
            DispatchQueue.MainQueue.DispatchAsync(() =>
            {
                foreach (var data in addedData)
                {
                    // handle data
                }
            });
        }
        finally
        {
            // Always dispose the frame, including on the early-return / exception path.
            // Failing to dispose causes a frozen, non-responsive, or stuttering preview.
            frameData.Dispose();
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}

// In InitializeAndStartBatchScanning:
this.barcodeBatch.AddListener(this);
```

### Event handler (idiomatic C#)

```csharp
this.barcodeBatch.SessionUpdated += (sender, args) =>
{
    try
    {
        var addedData = args.Session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();

        DispatchQueue.MainQueue.DispatchAsync(() =>
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
| `OnSessionUpdated(BarcodeBatch, BarcodeBatchSession, IFrameData)` | Called every processed frame. **Background recognition queue.** Copy data, dispatch UI work via `DispatchQueue.MainQueue.DispatchAsync`, and dispose the frame. |
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
| `Location` | `Quadrilateral` | Barcode position in image-space coordinates. |
| `GetAnchorPosition(Anchor)` | `Point` | Returns the position of the given anchor on the tracked barcode. |

## Step 8 — Lifecycle management

Drive the camera and the `Enabled` flag from `ViewWillAppear` and `ViewWillDisappear`. The camera must not be active while the view controller is not visible.

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    // Resume processing frames.
    this.barcodeBatch.Enabled = true;
    // Switch the camera on. iOS asks for the camera permission automatically on
    // the first launch when NSCameraUsageDescription is set in Info.plist.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);
    // Stop processing frames.
    this.barcodeBatch.Enabled = false;
    // Switch the camera off to release it.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}
```

For explicit teardown (e.g. when the scanning view controller is being deallocated), remove the listener and detach the mode:

```csharp
protected override void Dispose(bool disposing)
{
    if (disposing)
    {
        this.barcodeBatch.RemoveListener(this);
        this.dataCaptureContext.RemoveCurrentMode();
    }
    base.Dispose(disposing);
}
```

> Unlike Android (`OnResume` / `OnPause` / `OnDestroy`), iOS lifecycle hooks are `ViewWillAppear` / `ViewWillDisappear` (or `ViewDidAppear` / `ViewDidDisappear`). No runtime permission check is needed — iOS handles that via the `NSCameraUsageDescription` plist key the first time the camera opens.

## Complete minimal example

This mirrors the structure of the official `MatrixScanSimpleSample` for .NET iOS.

```csharp
using System.Collections.Generic;
using System.Linq;
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

public partial class BatchScanViewController : UIViewController, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;

    private readonly HashSet<string> scannedData = new();

    // Storyboard-loaded VCs: keep this constructor (the runtime calls it with a real handle).
    // Programmatically-instantiated VCs (no Main.storyboard): use the parameterless ctor below
    // and `new BatchScanViewController()`. DO NOT call `new BatchScanViewController(IntPtr.Zero)` —
    // that leaves the native peer uninitialized and ViewDidLoad may never fire.
    public BatchScanViewController(IntPtr handle) : base(handle) { }
    public BatchScanViewController() : base() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.InitializeAndStartBatchScanning();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeBatch.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeBatch.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            // Bind the camera to the context BEFORE applying settings — matches the
            // official MatrixScanSimpleSample order. Reversing these leaves the preview blank.
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);

            CameraSettings cameraSettings = BarcodeBatch.RecommendedCameraSettings;
            cameraSettings.PreferredResolution = VideoResolution.FullHd;
            this.camera.ApplySettingsAsync(cameraSettings);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        var dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleHeight |
                                        UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(dataCaptureView);
        this.View.SendSubviewToBack(dataCaptureView);

        BarcodeBatchBasicOverlay.Create(
            this.barcodeBatch,
            dataCaptureView,
            BarcodeBatchBasicOverlayStyle.Frame);
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            // Copy the data we need off the recognition queue before dispatching.
            var addedData = session.AddedTrackedBarcodes
                .Select(tb => tb.Barcode.Data)
                .Where(d => d != null)
                .Cast<string>()
                .ToList();

            DispatchQueue.MainQueue.DispatchAsync(() =>
            {
                foreach (var data in addedData)
                {
                    this.scannedData.Add(data);
                }
            });
        }
        finally
        {
            frameData.Dispose();
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            this.barcodeBatch?.RemoveListener(this);
        }
        base.Dispose(disposing);
    }
}
```

> The official `MatrixScanSimpleSample` does **not** override `Dispose` — it relies on the framework's deterministic teardown. Removing the listener in `Dispose(bool)` is a safe belt-and-suspenders for VCs that may be recreated. **Do not call `dataCaptureContext.RemoveCurrentMode()` here**: it can race with the recognition queue and tear down the mode while a frame is still in flight.

## Optional: BarcodeBatchAdvancedOverlay (requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom `UIView` to each tracked barcode in real time, retaining its relative position as the barcode moves. The `Create` factory auto-adds the overlay to the view when given a non-null `DataCaptureView`.

```csharp
using UIKit;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Core.Common.Geometry;

public partial class BatchScanViewController : UIViewController,
    IBarcodeBatchListener,
    IBarcodeBatchAdvancedOverlayListener
{
    private BarcodeBatchAdvancedOverlay advancedOverlay = null!;

    // In InitializeAndStartBatchScanning, after creating dataCaptureView:
    private void SetUpAdvancedOverlay(DataCaptureView dataCaptureView)
    {
        this.advancedOverlay = BarcodeBatchAdvancedOverlay.Create(
            this.barcodeBatch,
            dataCaptureView);
        this.advancedOverlay.Listener = this;
    }

    // Called on the main thread for each tracked barcode.
    // Return a UIView to anchor to this barcode, or null to show nothing.
    public UIView? ViewForTrackedBarcode(
        BarcodeBatchAdvancedOverlay overlay,
        TrackedBarcode trackedBarcode)
    {
        var label = new UILabel
        {
            Text = trackedBarcode.Barcode.Data,
            TextColor = UIColor.Black,
            BackgroundColor = UIColor.White,
            TextAlignment = UITextAlignment.Center,
        };
        label.SizeToFit();
        // Add a little padding around the text.
        label.Frame = new CoreGraphics.CGRect(
            label.Frame.X, label.Frame.Y,
            label.Frame.Width + 16, label.Frame.Height + 8);
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
| `SetViewForTrackedBarcode(TrackedBarcode, UIView?)` | Set or update the `UIView` for a barcode. Pass `null` to remove. Thread-safe. |
| `SetAnchorForTrackedBarcode(TrackedBarcode, Anchor)` | Override the anchor for a barcode. Thread-safe. |
| `SetOffsetForTrackedBarcode(TrackedBarcode, PointWithUnit)` | Override the offset for a barcode. Thread-safe. |
| `ClearTrackedBarcodeViews()` | Remove all anchored views. Thread-safe. |
| `ShouldShowScanAreaGuides` (`bool` get/set) | Debug: show the active scan-area outline. |
| `Dispose()` | Releases native resources. |

### IBarcodeBatchAdvancedOverlayListener

| Callback | Description |
|----------|-------------|
| `ViewForTrackedBarcode(overlay, trackedBarcode)` → `UIView?` | Return the `UIView` to anchor to this barcode, or `null` for none. Called on the main thread. |
| `AnchorForTrackedBarcode(overlay, trackedBarcode)` → `Anchor` | Return the anchor for this barcode's view (e.g. `Anchor.TopCenter`). |
| `OffsetForTrackedBarcode(overlay, trackedBarcode)` → `PointWithUnit` | Return a `PointWithUnit` offset to fine-tune the view position. |

> For tap callbacks and additional advanced-overlay options, fetch the [Adding AR Overlays](https://docs.scandit.com/sdks/net/ios/matrixscan/advanced/) page.

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

`BarcodeBatchLicenseInfo` is available from Scandit `dotnet.ios` 8.4 onwards. On earlier versions the property does not exist.

## Troubleshooting: frozen, non-responsive, or stuttering preview

**Symptom:** After integrating BarcodeBatch the camera preview freezes after a few frames, becomes unresponsive, or starts stuttering badly. Tracking updates stop arriving.

**Cause:** `IFrameData` (the `frameData` parameter of `OnSessionUpdated`, or `args.FrameData` from the `SessionUpdated` event) holds onto a native frame buffer. The .NET-iOS binding requires the consumer to explicitly `Dispose()` it; otherwise the recognition pipeline runs out of buffers and stalls.

**Fix:** Wrap the body of every `OnSessionUpdated` callback in a `try { ... } finally { frameData.Dispose(); }`, so the frame is always disposed — even on the early-return / exception path:

```csharp
public void OnSessionUpdated(BarcodeBatch barcodeBatch, BarcodeBatchSession session, IFrameData frameData)
{
    try
    {
        // … handle session …
    }
    finally
    {
        frameData.Dispose();
    }
}
```

The same applies to the event-based API — call `args.FrameData.Dispose()` in a `finally`. This is iOS-specific; on Android the binding manages the frame's lifetime for you.

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **Factory, not constructor** — `BarcodeBatch.Create(context, settings)` is the factory. Both `new BarcodeBatch(...)` and `BarcodeBatch.ForDataCaptureContext(...)` are compile errors in the .NET binding.
3. **Settings factory too** — `BarcodeBatchSettings.Create()` is the factory; `new BarcodeBatchSettings()` is a compile error.
4. **Manual camera, in this order** — `Camera.GetDefaultCamera()` → `dataCaptureContext.SetFrameSourceAsync(camera)` → `camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings)`. Bind the camera to the context **before** applying settings (matches the official `MatrixScanSimpleSample`); reversing the order can leave the preview blank. `RecommendedCameraSettings` is a static **property**, not a method.
5. **DataCaptureView takes a CGRect on iOS** — `DataCaptureView.Create(dataCaptureContext, this.View!.Bounds)`, then `AutoresizingMask`, `AddSubview`, `SendSubviewToBack`.
6. **Recognition queue** — `OnSessionUpdated` runs on a background queue. Copy the data you need, then dispatch UI work via `DispatchQueue.MainQueue.DispatchAsync(() => …)`.
7. **Always dispose `IFrameData`** — every `OnSessionUpdated` (and every `SessionUpdated` event handler) must call `frameData.Dispose()` in a `finally` block. Missing this is the #1 cause of frozen / stuttering previews on iOS.
8. **Don't retain the session** — the session and its collections are only safe within `OnSessionUpdated`. Copy data out before the callback returns.
9. **Overlay auto-adds** — `BarcodeBatchBasicOverlay.Create(mode, view, ...)` and `BarcodeBatchAdvancedOverlay.Create(mode, view)` both add themselves to the `DataCaptureView` automatically when `view` is non-null.
10. **AR add-on gates** — per-barcode brush customization (`IBarcodeBatchBasicOverlayListener` / `SetBrushForTrackedBarcode`) and `BarcodeBatchAdvancedOverlay` both require the MatrixScan AR add-on license.
11. **`Enabled` for pause/resume** — toggle `barcodeBatch.Enabled` to pause and resume tracking without removing the mode or releasing the camera.
12. **Lifecycle cleanup** — turn the camera off in `ViewWillDisappear()`, back on in `ViewWillAppear()`. If overriding `Dispose(bool)`, call `barcodeBatch?.RemoveListener(this)` only. Do **not** call `dataCaptureContext.RemoveCurrentMode()` from `Dispose` — it can race with the recognition queue and tear the mode down while a frame is still being processed. The official `MatrixScanSimpleSample` does not override `Dispose` at all.
13. **Symbologies** — all disabled by default; enable only what is needed. Names are PascalCase (`Ean13Upca`, not `.ean13UPCA`).
14. **No runtime permission call** — iOS handles the camera prompt automatically once `NSCameraUsageDescription` is in `Info.plist`. There is no Android-style `RequestPermissions`.
15. **SDK 8.0+ initialization** — `AppDelegate.FinishedLaunching` calling `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` is mandatory on 8.0+.
16. **`IFrameData`, not `FrameData`** — the .NET listener signature passes an `IFrameData`. Don't import `FrameData` (that's a Swift type).
