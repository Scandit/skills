# MatrixScan Count (.NET for iOS) Integration Guide

`BarcodeCount` is the multi-barcode counting mode, designed for high-volume scanning such as inventory and receiving. It scans every barcode in the camera feed during a scan phase, then reports them all at once when the user triggers the scan. `BarcodeCountView` provides the full built-in AR counting UI (camera preview, shutter, list/exit buttons, on-screen highlights and hints).

`BarcodeCount` **does not manage its own camera** — you create a `Camera`, set it as the context's frame source, and switch it on/standby/off across the view-controller lifecycle yourself. And **`BarcodeCountView` is a real `UIView`** that you add to the hierarchy yourself with `this.View.AddSubview(...)`.

Examples below use C# and a `UIViewController`. The same APIs work from any controller — adapt ownership of `DataCaptureContext`, `Camera`, `BarcodeCount`, and `BarcodeCountView` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts `BarcodeCountView` as a XAML element and wires it through `HandlerChanged`, which is different. **Also note:** the official iOS Get Started page contains some MAUI (XAML / `Scandit.DataCapture.Barcode.Maui`) snippets — ignore those here.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeCount` has been available on `dotnet.ios` since **6.19**, so any current stable release supports it.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add both packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
  This is the Scandit iOS framework's minimum deployment target. A matching `MinimumOSVersion` belongs in `Info.plist`.
- **Camera usage description in `Info.plist`.** iOS requires `NSCameraUsageDescription` or the app crashes the moment the camera starts. iOS shows the permission prompt automatically the first time the camera switches on — there is no runtime-permission helper to write (unlike Android).
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>For barcode scanning.</string>
  ```
- **SDK initialization (Scandit 8.0+).** In `AppDelegate.FinishedLaunching` (`application:didFinishLaunchingWithOptions:`), call `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before any Scandit type is constructed. Without this, the first `DataCaptureContext.ForLicenseKey(...)` / `BarcodeCount.Create(...)` call crashes because the container has no registrations.

  ```csharp
  using Foundation;
  using UIKit;
  using Scandit.DataCapture.Barcode;
  using Scandit.DataCapture.Core;

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

          // ... existing launch code (root view controller, navigation controller, etc.)
          return true;
      }
  }
  ```

  If the project already has an `AppDelegate`, add the two `Initialize()` calls at the top of its existing `FinishedLaunching`. **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip it entirely.**
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.

### Project scaffolding (new projects only)

If a .NET iOS project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add `BarcodeCount` on top:

```bash
dotnet new ios -o MyApp
cd MyApp
```

Add the Scandit packages from the bullets above, set `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>`, add `NSCameraUsageDescription` to `Info.plist`, add the `Initialize()` calls to `AppDelegate`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as every extra symbology adds processing overhead.

Once the user responds, ask which `UIViewController` they'd like to integrate `BarcodeCount` into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

### Host UIViewController boilerplate

Pick the right host-class shape for how the controller is created — getting this wrong crashes at launch with `ObjectDisposedException` the moment something (e.g. `UINavigationController(rootViewController)`) touches the native handle.

- **Code-only `UIViewController` instantiated with `new MyViewController()` (no Storyboard / no XIB)** — the common case when adding scanning to a fresh `dotnet new ios` template or a programmatically-built UI:

  ```csharp
  public class ScanViewController : UIViewController
  {
      // No [Register], no `partial`, no IntPtr-handle constructor.
      // Default parameterless constructor is fine.
  }

  // Instantiate:
  var scanVC = new ScanViewController();
  ```

  **Do not** write `new ScanViewController(IntPtr.Zero)` — that calls the ObjC-bridging handle constructor with a null handle, producing a `UIViewController` whose underlying native object is already disposed.

- **`UIViewController` paired with a Storyboard/XIB** (loaded by name via Interface Builder) — keep `partial`, `[Register("...")]`, and the `IntPtr handle` constructor so the runtime can rehydrate it:

  ```csharp
  [Register("ScanViewController")]
  public partial class ScanViewController : UIViewController
  {
      public ScanViewController(IntPtr handle) : base(handle) { }
  }
  ```

  In this case the controller is created by the storyboard loader, never by `new ... (IntPtr.Zero)` in your own code.

If unsure which applies, look at `SceneDelegate` / `AppDelegate`: if it builds the root VC with `new ...()` and there is no `Main.storyboard`, use the code-only shape.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** — do not guess).
2. Ensure `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<key>NSCameraUsageDescription</key>` with a usage string to `Info.plist`.
4. Add `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` to `AppDelegate.FinishedLaunching` (SDK 8.0+).
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

this.dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure BarcodeCountSettings

Choose which barcode symbologies to count. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need.

`BarcodeCountSettings` is constructed with a plain `new` (it is the `BarcodeCount` *mode* that uses a factory, not the settings).

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;

BarcodeCountSettings settings = new BarcodeCountSettings();

HashSet<Symbology> symbologies = new()
{
    Symbology.Ean13Upca,
    Symbology.Ean8,
    Symbology.Code128,
};
settings.EnableSymbologies(symbologies);

// Optional: if the environment guarantees no duplicate barcode values, this speeds up scanning.
settings.ExpectsOnlyUniqueBarcodes = true;
```

`ExpectsOnlyUniqueBarcodes` (default `false`) tells the engine each barcode value appears at most once in the scene, so it can stop re-evaluating a value once counted. Leave it `false` if the same barcode can legitimately appear multiple times.

### Filtering (count only some of the barcodes on a label)

When a label carries several barcodes and you only want to count some of them, filter the rest out through `settings.FilterSettings` (a `BarcodeFilterSettings`, exposed read-only on `BarcodeCountSettings`). Filtering is by symbology, by symbol count, or by a regex on the barcode data. Filtered barcodes are still detected but are covered by a highlight and excluded from the count.

```csharp
using Scandit.DataCapture.Barcode.Data;

BarcodeCountSettings settings = new BarcodeCountSettings();
settings.EnableSymbologies(symbologies);

// Exclude an entire symbology (e.g. count Code 128 but never PDF417):
settings.FilterSettings.ExcludedSymbologies = new HashSet<Symbology> { Symbology.Pdf417 };

// Or exclude by a regex matched against the barcode data (e.g. anything starting with 1234):
settings.FilterSettings.ExcludedCodesRegex = "^1234.*";
```

| `BarcodeFilterSettings` member | Type | Description |
|--------|------|-------------|
| `ExcludedSymbologies` | `ISet<Symbology>` (get/set) | Symbologies to filter out. Has no effect on a symbology that isn't also enabled on the mode. |
| `ExcludedCodesRegex` | `string` (get/set) | Regex matched against each barcode's data; matching barcodes are filtered out. |
| `ExcludedSymbolCounts` | `IDictionary<Symbology, ISet<int>>` (get/set) | Filter by symbol count per symbology. |
| `SetExcludedSymbolCounts(IList<short>, Symbology)` / `GetExcludedSymbolCountsForSymbology(Symbology)` | methods | Per-symbology symbol-count filtering. |

By default the filtered barcodes are covered by a transparent layer. To change that highlight's color/transparency, set the **view's** `FilterSettings` property (distinct from `BarcodeCountSettings.FilterSettings`, which holds the filter *rules* above — this one holds the filter *highlight*). On .NET the highlight type is the **`IBarcodeFilterHighlightSettings` interface** (the cross-platform name `BarcodeFilterHighlightSettings` is exposed as this interface), implemented by `BarcodeFilterHighlightSettingsBrush`. The brush wrapper has **no public constructor** — build it with the static `BarcodeFilterHighlightSettingsBrush.Create(Brush)` factory:

```csharp
using Scandit.DataCapture.Barcode.Filter.UI.Overlay;  // BarcodeFilterHighlightSettingsBrush
using Scandit.DataCapture.Core.UI.Style;

this.barcodeCountView.FilterSettings =
    BarcodeFilterHighlightSettingsBrush.Create(new Brush(fillColor, strokeColor, strokeWidth));
```

### BarcodeCountSettings members

| Member | Type | Description |
|--------|------|-------------|
| `new BarcodeCountSettings()` | constructor | All symbologies disabled. |
| `EnableSymbology(Symbology, bool)` | method | Enable/disable a single symbology. |
| `EnableSymbologies(ICollection<Symbology>)` | method | Enable a set in one call. |
| `GetSymbologySettings(Symbology)` | method | Per-symbology `SymbologySettings` (`ActiveSymbolCounts`, checksum config, etc.). |
| `EnabledSymbologies` | `ICollection<Symbology>` (get) | Currently enabled symbologies. |
| `ExpectsOnlyUniqueBarcodes` | `bool` (get/set) | When `true`, assumes each barcode appears once and optimizes accordingly. |
| `DisableModeWhenCaptureListCompleted` | `bool` (get/set) | When using a capture list, auto-disable the mode once the list is complete. |
| `MappingEnabled` | `bool` (get/set) | Enables the spatial map (`session.GetSpatialMap()`). |
| `FilterSettings` | `BarcodeFilterSettings` (get) | Per-symbology filtering configuration. |
| `SetProperty` / `GetProperty` / `GetProperty<T>` / `TryGetProperty<T>` | methods | Read/write experimental engine flags. |

## Step 3 — Create the BarcodeCount mode

`BarcodeCount` is created with a **static factory** that attaches the mode to the context. There is **no** public `new BarcodeCount(...)` constructor.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;

this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);
```

There is also a `BarcodeCount.Create(settings)` overload that creates the mode without a context (you would attach it to a context later); for a normal integration use the two-argument form above.

### BarcodeCount members

| Member | Description |
|--------|-------------|
| `static BarcodeCount Create(DataCaptureContext? context, BarcodeCountSettings settings)` | Factory — creates the mode and attaches it to the context. |
| `static BarcodeCount Create(BarcodeCountSettings settings)` | Factory — creates the mode without a context. |
| `Context` | `DataCaptureContext?` (get). |
| `Feedback` | `BarcodeCountFeedback` (get/set) — sound / vibration. See Optional configuration. |
| `Enabled` | `bool` (get/set) — **set `true` to process frames.** Toggle in `ViewWillAppear`/`ViewWillDisappear`. |
| `static CameraSettings RecommendedCameraSettings` | Recommended camera settings for counting. |
| `ApplySettingsAsync(BarcodeCountSettings)` | `Task` — applies new settings. |
| `AddListener(IBarcodeCountListener)` / `RemoveListener(...)` | Register/remove a listener. |
| `event EventHandler<BarcodeCountEventArgs> Scanned` | Raised when a scan phase finishes. Corresponds to `IBarcodeCountListener.OnScan`. **Recommended** in idiomatic C#. |
| `Reset()` | Clear all counted barcodes and AR overlays for a fresh scanning process. |
| `StartScanningPhase()` / `EndScanningPhase()` | Manually delimit a scanning phase (advanced; the view's shutter normally drives this). |
| `SetBarcodeCountCaptureList(BarcodeCountCaptureList)` | Apply a capture/receiving list (see that section). |
| `SetAdditionalBarcodes(IList<Barcode>)` / `ClearAdditionalBarcodes()` | Seed/clear barcodes that should be considered already counted (e.g. restored across backgrounding). |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the `Scanned` event — not both for the same handler.** They both deliver the scan result; subscribing to both double-processes.

## Step 4 — Set up the camera (you manage it; the view does not)

Get the default camera, apply the recommended settings, and set it as the context's frame source. Keep a reference so you can switch it on/standby/off across the lifecycle.

```csharp
using Scandit.DataCapture.Core.Source;

this.camera = Camera.GetDefaultCamera();
if (this.camera is null)
{
    throw new InvalidOperationException("MatrixScan Count requires a camera.");
}

this.camera.ApplySettingsAsync(BarcodeCount.RecommendedCameraSettings);
this.dataCaptureContext.SetFrameSourceAsync(this.camera);
```

> **Do not `await` these inside `ViewDidLoad`** — and **do not** make `ViewDidLoad` `async void`. An `async void` lifecycle method returns to UIKit at the first `await`, so `ViewWillAppear` fires before `barcodeCount` / `barcodeCountView` are constructed; the null-guard in Step 7 then skips `Enabled = true` and the camera switch-on, leaving you with a black screen and no scans. Fire-and-forget the two async calls above and keep `ViewDidLoad` synchronous. If you genuinely need to await camera setup, do it before pushing the view controller (e.g. in the parent) rather than inside `ViewDidLoad`.

The camera is off by default. You turn it on in `ViewWillAppear` and put it to standby/off in `ViewWillDisappear` (Step 7). Do **not** look for `barcodeCountView.OnResume()`/`Start()` — those don't exist; the camera is the lifecycle handle.

## Step 5 — Create and add the BarcodeCountView

`BarcodeCountView.Create` takes a **`CGRect` frame** (typically `this.View!.Bounds`), the `DataCaptureContext`, the `BarcodeCount` mode, and optionally a `BarcodeCountViewStyle`. The returned view **is** a `UIView` (implicit conversion), so add it with `AddSubview`.

```csharp
using Scandit.DataCapture.Barcode.Count.UI;
using UIKit;

this.barcodeCountView = BarcodeCountView.Create(
    this.View!.Bounds,
    this.dataCaptureContext,
    this.barcodeCount,
    BarcodeCountViewStyle.Icon); // or BarcodeCountViewStyle.Dot

// BarcodeCountView IS a UIView — add it and let it resize with its parent.
UIView platformView = this.barcodeCountView;
platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
this.View.AddSubview(this.barcodeCountView);
```

`BarcodeCountViewStyle` is `Icon` (counted barcodes show a check-mark icon) or `Dot` (a dot). Use the three-argument `Create` overload to accept the default style.

### Common BarcodeCountView members

| Member | Description |
|--------|-------------|
| `static Create(CGRect, DataCaptureContext, BarcodeCount)` / `Create(CGRect, DataCaptureContext, BarcodeCount, BarcodeCountViewStyle)` | Factory. First arg is a `CGRect` frame, not a context or parent view. |
| `implicit operator View(BarcodeCountView)` | Lets you treat the view as a `UIKit.UIView` and pass it to `AddSubview(...)`. |
| `Style` | `BarcodeCountViewStyle` (get). |
| `Listener` | `IBarcodeCountViewListener?` (get/set) — custom brushes + tap callbacks. |
| `ShouldShowListButton` / `ShouldShowExitButton` / `ShouldShowShutterButton` / `ShouldShowFloatingShutterButton` / `ShouldShowSingleScanButton` / `ShouldShowClearHighlightsButton` / `ShouldShowStatusModeButton` / `ShouldShowUserGuidanceView` / `ShouldShowHints` / `ShouldShowToolbar` / `ShouldShowScanAreaGuides` / `ShouldShowListProgressBar` / `ShouldShowTorchControl` | `bool` toggles for the built-in UI. |
| `ShouldDisableModeOnExitButtonTapped` | `bool`. |
| `TapToUncountEnabled` | `bool`. |
| `TorchControlPosition` | `Anchor`. |
| `RecognizedBrush` / `NotInListBrush` / `AcceptedBrush` / `RejectedBrush` | `Brush?` (get/set) overlay styles; static `Default*Brush` provide the defaults. |
| `BarcodeNotInListActionSettings` | `BarcodeCountNotInListActionSettings` (get) — see that section. |
| **`HardwareTriggerEnabled`** (iOS-only) | `bool` (get/set) — enable scanning via a hardware button. (Android uses `EnableHardwareTrigger(int?)` instead — do not use that here.) |
| **`PrepareScanning(DataCaptureContext)` / `StopScanning()`** (iOS-only) | Prepare/stop the scanning surface. |
| `SetToolbarSettings(BarcodeCountToolbarSettings)` | Customize toolbar button text. |
| `SetStatusProvider(IBarcodeCountStatusProvider)` | Enable status mode (see that section). |
| `ClearHighlights()` | Clear current on-screen highlights. |
| `SetBrushForRecognizedBarcode` / `*NotInList` / `*Accepted` / `*Rejected` `(TrackedBarcode, Brush?)` | Per-barcode brush override. |
| `*AccessibilityLabel` / `*AccessibilityHint` (iOS-only) | VoiceOver text for the built-in buttons. |
| `event ExitButtonTapped` / `ListButtonTapped` / `SingleScanButtonTapped` | Toolbar button taps. See Step 8. |
| `Dispose()` | Releases native resources. |

## Step 6 — Handle scan results

`Scanned` (equivalently `IBarcodeCountListener.OnScan`) fires when a scan phase finishes. It runs on a **background thread**, and the `BarcodeCountSession` is only valid inside the callback — copy out the barcodes you need immediately.

The recommended idiomatic C# pattern is the event:

```csharp
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;
using UIKit;

// Subscribe in ViewWillAppear (see lifecycle note in Step 7):
this.barcodeCount.Scanned += this.OnBarcodeCountScanned;

private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
{
    // Copy the recognized barcodes out of the session right away.
    List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
    List<Barcode> additional = args.Session.AdditionalBarcodes.ToList();

    // Dispatch UI updates onto the main thread.
    UIApplication.SharedApplication.InvokeOnMainThread(() =>
    {
        foreach (Barcode barcode in recognized)
        {
            // barcode.Data, barcode.Symbology
        }
    });
}
```

If you prefer the listener interface, implement `IBarcodeCountListener` — note it has **three** methods:

```csharp
using Scandit.DataCapture.Core.Data;

public class ViewController : UIViewController, IBarcodeCountListener
{
    public void OnScan(BarcodeCount mode, BarcodeCountSession session, IFrameData data)
    {
        List<Barcode> recognized = session.RecognizedBarcodes.ToList();
        UIApplication.SharedApplication.InvokeOnMainThread(() => /* update UI */);
    }

    public void OnObservationStarted(BarcodeCount mode) { }
    public void OnObservationStopped(BarcodeCount mode) { }
}

// In setup:
this.barcodeCount.AddListener(this);
```

### BarcodeCountSession members

| Member | Type | Description |
|--------|------|-------------|
| `RecognizedBarcodes` | `IList<Barcode>` | All barcodes counted in this scan phase. |
| `AdditionalBarcodes` | `IList<Barcode>` | Barcodes added via `SetAdditionalBarcodes` (e.g. restored across backgrounding). |
| `FrameSequenceId` | `long` | Identifier of the underlying frame sequence. |
| `Reset()` | method | Reset all session state. Only call from inside the callback. |
| `GetSpatialMap()` / `GetSpatialMap(int rows, int cols)` | `BarcodeSpatialGrid?` | The spatial layout of counted barcodes (requires `settings.MappingEnabled = true`). |

### Storing scanned barcodes across the results screen

Because the session is not accessible outside `OnScan`, store the barcodes if you need them later (e.g. to show a results list when the user taps the List or Exit button). A common pattern is to keep them in a shared manager and, when the app goes to background, persist the current barcodes as *additional* barcodes so the count survives:

```csharp
// When leaving for a results screen, or going to background:
this.barcodeCount.SetAdditionalBarcodes(savedBarcodes);

// To start a brand-new counting process:
this.barcodeCount.ClearAdditionalBarcodes();
this.barcodeCount.Reset();
```

To run that save on backgrounding, observe `UIApplication.DidEnterBackgroundNotification`:

```csharp
this.enterBackgroundToken = NSNotificationCenter.DefaultCenter.AddObserver(
    UIApplication.DidEnterBackgroundNotification,
    _ => { /* SetAdditionalBarcodes(...) */ });
```

## Step 7 — Camera lifecycle

Toggle the camera and the mode across the view-controller lifecycle. The camera — not the view — is the lifecycle handle. iOS shows the camera permission prompt automatically the first time the camera turns on (because of `NSCameraUsageDescription`), so there is no permission code to write.

```csharp
using Scandit.DataCapture.Core.Source;

public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);

    // (Re)subscribe and enable the mode so frames are processed.
    this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
    this.barcodeCount.Enabled = true;

    // Turn the camera on (iOS prompts for permission the first time).
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);

    // Standby keeps the camera warm when navigating within the app;
    // use FrameSourceState.Off when actually leaving / backgrounding.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Standby);
    this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
}
```

> If you navigate to a results screen *within* the app and want to keep the count, use `FrameSourceState.Standby` (not `Off`) and avoid resetting — only switch fully `Off` (and optionally save additional barcodes) when actually backgrounding. The official sample tracks a `shouldCameraStandby` flag for exactly this.

Release native resources when the controller is torn down (e.g. in `Dispose`): `this.barcodeCountView.Dispose();` and `this.barcodeCount.Dispose();`.

## Step 8 — List / Exit / Single-Scan button taps

The built-in toolbar buttons are surfaced as C# events on `BarcodeCountView`. Subscribe to react when the user taps them.

The standard pattern is to push a results view controller onto the navigation stack, so **the scanning view controller must be hosted inside a `UINavigationController`**. In `SceneDelegate.WillConnect` (or wherever you build the root):

```csharp
var scanVC = new ScanViewController();
this.Window!.RootViewController = new UINavigationController(scanVC);
```

`BarcodeCountView` has its own toolbar, so hide the navigation bar while the scanner is visible:

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    this.NavigationController?.SetNavigationBarHidden(true, animated: false);
    // ...rest of ViewWillAppear (Step 7)...
}
```

> **`SetNavigationBarHidden` is shared state on the `UINavigationController`.** Hiding the bar in `ScanViewController` leaves it hidden on any view controller you push afterwards — so the pushed list screen has no back button and the user is stranded. Un-hide it in the pushed VC's `ViewWillAppear`:
>
> ```csharp
> public override void ViewWillAppear(bool animated)
> {
>     base.ViewWillAppear(animated);
>     this.NavigationController?.SetNavigationBarHidden(false, animated: animated);
> }
> ```
>
> The system back button then appears automatically (driven by the pushed VC's `Title`), and the scanner's own `ViewWillAppear` re-hides the bar on the way back. The working Scandit sample takes a heavier route — keeping the nav bar hidden and building a custom top bar with its own back button — which is also fine if you want full control.

Then wire the events to push a results screen:

```csharp
this.barcodeCountView.ListButtonTapped += (sender, args) =>
{
    // Order not yet complete — show progress so far.
    var snapshot = new List<Barcode>(this.scannedBarcodes);
    var listVC = new ScannedItemsViewController(snapshot, isOrderCompleted: false);
    this.NavigationController?.PushViewController(listVC, animated: true);
};

this.barcodeCountView.ExitButtonTapped += (sender, args) =>
{
    // The user finished — show the final results.
    var snapshot = new List<Barcode>(this.scannedBarcodes);
    var listVC = new ScannedItemsViewController(snapshot, isOrderCompleted: true);
    this.NavigationController?.PushViewController(listVC, animated: true);
};

this.barcodeCountView.SingleScanButtonTapped += (sender, args) =>
{
    // The user wants to switch to a single-barcode scan flow.
};
```

> **Do not stop at `Console.WriteLine`** in these handlers in a real integration — the buttons are useless to the end user unless they navigate somewhere. A minimal `ScannedItemsViewController` can be a plain `UITableViewController` that takes the list in its constructor and renders one row per barcode (`barcode.Data`, `barcode.Symbology`). If you want both labels in each row, instantiate cells with `new UITableViewCell(UITableViewCellStyle.Subtitle, reuseId)` — `RegisterClassForCellReuse(typeof(UITableViewCell), …)` always creates `Default`-style cells where `DetailTextLabel` is `null` and dereferencing it throws `NullReferenceException`.

Each event argument (`ListButtonTappedEventArgs`, `ExitButtonTappedEventArgs`, `SingleScanButtonTappedEventArgs`) exposes a `.View` property if you need it.

## Complete minimal example

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp;

// Code-only host (no Storyboard/XIB). If the controller is paired with a XIB,
// add [Register], `partial`, and the `IntPtr handle` constructor instead —
// see "Host UIViewController boilerplate" earlier in this guide.
public class ViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext? dataCaptureContext;
    private Camera? camera;
    private BarcodeCount? barcodeCount;
    private BarcodeCountView? barcodeCountView;

    private readonly List<Barcode> scannedBarcodes = new();

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Camera (you manage it — the view does not).
        // Keep ViewDidLoad SYNCHRONOUS — fire-and-forget the async camera setup.
        // An `async void ViewDidLoad` returns at the first await, so UIKit fires
        // `ViewWillAppear` before `barcodeCount` / `barcodeCountView` exist; the
        // null-guard there then skips `Enabled = true` and the camera switch-on,
        // giving you a black screen with no scans.
        this.camera = Camera.GetDefaultCamera();
        if (this.camera is not null)
        {
            this.camera.ApplySettingsAsync(BarcodeCount.RecommendedCameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        // Configure and create BarcodeCount.
        BarcodeCountSettings settings = new BarcodeCountSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });
        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);

        // Host the counting UI. BarcodeCountView IS a UIView — add it yourself.
        this.barcodeCountView = BarcodeCountView.Create(
            this.View!.Bounds, this.dataCaptureContext, this.barcodeCount, BarcodeCountViewStyle.Icon);
        UIView platformView = this.barcodeCountView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.barcodeCountView);

        this.barcodeCountView.ListButtonTapped += (s, e) => this.ShowResults();
        this.barcodeCountView.ExitButtonTapped += (s, e) => this.ShowResults();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        if (this.barcodeCount is null) return;
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
        this.barcodeCount.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Standby);
        if (this.barcodeCount is not null)
        {
            this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
        }
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        UIApplication.SharedApplication.InvokeOnMainThread(() =>
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

## Capture list (receiving / "scan against an expected list")

A capture list checks scanned barcodes against an expected set of `TargetBarcode`s, classifying them as correct / wrong / missing. Both `BarcodeCountCaptureList` and `TargetBarcode` use **factory** methods.

```csharp
using Scandit.DataCapture.Barcode.Count.Capture.List;
using Scandit.DataCapture.Barcode.Batch.Data;

private sealed class CaptureListListener : IBarcodeCountCaptureListListener
{
    public void OnObservationStarted() { }
    public void OnObservationStopped() { }

    public void OnCaptureListSessionUpdated(BarcodeCountCaptureListSession session)
    {
        IList<TrackedBarcode> correct = session.CorrectBarcodes;
        IList<TrackedBarcode> wrong   = session.WrongBarcodes;
        IList<TargetBarcode>  missing = session.MissingBarcodes;
        // Update progress UI...
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
settings.DisableModeWhenCaptureListCompleted = true;
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

`BarcodeCountFeedback` exposes two `Core.Common.Feedback.Feedback` slots:

| Property | Type | Description |
|----------|------|-------------|
| `Success` | `Feedback` | Played on a successful scan. |
| `Failure` | `Feedback` | Played on a failed / rejected scan. |

To customize one:
```csharp
using Scandit.DataCapture.Core.Common.Feedback;

this.barcodeCount.Feedback = new BarcodeCountFeedback
{
    Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
    Failure = new Feedback(null, null),  // silent on failure
};
```

> `BarcodeCountFeedback.DefaultFeedback` is a **static property** in .NET — not a method. Calling it as `DefaultFeedback()` is a compile error.

### Custom brushes and barcode taps (IBarcodeCountViewListener)

Assign `barcodeCountView.Listener` to color barcodes differently and react to taps. **On iOS this interface has 9 methods — there is no `OnCaptureListCompleted` (that's Android-only).**

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

this.barcodeCountView.Listener = new ViewListener();
```

> Brush customization is most relevant with `BarcodeCountViewStyle.Dot`.

### Not-in-list action

When a capture list is set, you can prompt the user to accept/reject barcodes that are not on the list, via `barcodeCountView.BarcodeNotInListActionSettings`:

```csharp
var action = this.barcodeCountView.BarcodeNotInListActionSettings;
action.Enabled = true;
action.AcceptButtonText = "Accept";
action.RejectButtonText = "Reject";
action.BarcodeAcceptedHint = "Barcode accepted";
action.BarcodeRejectedHint = "Barcode rejected";
```

### Status mode

Status mode lets you annotate each counted barcode with a status (expired, fragile, low stock, etc.). Implement `IBarcodeCountStatusProvider` and register it via `SetStatusProvider`:

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

### Hardware trigger (iOS)

On iOS, enable scanning via a hardware button with a single `bool` property:

```csharp
this.barcodeCountView.HardwareTriggerEnabled = true;
```

> This is the iOS API. The Android binding instead uses `EnableHardwareTrigger(int? keyCode)` + static `HardwareTriggerSupported` — those do **not** exist on iOS.

### Toolbar text

```csharp
var toolbar = new BarcodeCountToolbarSettings
{
    AudioOnButtonText = "Sound on",
    AudioOffButtonText = "Sound off",
    VibrationOnButtonText = "Vibration on",
    VibrationOffButtonText = "Vibration off",
};
this.barcodeCountView.SetToolbarSettings(toolbar);
```

### Apply settings at runtime

```csharp
BarcodeCountSettings updated = new BarcodeCountSettings();
updated.EnableSymbology(Symbology.Qr, true);
await this.barcodeCount.ApplySettingsAsync(updated);
```

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **`BarcodeCount.Create(...)`, `new BarcodeCountSettings()`** — the mode uses a factory (no public constructor); the settings use `new`.
3. **You manage the camera** — `Camera.GetDefaultCamera()`, `camera.ApplySettingsAsync(BarcodeCount.RecommendedCameraSettings)`, `dataCaptureContext.SetFrameSourceAsync(camera)`, `camera.SwitchToDesiredStateAsync(FrameSourceState.On/Standby/Off)` in `ViewWillAppear`/`ViewWillDisappear`. `BarcodeCountView` has no `OnResume`/`OnPause`/`Start`/`Stop`.
4. **Set `barcodeCount.Enabled = true`** so frames are processed; toggle it across the lifecycle.
5. **`BarcodeCountView` is a `UIView`** — `BarcodeCountView.Create(View.Bounds, …)` then `View.AddSubview(view)`. The first `Create` argument is a `CGRect` frame, not a context or parent view.
6. **`Scanned` event is idiomatic** — prefer `barcodeCount.Scanned += handler` over `AddListener`. Both deliver the scan result.
7. **`IBarcodeCountListener` has three methods** — `OnScan`, `OnObservationStarted`, `OnObservationStopped`.
8. **Copy barcodes out of the session immediately** — `session.RecognizedBarcodes.ToList()` inside the callback; the session is invalid afterward. `OnScan` runs on a background thread, so dispatch UI work with `UIApplication.SharedApplication.InvokeOnMainThread(...)`.
9. **Capture list & TargetBarcode use factories** — `BarcodeCountCaptureList.Create(listener, targets)`, `TargetBarcode.Create(data, quantity)`, applied with `barcodeCount.SetBarcodeCountCaptureList(list)`.
10. **Feedback uses `Success`/`Failure`** — empty `new BarcodeCountFeedback()` is silent; `BarcodeCountFeedback.DefaultFeedback` (static property) restores defaults.
11. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Code128`, not the native Swift style.
12. **SDK 8.0+ requires `Initialize()` in `AppDelegate`** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` in `FinishedLaunching` before any Scandit type is used.
13. **`NSCameraUsageDescription` in `Info.plist`** — required; iOS prompts for camera permission automatically. No runtime-permission helper to write.
14. **iOS-only view APIs**: `HardwareTriggerEnabled`, `PrepareScanning`/`StopScanning`, `*AccessibilityLabel`/`*AccessibilityHint`. Don't use Android's `EnableHardwareTrigger`/`*ContentDescription`/`Context` here.
