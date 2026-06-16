# BarcodeCapture .NET for iOS Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On .NET for iOS you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with an `IBarcodeCaptureListener` (or the `BarcodeScanned` event), a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built UI — the camera preview and highlight rectangle are the only visuals.

Examples below use C# 12 and a `UIViewController`. The same APIs work in storyboards, XIBs, or programmatically-instantiated controllers — adapt ownership of `DataCaptureContext`, `BarcodeCapture`, and `Camera` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, switch to the `barcode-capture-maui` skill. The MAUI integration uses `<scandit:DataCaptureView>` in XAML and the `UseScanditCore` / `UseScanditBarcode` builder, which are different.

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
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera usage description in `Info.plist`:
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan barcodes.</string>
  ```
  Without this key the app crashes on first camera access. iOS prompts the user for permission automatically the first time the camera is opened; there is no separate runtime-request API to call (the Scandit SDK triggers the standard system prompt when the camera starts).
- **SDK initialization (Scandit 8.0+).** Initialize the Scandit DI container in `AppDelegate.FinishedLaunching` before any Scandit type is constructed. Without this the first `DataCaptureView.Create` / `BarcodeCapture.Create` call crashes because the container has no registrations.

  ```csharp
  using Scandit.DataCapture.Barcode;
  using Scandit.DataCapture.Core;

  [Register("AppDelegate")]
  public class AppDelegate : UIApplicationDelegate
  {
      public override UIWindow? Window { get; set; }

      public override bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
      {
          ScanditCaptureCore.Initialize();
          ScanditBarcodeCapture.Initialize();

          this.Window = new UIWindow(UIScreen.MainScreen.Bounds);
          this.Window.RootViewController = new ViewController();
          this.Window.MakeKeyAndVisible();
          return true;
      }
  }
  ```

  If the project already has an `AppDelegate`, add the two `Initialize()` calls at the top of `FinishedLaunching` rather than creating a second delegate. **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip this entirely.**

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which `UIViewController` they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Add `NSCameraUsageDescription` to `Info.plist` with a short user-facing description.
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

private DataCaptureContext dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need; each extra symbology adds processing time.

```csharp
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;

BarcodeCaptureSettings settings = BarcodeCaptureSettings.Create();
settings.EnableSymbology(Symbology.Ean13Upca, true);
settings.EnableSymbology(Symbology.Ean8, true);
settings.EnableSymbology(Symbology.Upce, true);
settings.EnableSymbology(Symbology.Code39, true);
settings.EnableSymbology(Symbology.Code128, true);

// Optional: adjust active symbol counts for variable-length 1D symbologies.
SymbologySettings code39 = settings.GetSymbologySettings(Symbology.Code39);
code39.ActiveSymbolCounts = new HashSet<short>(
    new short[] { 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 });
```

You can also enable a set of symbologies at once:

```csharp
settings.EnableSymbologies(new HashSet<Symbology>
{
    Symbology.Ean13Upca,
    Symbology.Code128
});
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

## Step 3 — Camera setup

`Camera.GetDefaultCamera()` returns the back camera. Apply the recommended settings with `ApplySettingsAsync` and attach the camera to the context.

```csharp
using Scandit.DataCapture.Core.Source;

private Camera? camera = Camera.GetDefaultCamera();

private void SetUpCamera()
{
    if (this.camera != null)
    {
        // BarcodeCapture.RecommendedCameraSettings is a static property — not a method.
        this.camera.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
        this.dataCaptureContext.SetFrameSourceAsync(this.camera);
    }
}
```

Switch the camera on / off:

```csharp
await this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);   // start preview / scanning
await this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);  // release the camera
```

> `Camera.GetCamera(CameraPosition.WorldFacing)` is also valid if you need to explicitly request the world-facing camera. `GetDefaultCamera()` returns the recommended camera for the device.

## Step 4 — Create the BarcodeCapture mode

```csharp
this.barcodeCapture = BarcodeCapture.Create(this.dataCaptureContext, settings);
```

If you need to construct the mode detached from a context and attach later, use `BarcodeCapture.Create(settings)` (single-argument overload). When the context is `null`, the mode is **not** auto-added to a context.

Re-applying settings at runtime:

```csharp
await this.barcodeCapture.ApplySettingsAsync(newSettings);
```

### BarcodeCapture members

| Member | Description |
|--------|-------------|
| `BarcodeCapture.Create(context, settings)` | Factory — creates the mode and attaches it to the context. |
| `BarcodeCapture.Create(settings)` | Factory — creates the mode without a context. |
| `Enabled` | `bool` (get/set) — pause / resume scanning without tearing down the camera. |
| `PointOfInterest` | `PointWithUnit?` (get/set) — overrides the data capture view's point of interest. Use `PointWithUnit.Zero` to unset. |
| `Feedback` | `BarcodeCaptureFeedback` (get/set) — sound / vibration on success. |
| `BarcodeCaptureLicenseInfo` | `BarcodeCaptureLicenseInfo?` (get) — licensed symbologies (available after `IDataCaptureContextListener.OnModeAdded`). |
| `Context` | `DataCaptureContext?` (get) — the context the mode is attached to. |
| `BarcodeCapture.RecommendedCameraSettings` | static `CameraSettings` (get) — the recommended camera settings for barcode capture. |
| `ApplySettingsAsync(BarcodeCaptureSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(IBarcodeCaptureListener)` / `RemoveListener(IBarcodeCaptureListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeCaptureEventArgs> BarcodeScanned` | C# event raised after a successful scan. Equivalent to `IBarcodeCaptureListener.OnBarcodeScanned`. |
| `event EventHandler<BarcodeCaptureEventArgs> SessionUpdated` | C# event raised every processed frame. Equivalent to `IBarcodeCaptureListener.OnSessionUpdated`. |

> Use **either** `AddListener` **or** the events — not both for the same handler.

## Step 5 — DataCaptureView and BarcodeCaptureOverlay

`DataCaptureView.Create(dataCaptureContext, frame)` creates the camera preview as a `UIView`. Pass `this.View.Bounds` as the initial frame and set the autoresizing mask so the preview tracks orientation and size changes.

`BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView)` adds the highlight overlay to the view in one step.

```csharp
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Barcode.UI.Overlay;
using UIKit;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View.Bounds);
UIView platformView = this.dataCaptureView;
platformView.AutoresizingMask =
    UIViewAutoresizing.FlexibleHeight | UIViewAutoresizing.FlexibleWidth;
this.View.AddSubview(this.dataCaptureView);

this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);
```

### BarcodeCaptureOverlay members

| Member | Description |
|--------|-------------|
| `BarcodeCaptureOverlay.Create(mode, view)` | Factory — creates the overlay and adds it to the view. |
| `BarcodeCaptureOverlay.Create(mode)` | Factory — creates the overlay without attaching to a view. |
| `Brush` | `Brush` (get/set) — fill / stroke for recognized-barcode highlights. |
| `BarcodeCaptureOverlay.DefaultBrush` | static `Brush` (get) — the default Scandit-blue stroke brush. |
| `Viewfinder` | `IViewfinder?` (get/set) — optional viewfinder drawn on the preview. |
| `ShouldShowScanAreaGuides` | `bool` (get/set) — development-only aid, defaults to `false`. |
| `SetProperty(string, object)` | Unstable/experimental flags. |

## Step 6 — Implement IBarcodeCaptureListener (or subscribe to the event)

The .NET binding exposes both patterns. Pick **one**:

### Listener interface (parity with the Swift native API)

```csharp
using CoreFoundation;
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Core.Data;

public partial class ViewController : UIViewController, IBarcodeCaptureListener
{
    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null)
        {
            // Always dispose the frame, even on early return.
            frameData.Dispose();
            return;
        }

        // Prevent duplicate / racing scans while we handle this one.
        // Re-enabled inside ShowResult below when the user dismisses the dialog.
        barcodeCapture.Enabled = false;

        var description = new SymbologyDescription(barcode.Symbology).ReadableName;
        this.ShowResult($"Scanned {barcode.Data} ({description})");

        // Dispose the frame when you have finished processing it. If the frame is not
        // properly disposed, different issues could arise, e.g. a frozen, non-responsive,
        // or "severely stuttering" video feed.
        frameData.Dispose();
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        frameData.Dispose();
    }

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}

// In ViewDidLoad or InitializeAndStartBarcodeScanning:
this.barcodeCapture.AddListener(this);
```

### Event handler (idiomatic C#)

```csharp
this.barcodeCapture.BarcodeScanned += (sender, args) =>
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    try
    {
        if (barcode == null) return;
        args.BarcodeCapture.Enabled = false;
        var description = new SymbologyDescription(barcode.Symbology).ReadableName;
        this.ShowResult($"Scanned {barcode.Data} ({description})");
    }
    finally
    {
        args.FrameData.Dispose();
    }
};
```

### IBarcodeCaptureListener

| Callback | Description |
|----------|-------------|
| `OnBarcodeScanned(BarcodeCapture, BarcodeCaptureSession, IFrameData)` | A barcode was recognized. Read it from `session.NewlyRecognizedBarcode`. Called on a background thread. |
| `OnSessionUpdated(BarcodeCapture, BarcodeCaptureSession, IFrameData)` | Called for every processed frame. Keep work minimal. |
| `OnObservationStarted(BarcodeCapture)` | Listener was added. |
| `OnObservationStopped(BarcodeCapture)` | Listener was removed. |

### BarcodeCaptureEventArgs (for the event-based API)

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeCapture` | `BarcodeCapture` | The capture mode that raised the event. |
| `Session` | `BarcodeCaptureSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. Always `Dispose()` it on iOS. |

### BarcodeCaptureSession

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `NewlyRecognizedBarcode` | `Barcode?` | The barcode just scanned in the most recent frame. |
| `NewlyLocalizedBarcodes` | `IList<LocalizedOnlyBarcode>` | Codes that were located but not decoded. |
| `FrameSequenceId` | `long` | Identifier of the current frame sequence (stable until camera interruption). |
| `Reset()` | method | Clears the session's duplicate-filter history. **Only call inside the listener callbacks.** |

### Showing the result and re-enabling scanning

`barcodeCapture.Enabled = false` stops new detections until you set it back to `true`. The handler must own that re-enable — otherwise the scanner stays dead after the first scan. The canonical Scandit sample uses a `UIAlertController` so the user dismisses the result with an OK button, which is also the natural point to re-enable:

```csharp
public void ShowResult(string result)
{
    DispatchQueue.MainQueue.DispatchAsync(() =>
    {
        var alert = UIAlertController.Create(
            result, message: null, preferredStyle: UIAlertControllerStyle.Alert);
        var ok = UIAlertAction.Create("OK", UIAlertActionStyle.Default, _ =>
        {
            this.barcodeCapture.Enabled = true;
        });
        alert.AddAction(ok);
        this.PresentViewController(alert, animated: true, completionHandler: () => { });
    });
}
```

No need to retain the controller — iOS dismisses it automatically when the user taps OK, and `ViewWillDisappear` already turns the camera off if the view is backgrounded while a dialog is up. Call `ShowResult` from `OnBarcodeScanned`:

```csharp
string description = new SymbologyDescription(barcode.Symbology).ReadableName;
this.ShowResult($"Scanned {barcode.Data} ({description})");
```

This matches Scandit's official `BarcodeCaptureSimpleSample` flow on iOS. The rule regardless of UX choice: every `barcodeCapture.Enabled = false` must be balanced by a matching `Enabled = true` on the path that returns control to the user.

## Step 7 — Lifecycle management

Drive the camera from `ViewWillAppear` and `ViewWillDisappear`. The camera must not be active while the view controller is off-screen.

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    this.barcodeCapture.Enabled = true;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);
    // Stop the camera so it doesn't keep streaming while off-screen.
    // BarcodeCapture.Enabled = false is also set inside OnBarcodeScanned, so disabling
    // explicitly here is optional but harmless.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}
```

## Complete minimal example

```csharp
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Core.UI.Viewfinder;

namespace MyApp;

public partial class ViewController : UIViewController, IBarcodeCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;
    private BarcodeCapture barcodeCapture = null!;
    private BarcodeCaptureOverlay overlay = null!;

    public ViewController(IntPtr handle) : base(handle) { }
    public ViewController() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.InitializeAndStartBarcodeScanning();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    private void InitializeAndStartBarcodeScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            this.camera.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeCaptureSettings settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128
        });

        this.barcodeCapture = BarcodeCapture.Create(this.dataCaptureContext, settings);
        this.barcodeCapture.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask =
            UIViewAutoresizing.FlexibleHeight | UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);
        this.overlay.Viewfinder = new RectangularViewfinder(
            RectangularViewfinderStyle.Square,
            RectangularViewfinderLineStyle.Light);
    }

    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null)
        {
            frameData.Dispose();
            return;
        }

        // Stop scanning while we display the result. Re-enabled when the user dismisses the alert.
        barcodeCapture.Enabled = false;

        var description = new SymbologyDescription(barcode.Symbology).ReadableName;
        this.ShowResult($"Scanned {barcode.Data} ({description})");

        frameData.Dispose();
    }

    public void ShowResult(string result)
    {
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            var alert = UIAlertController.Create(
                result, message: null, preferredStyle: UIAlertControllerStyle.Alert);
            var ok = UIAlertAction.Create("OK", UIAlertActionStyle.Default, _ =>
            {
                this.barcodeCapture.Enabled = true;
            });
            alert.AddAction(ok);
            this.PresentViewController(alert, animated: true, completionHandler: () => { });
        });
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData) => frameData.Dispose();

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}
```

## Optional configuration

### Async work after a scan (Task-based)

When the scan result requires a network or database call, disable scanning immediately on the scanner thread, then offload the work and re-enable in a `finally` block so scanning always resumes even if the lookup fails. Always dispose the frame data before returning from the callback.

```csharp
public async void OnBarcodeScanned(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    IFrameData frameData)
{
    var data = session.NewlyRecognizedBarcode?.Data;
    try
    {
        if (data == null) return;
        barcodeCapture.Enabled = false;
        try
        {
            var result = await LookupAsync(data); // your async network call
            DispatchQueue.MainQueue.DispatchAsync(() => UpdateUi(result));
        }
        finally
        {
            barcodeCapture.Enabled = true;
        }
    }
    finally
    {
        frameData.Dispose();
    }
}
```

> Using `async void` is acceptable here because the callback signature is `void`. Wrap the body in `try`/`finally` so an exception cannot leave the capture mode permanently disabled and so the frame is always disposed.

### Per-symbology configuration (extensions, checksums, active symbol counts, color-inverted)

`settings.GetSymbologySettings(Symbology.X)` returns the `SymbologySettings` for one symbology (the method is `GetSymbologySettings` — there is no `SettingsForSymbology`). Mutate it in place after enabling the symbology, then pass `settings` to `BarcodeCapture.Create`.

```csharp
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;

// Code 39 full-ASCII extension. SetExtensionEnabled(name, enabled) — there is no IsExtensionEnabled setter.
SymbologySettings code39 = settings.GetSymbologySettings(Symbology.Code39);
code39.SetExtensionEnabled("full_ascii", true);

// Checksum: the property is Checksums (not ChecksumType), typed as the Checksum enum.
code39.Checksums = Checksum.Mod43;

// Active symbol counts for variable-length 1D symbologies (ICollection<short>).
SymbologySettings code128 = settings.GetSymbologySettings(Symbology.Code128);
code128.ActiveSymbolCounts = new HashSet<short>(
    new short[] { 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 });

// Color-inverted (light code on dark background). The property is ColorInvertedEnabled,
// not IsColorInvertedEnabled.
SymbologySettings qr = settings.GetSymbologySettings(Symbology.Qr);
qr.ColorInvertedEnabled = true;
```

| `SymbologySettings` member | Type | Description |
|--------|------|-------------|
| `SetExtensionEnabled(string, bool)` | method | Enable/disable a named extension (e.g. `"full_ascii"`). Read state with `EnabledExtensions`. |
| `Checksums` | `Checksum` (get/set) | Optional checksum(s), e.g. `Checksum.Mod43`. |
| `ActiveSymbolCounts` | `ICollection<short>` (get/set) | Accepted symbol-count range for variable-length symbologies. |
| `ColorInvertedEnabled` | `bool` (get/set) | Accept color-inverted (light-on-dark) codes. |
| `Enabled` | `bool` (get/set) | Whether the symbology is enabled (same as `settings.EnableSymbology`). |

### BarcodeCaptureFeedback

By default, BarcodeCapture beeps and vibrates on success. To customize feedback, modify `barcodeCapture.Feedback.Success` or replace the entire `Feedback` object:

```csharp
using Scandit.DataCapture.Core.Common.Feedback;

// Suppress sound, keep vibration:
barcodeCapture.Feedback.Success = new Feedback(Vibration.DefaultVibration, sound: null);

// Suppress vibration, keep sound:
barcodeCapture.Feedback.Success = new Feedback(vibration: null, Sound.DefaultSound);

// Silent mode (no sound, no vibration):
barcodeCapture.Feedback.Success = new Feedback(vibration: null, sound: null);

// Reset to defaults:
barcodeCapture.Feedback = BarcodeCaptureFeedback.DefaultFeedback;
```

### Viewfinder

Attach a viewfinder to the overlay to draw a guide on the preview:

```csharp
using Scandit.DataCapture.Core.UI.Viewfinder;

overlay.Viewfinder = new RectangularViewfinder(
    RectangularViewfinderStyle.Square,
    RectangularViewfinderLineStyle.Light);
```

For a crosshair-style aiming reticle instead of a rectangle, use `AimerViewfinder` (no constructor arguments):

```csharp
overlay.Viewfinder = new AimerViewfinder();
```

### Overlay highlight brush

`overlay.Brush` controls the fill/stroke drawn over recognized barcodes; `BarcodeCaptureOverlay.DefaultBrush` is the Scandit-blue default. A custom brush is `new Brush(fillColor, strokeColor, strokeWidth)`. On the .NET-for-iOS slice the color arguments accept `UIColor` (implicitly converted to the SDK's `Color`):

```csharp
using Scandit.DataCapture.Core.UI.Style;
using UIKit;

overlay.Brush = new Brush(
    UIColor.Green.ColorWithAlpha(0.2f), // fill
    UIColor.Green,                       // stroke
    2.0f);                               // stroke width
```

### Reject barcodes that don't match

There is no built-in filter callback in BarcodeCapture — implement rejection in the scan callback. For a non-matching `barcode.Data`, clear the highlight by setting `overlay.Brush = Brush.TransparentBrush`, dispose the frame, and return early **without** re-enabling/handling. For a match, restore the normal brush and proceed:

```csharp
public void OnBarcodeScanned(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    IFrameData frameData)
{
    var barcode = session.NewlyRecognizedBarcode;
    if (barcode == null || !IsAccepted(barcode.Data))
    {
        // Don't highlight rejected codes; still dispose the frame on every early return.
        this.overlay.Brush = Brush.TransparentBrush;
        frameData?.Dispose();
        return;
    }

    this.overlay.Brush = BarcodeCaptureOverlay.DefaultBrush;
    barcodeCapture.Enabled = false;
    this.ShowResult($"Scanned {barcode.Data}");
    frameData?.Dispose();
}
```

`Brush.TransparentBrush` is a static property. `frameData?.Dispose()` on the reject path is mandatory — skipping it on early return is the most common cause of a frozen preview (see Key rule 5).

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

`BarcodeCaptureSettings.ScanIntention` defaults to `ScanIntention.Smart` from SDK 7.0. Set `ScanIntention.Manual` if the project uses a single-image frame source, or if the user wants the v6-style behavior:

```csharp
settings.ScanIntention = ScanIntention.Manual;
```

### BatterySaving

```csharp
settings.BatterySaving = BatterySavingMode.Auto; // default
settings.BatterySaving = BatterySavingMode.Off;
settings.BatterySaving = BatterySavingMode.On;
```

### LocationSelection

To restrict scanning to a sub-area of the preview, set `BarcodeCaptureSettings.LocationSelection` to an `ILocationSelection`. `RectangularLocationSelection` is created with the `Create(...)` factory (not `new`), taking a `SizeWithUnit`:

```csharp
using Scandit.DataCapture.Core.Area;
using Scandit.DataCapture.Core.Common.Geometry;

settings.LocationSelection = RectangularLocationSelection.Create(
    new SizeWithUnit(
        new FloatWithUnit(0.9f, MeasureUnit.Fraction),
        new FloatWithUnit(0.3f, MeasureUnit.Fraction)));
```

There are also `RectangularLocationSelection.CreateWithWidthAndAspectRatio(FloatWithUnit width, float heightToWidthAspectRatio)` / `CreateWithHeightAndAspectRatio(FloatWithUnit height, float widthToHeightAspectRatio)` factories that fix one dimension and derive the other from an aspect ratio.

### Composite codes

Composite codes (linear + 2D companion) require both symbologies *and* composite types to be enabled. The .NET API uses a `CompositeType` bit flag and a dedicated `EnableSymbologies(CompositeType)` overload:

```csharp
using Scandit.DataCapture.Barcode.Data;

settings.EnableSymbologies(CompositeType.A | CompositeType.B);
settings.EnabledCompositeTypes = CompositeType.A | CompositeType.B;
```

### BarcodeCaptureLicenseInfo

Once the mode has been attached to the context and the context has emitted `OnModeAdded`, you can inspect which symbologies the active license allows:

```csharp
using Scandit.DataCapture.Barcode.Capture;

// After IDataCaptureContextListener.OnModeAdded fires:
BarcodeCaptureLicenseInfo? licenseInfo = barcodeCapture.BarcodeCaptureLicenseInfo;
ICollection<Symbology>? licensed = licenseInfo?.LicensedSymbologies;
```

`BarcodeCaptureLicenseInfo` is available from `Scandit.DataCapture.Barcode` 8.4 onwards on `dotnet.android` / `dotnet.ios`.

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **Factory wires the mode** — `BarcodeCapture.Create(context, settings)` both creates the mode and attaches it to the context.
3. **Listener thread** — `OnBarcodeScanned` runs on a background thread; always dispatch UI work via `DispatchQueue.MainQueue.DispatchAsync(() => …)`.
4. **Disable inside the callback** — set `barcodeCapture.Enabled = false` before doing any non-trivial work to avoid duplicate scans.
5. **Always dispose the frame** — call `frameData.Dispose()` at the end of `OnBarcodeScanned` and `OnSessionUpdated` (and on early returns). Failing to do so causes a frozen / stuttering preview on iOS.
6. **Camera lifecycle** — turn the camera off in `ViewWillDisappear`, back on in `ViewWillAppear`. Call `barcodeCapture.RemoveListener(this)` when tearing down the view controller (e.g. in `Dispose`).
7. **Overlay is explicit** — `BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView)` adds the overlay to the view in one step.
8. **Info.plist** — `NSCameraUsageDescription` is required. iOS shows the system permission dialog automatically on first camera access.
9. **Symbologies** — enable only what's needed. Variable-length 1D symbologies (Code39, Code128, ITF) may need `ActiveSymbolCounts` adjusted (use `ICollection<short>`).
10. **Settings before construction** — configure `BarcodeCaptureSettings` before passing to `Create`. To change at runtime, use `barcodeCapture.ApplySettingsAsync(newSettings)`.
11. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter` is `TimeSpan`. Use `CodeDuplicate.DefaultDuplicateFilter` / `CodeDuplicate.ReportDataAndSymbologyOnlyOnce` / `TimeSpan.FromMilliseconds(...)` / `TimeSpan.Zero`.
