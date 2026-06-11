# MatrixScan AR (.NET for iOS) Integration Guide

`BarcodeAr` is the multi-barcode AR scanning mode. It simultaneously tracks all barcodes in the camera feed and overlays interactive highlights and annotations on each one in real time. Unlike `BarcodeCapture` or `BarcodeBatch`, `BarcodeAr` does **not** require a separate `Camera`, `DataCaptureView`, or `BarcodeCaptureOverlay` — the `BarcodeArView` manages its own camera and rendering. AR overlays are driven by **provider interfaces**: `IBarcodeArHighlightProvider` supplies a highlight per barcode, and `IBarcodeArAnnotationProvider` supplies an optional annotation. In the .NET binding both providers are **async / Task-based**.

Examples below use C# 12 and a `UIViewController`. The same APIs work in storyboards, XIBs, or programmatically-instantiated controllers — adapt ownership of `DataCaptureContext`, `BarcodeAr`, and `BarcodeArView` to the project's existing structure.

> **Constructor pattern depends on instantiation path.** Storyboard / XIB inflation uses `public MyVC(IntPtr handle) : base(handle) { }`. Programmatic instantiation (no `Main.storyboard`, root view controller set from `SceneDelegate.WillConnect` or `AppDelegate`) needs a parameterless `public MyVC() : base() { }` and `new MyVC()`. **Never construct a VC with `new MyVC(IntPtr.Zero)`** — the native peer is not initialized, `ViewDidLoad` may never fire, and you'll see a black screen with no preview and no scans. If you support both paths, declare both constructors.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration uses XAML and a `UseScanditBarcode` / builder-based DI registration which are different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeAr` was introduced in **`dotnet.ios` 7.2**. If the latest stable is older than 7.2 (extremely unlikely today), stop and tell the user — the integration cannot proceed.

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
  Without this key the app crashes on first camera access. iOS prompts the user automatically the first time the camera is opened; there is **no separate runtime-request API** to call (the Scandit SDK triggers the standard system prompt when the camera starts). This is different from .NET for Android, which needs a manual `RequestPermissions` call.
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
  Matches the official Scandit iOS samples' `Info.plist` `MinimumOSVersion`.
- **SDK initialization (Scandit 8.0+).** Initialize the Scandit DI container in `AppDelegate.FinishedLaunching` before any Scandit type is constructed. Without this the first `DataCaptureContext.ForLicenseKey(...)` / `new BarcodeAr(...)` / `BarcodeArView.Create(...)` call crashes because the container has no registrations.

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

**Recommended:** scaffold a buildable shell with the official template, then add `BarcodeAr` on top:

```bash
dotnet new ios -o MyApp
cd MyApp
```

This produces a project with the correct `OutputType`, a working `AppDelegate` / `SceneDelegate`, an `Info.plist`, and storyboard-or-programmatic UI scaffolding. Add the Scandit packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `15.0` (or higher), add `NSCameraUsageDescription` to `Info.plist`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves tracking performance and accuracy.

Once the user responds, ask them which `UIViewController` they'd like to integrate `BarcodeAr` into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

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
| `BarcodeAr`, `BarcodeArSettings`, `IBarcodeArListener`, `BarcodeArSession`, `BarcodeArEventArgs` | `Scandit.DataCapture.Barcode.Ar.Capture` |
| `BarcodeArFeedback` | `Scandit.DataCapture.Barcode.Ar.Feedback` |
| `BarcodeArView`, `BarcodeArViewSettings`, `HighlightForBarcodeTappedEventArgs` | `Scandit.DataCapture.Barcode.Ar.UI` |
| `IBarcodeArHighlight`, `IBarcodeArHighlightProvider`, `BarcodeArRectangleHighlight`, `BarcodeArCircleHighlight`, `BarcodeArCircleHighlightPreset` | `Scandit.DataCapture.Barcode.Ar.UI.Highlight` |
| `IBarcodeArAnnotation`, `IBarcodeArAnnotationProvider`, `BarcodeArInfoAnnotation`, `BarcodeArStatusIconAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArResponsiveAnnotation`, `BarcodeArAnnotationTrigger` | `Scandit.DataCapture.Barcode.Ar.UI.Annotations` |
| `BarcodeArInfoAnnotationBodyComponent`, `BarcodeArInfoAnnotationHeader`, `BarcodeArInfoAnnotationFooter`, `BarcodeArInfoAnnotationAnchor`, `BarcodeArInfoAnnotationWidthPreset`, `IBarcodeArInfoAnnotationListener` | `Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info` |
| `BarcodeArPopoverAnnotationButton`, `IBarcodeArPopoverAnnotationListener` | `Scandit.DataCapture.Barcode.Ar.UI.Annotations.Popover` |
| `TrackedBarcode` | `Scandit.DataCapture.Barcode.Batch.Data` |
| `Symbology`, `Barcode`, `SymbologyDescription` | `Scandit.DataCapture.Barcode.Data` |
| `DataCaptureContext` | `Scandit.DataCapture.Core.Capture` |
| `CameraPosition` | `Scandit.DataCapture.Core.Source` |
| `IFrameData` | `Scandit.DataCapture.Core.Data` |
| `Anchor`, `Quadrilateral` | `Scandit.DataCapture.Core.Common.Geometry` |
| `Brush` | `Scandit.DataCapture.Core.UI.Style` |
| `Feedback`, `Sound`, `Vibration` | `Scandit.DataCapture.Core.Common.Feedback` |

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

private DataCaptureContext dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Configure BarcodeArSettings

Choose which barcode symbologies to track. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need; each extra symbology adds tracking overhead.

`BarcodeArSettings` is constructed with a plain `new` — there is no `BarcodeArSettings.Create()` factory.

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Data;

BarcodeArSettings settings = new BarcodeArSettings();

HashSet<Symbology> symbologies = new()
{
    Symbology.Ean13Upca,
    Symbology.Code128,
    Symbology.Qr,
};
settings.EnableSymbologies(symbologies);

// Optional: adjust active symbol counts for variable-length 1D symbologies.
settings.GetSymbologySettings(Symbology.Code128).ActiveSymbolCounts =
    new short[] { 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };
```

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

> Unlike `BarcodeCaptureSettings`, `BarcodeArSettings` does **not** expose `LocationSelection`, `CodeDuplicateFilter`, `BatterySaving`, or `ScanIntention`. Those concepts don't apply to AR tracking.

## Step 3 — Create the BarcodeAr mode

`BarcodeAr` uses a direct constructor that takes the context — unlike `BarcodeBatch` which uses a `Create(...)` factory.

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;

this.barcodeAr = new BarcodeAr(this.dataCaptureContext, settings);
```

There is no `BarcodeAr.Create(...)` factory and no `BarcodeAr.ForDataCaptureContext(...)` static.

### BarcodeAr members

| Member | Description |
|--------|-------------|
| `new BarcodeAr(DataCaptureContext? context, BarcodeArSettings settings)` | Constructor — creates the mode and attaches it to the context. |
| `Feedback` | `BarcodeArFeedback` (get/set) — sound / vibration for scan and tap events. See "Customize feedback" below. |
| `ApplySettingsAsync(BarcodeArSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(IBarcodeArListener)` / `RemoveListener(IBarcodeArListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeArEventArgs> SessionUpdated` | Raised on every processed frame. **Recommended** in idiomatic C#. |
| `static CameraSettings RecommendedCameraSettings` | Get the recommended camera settings (used implicitly when `BarcodeArView.Create` is passed `null` for `cameraSettings`). Static **property**, not a method. |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the event — not both for the same handler.** They both fire `OnSessionUpdated`/`SessionUpdated`; subscribing to both leads to double-processing.

## Step 4 — Configure BarcodeArViewSettings (optional)

`BarcodeArViewSettings` is intentionally minimal. It only exposes three properties; if all you want is the defaults, you can pass `new BarcodeArViewSettings()` straight to `BarcodeArView.Create(...)`.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Core.Source;

BarcodeArViewSettings viewSettings = new BarcodeArViewSettings
{
    SoundEnabled = true,                                // beep on each tracked barcode (default true)
    HapticEnabled = true,                               // vibrate on each tracked barcode (default true)
    DefaultCameraPosition = CameraPosition.WorldFacing, // default; or UserFacing for the selfie camera
};
```

### BarcodeArViewSettings properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `SoundEnabled` | `bool` | `true` | Whether a beep plays on each tracked barcode. |
| `HapticEnabled` | `bool` | `true` | Whether haptics fire on each tracked barcode. |
| `DefaultCameraPosition` | `CameraPosition` | `WorldFacing` | Camera position to open on start. |

> `BarcodeArViewSettings` does **not** expose `TriggerButtonCollapseTimeout`, `InactiveStateTimeout`, `ToastSettings`, `DefaultMiniPreviewSize`, or `DefaultScanningMode` — those are SparkScan properties. Do not invent them on this type.

## Step 5 — Create the BarcodeArView

`BarcodeArView` is the AR rendering surface. The `Create` factory attaches the view to the `parentView` (a `UIView`) you pass — typically `this.View` of the view controller, or a dedicated `@IBOutlet` / outlet-style `UIView` if the project uses storyboards with a container view.

The factory takes a nullable `cameraSettings` — pass `null` to use `BarcodeAr.RecommendedCameraSettings` automatically.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI;
using UIKit;

// In ViewDidLoad / your setup helper, after this.View exists:
BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();

this.barcodeArView = BarcodeArView.Create(
    parentView: this.View!,           // any UIView — typically the VC's root view
    barcodeAr: this.barcodeAr,
    dataCaptureContext: this.dataCaptureContext,
    settings: viewSettings,
    cameraSettings: null);            // null = use BarcodeAr.RecommendedCameraSettings
```

You do **not** call `this.View.AddSubview(barcodeArView)` — the `Create` factory wires it in. If you need the underlying `UIView` (e.g. to query it from a test or insert another subview on top), `BarcodeArView` declares an `implicit operator View(BarcodeArView)` for that purpose (`View` is aliased to `UIKit.UIView` on iOS); do not depend on it for normal use.

### BarcodeArView members

| Member | Description |
|--------|-------------|
| `static BarcodeArView Create(UIView parentView, BarcodeAr barcodeAr, DataCaptureContext dataCaptureContext, BarcodeArViewSettings settings, CameraSettings? cameraSettings)` | Static factory — creates the view and attaches it to `parentView`. Pass `null` for `cameraSettings` to use `BarcodeAr.RecommendedCameraSettings`. |
| `HighlightProvider` | `IBarcodeArHighlightProvider?` — supplies a highlight per tracked barcode. If `null`, a default rectangle highlight is shown. |
| `AnnotationProvider` | `IBarcodeArAnnotationProvider?` — supplies an annotation per tracked barcode. If `null`, no annotation is shown. |
| `ShouldShowTorchControl` | `bool` (default `false`) — whether to render the built-in torch toggle button. |
| `ShouldShowZoomControl` | `bool` — whether to render the built-in zoom switch button. |
| `ShouldShowCameraSwitchControl` | `bool` (default `false`) — whether to render the camera-switch button (between world-facing and user-facing cameras). |
| `ShouldShowMacroModeControl` | `bool` (default `false`) — **iOS-only**: whether to render the macro-mode toggle button. |
| `TorchControlPosition` | `Anchor` (default `TopLeft`) — where the torch button sits. |
| `ZoomControlPosition` | `Anchor` (default `BottomRight`). |
| `CameraSwitchControlPosition` | `Anchor` (default `TopRight`). |
| `MacroModeControlPosition` | `Anchor` (default `TopRight`) — **iOS-only**. |
| `Start()` | Begin scanning. Call from `ViewWillAppear` (matches the official sample). |
| `Stop()` | Stop scanning and release the camera. Call from `ViewWillDisappear`. |
| `Pause()` | Pause scanning (keeps overlays and camera attached). Use to temporarily suspend tracking without releasing the camera. |
| `Reset()` | Clear all current highlights/annotations and re-query the providers for each tracked barcode. |
| `GetNotificationPresenter()` | Returns an `INotificationPresenter` that can render notifications inside the AR view (8.5+). |
| `event EventHandler<HighlightForBarcodeTappedEventArgs> HighlightForBarcodeTapped` | Fires when the user taps a highlight. See Step 9. |
| `Dispose()` | Releases native resources and clears the cache. Call from the view controller's `Dispose(bool)` override. |
| `implicit operator View(BarcodeArView)` | Implicit conversion to `UIKit.UIView` for native interop. |

> The .NET `BarcodeArView` does **not** expose `OnResume()` / `OnPause()` on iOS — those are Android-only (the binding wraps them in `#if __ANDROID__`). The iOS lifecycle is `Start()` in `ViewWillAppear` and `Stop()` in `ViewWillDisappear`, mirroring the official `MatrixScanARSimpleSample`. There is also no `OnDestroy()` method — call `Dispose()` from your VC's `Dispose(bool)` override.

## Step 6 — Handle session updates

The session is updated on every processed frame. The recommended idiomatic C# pattern is the `SessionUpdated` event on `BarcodeAr`:

```csharp
using CoreFoundation;
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;

// In your setup helper, after creating barcodeAr:
this.barcodeAr.SessionUpdated += this.OnSessionUpdated;

private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
{
    // SessionUpdated runs on a background recognition queue — dispatch UI work.
    IReadOnlyList<TrackedBarcode> added = args.Session.AddedTrackedBarcodes;
    if (added.Count == 0) return;

    // Copy data off the recognition queue before dispatching.
    var addedData = added.Select(tb => tb.Barcode.Data).ToList();

    DispatchQueue.MainQueue.DispatchAsync(() =>
    {
        foreach (var data in addedData)
        {
            // handle each newly tracked barcode's data
        }
    });
}
```

If you prefer the listener interface, implement `IBarcodeArListener` directly on the view controller. **`IBarcodeArListener` has only one method** — there are no `OnObservationStarted` / `OnObservationStopped` callbacks (unlike Swift):

```csharp
public partial class ScanViewController : UIViewController, IBarcodeArListener
{
    public void OnSessionUpdated(BarcodeAr barcodeAr, BarcodeArSession session, IFrameData frameData)
    {
        var added = session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();

        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // update UI
        });
    }
}

// In your setup helper:
this.barcodeAr.AddListener(this);
```

> **Do not hold references to `BarcodeArSession` or its collections outside `OnSessionUpdated`.** The session is only safe to access within that callback — copy `AddedTrackedBarcodes` / `TrackedBarcodes` data first, then dispatch.

### BarcodeArSession members

| Member | Type | Description |
|--------|------|-------------|
| `AddedTrackedBarcodes` | `IReadOnlyList<TrackedBarcode>` | Barcodes that entered the view in this frame. |
| `RemovedTrackedBarcodes` | `IReadOnlyList<int>` | Tracking IDs of barcodes that left the view in this frame. |
| `TrackedBarcodes` | `IReadOnlyDictionary<int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `Reset()` | method | Reset all tracked state. Only call from inside a listener / event callback. |

### BarcodeArEventArgs

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeAr` | `BarcodeAr` | The capture mode that raised the event. |
| `Session` | `BarcodeArSession` | The active session. |
| `FrameData` | `IFrameData` | The frame that produced the event. |

### TrackedBarcode

`TrackedBarcode` lives in `Scandit.DataCapture.Barcode.Batch.Data`. Properties:

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` | The decoded barcode — access `.Data`, `.Symbology`, etc. |
| `Identifier` | `int` | Unique tracking ID for this barcode (stable across frames). |
| `Location` | `Quadrilateral` | Position in image-space coordinates. |

## Step 7 — Highlights

Highlights are visual overlays drawn over each tracked barcode. Implement `IBarcodeArHighlightProvider` and assign it to `barcodeArView.HighlightProvider`.

**The .NET provider is async.** It returns `Task<IBarcodeArHighlight?>` — there is **no** `completionHandler` / delegate parameter (those are the Swift pattern). Return `null` (or `Task.FromResult<IBarcodeArHighlight?>(null)`) to hide a barcode entirely.

Highlight constructors take only the `Barcode` — no `context` argument.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Data;

private sealed class HighlightProvider : IBarcodeArHighlightProvider
{
    public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode)
    {
        IBarcodeArHighlight highlight = new BarcodeArRectangleHighlight(barcode);
        return Task.FromResult<IBarcodeArHighlight?>(highlight);
    }
}

// Assign before calling Start():
this.barcodeArView.HighlightProvider = new HighlightProvider();
```

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
highlight.Brush = new Brush(/* ... */);        // optional
highlight.Icon = myScanditIcon;                // optional (used with the Icon preset)
```

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` (get) | |
| `Brush` | `Brush` (get/set) | |
| `Icon` | `ScanditIcon?` (get/set) | |
| `Size` | `float` (get/set) | Circle diameter in points (minimum 18). |

`BarcodeArCircleHighlightPreset` is an enum: `Dot` (default-styled solid dot) or `Icon` (icon-centered circle).

Returning `null` from `HighlightForBarcodeAsync` hides the highlight for that specific barcode (the barcode is still tracked, just not visually marked).

## Step 8 — Annotations

Annotations are floating tooltips, status icons, or panels displayed alongside a tracked barcode. Implement `IBarcodeArAnnotationProvider` and assign it to `barcodeArView.AnnotationProvider`. The provider is **async**, the same pattern as highlights.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;
using Scandit.DataCapture.Barcode.Data;

private sealed class AnnotationProvider : IBarcodeArAnnotationProvider
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

this.barcodeArView.AnnotationProvider = new AnnotationProvider();
```

### Built-in annotation types

All three types take only the `Barcode` in the constructor (no `context`).

| Type | Constructor | Description |
|------|-------------|-------------|
| `BarcodeArStatusIconAnnotation` | `(Barcode)` | Compact icon that expands to text on tap. |
| `BarcodeArInfoAnnotation` | `(Barcode)` | Structured tooltip with optional header, body rows, and footer. |
| `BarcodeArPopoverAnnotation` | `(Barcode, IList<BarcodeArPopoverAnnotationButton>)` | A row of icon+text action buttons. |

**`BarcodeArStatusIconAnnotation` properties:**

| Property | Type | Description |
|----------|------|-------------|
| `Icon` | `ScanditIcon` (get/set) | Collapsed-state icon. |
| `Text` | `string?` (get/set) | Expanded-state text (max ~20 chars). `null` = no expand. |
| `BackgroundColor` | `UIColor` (get/set) | Annotation background color. |
| `TextColor` | `UIColor` (get/set) | Expanded text color. |
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
| `BackgroundColor` | `UIColor` (get/set) | |
| `Listener` | `IBarcodeArInfoAnnotationListener?` (get/set) | Receives tap events for header / footer / icons / body. |
| `Barcode` | `Barcode` (get) | |

`BarcodeArInfoAnnotationBodyComponent` (in the `Info` sub-package) has its own properties: `Text`, `TextColor`, `TextSize`, `Typeface`, `StyledTextFormatted`, `LeftIcon`, `RightIcon`, `LeftIconTappable`, `RightIconTappable`, `TextAlignment`.

`BarcodeArInfoAnnotationHeader`: `Text`, `TextSize`, `Typeface`, `TextColor`, `Icon`, `BackgroundColor`.
`BarcodeArInfoAnnotationFooter`: `Text`, `TextSize`, `Typeface`, `TextColor`, `Icon`, `BackgroundColor`.

**`BarcodeArPopoverAnnotation` properties:**

| Property | Type | Description |
|----------|------|-------------|
| `Buttons` | `IReadOnlyCollection<BarcodeArPopoverAnnotationButton>` (get) | The buttons passed to the constructor. |
| `EntirePopoverTappable` | `bool` (get/set) | If `true`, taps anywhere on the popover fire `OnPopoverTapped`. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | |
| `Listener` | `IBarcodeArPopoverAnnotationListener?` (get/set) | Receives `OnPopoverButtonTapped(annotation, button, buttonIndex)` and `OnPopoverTapped(annotation)`. |
| `Barcode` | `Barcode` (get) | |

`BarcodeArPopoverAnnotationButton(ScanditIcon icon, string text)`: `Text` (get), `TextSize` (get/set), `Typeface` (get/set), `TextColor` (get/set), `Enabled` (get/set), `Icon` (get).

**`BarcodeArResponsiveAnnotation`** (available since `dotnet.ios=8.0`) — wraps two `BarcodeArInfoAnnotation` variations and switches between them based on how large the barcode appears on screen. It is also in the `Scandit.DataCapture.Barcode.Ar.UI.Annotations` namespace.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;

var closeUp = new BarcodeArInfoAnnotation(barcode)
{
    Body = new List<BarcodeArInfoAnnotationBodyComponent>
    {
        new BarcodeArInfoAnnotationBodyComponent { Text = barcode.Data ?? string.Empty },
    },
};
var farAway = new BarcodeArInfoAnnotation(barcode)
{
    Body = new List<BarcodeArInfoAnnotationBodyComponent>
    {
        new BarcodeArInfoAnnotationBodyComponent { Text = "Scan closer" },
    },
};

var annotation = new BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
// Threshold is a static property (applies to ALL instances) — barcode area / screen area, 0.0–1.0, default 0.05.
BarcodeArResponsiveAnnotation.Threshold = 0.1f;
```

The constructor is `BarcodeArResponsiveAnnotation(Barcode barcode, BarcodeArInfoAnnotation? closeUpAnnotation, BarcodeArInfoAnnotation? farAwayAnnotation)`. Either annotation may be `null` to show nothing for that variation.

| Member | Type | Description |
|--------|------|-------------|
| `Threshold` | `static float` (get/set) | Class-level switch point (barcode-area / screen-area, `0.0`–`1.0`, default `0.05`). Above it the close-up annotation shows; at or below it the far-away annotation shows. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | Default `HighlightTapAndBarcodeScan`. |
| `Barcode` | `Barcode` (get) | |

Returning `null` from `AnnotationForBarcodeAsync` simply omits the annotation for that barcode.

## Step 9 — Tap interactions on highlights

The .NET `BarcodeArView` exposes tap events as a C# event. There is **no `UiListener` / `UIDelegate` property** — use the event instead:

```csharp
this.barcodeArView.HighlightForBarcodeTapped += (sender, args) =>
{
    // args.BarcodeAr, args.Barcode, args.Highlight
    var data = args.Barcode.Data;
    DispatchQueue.MainQueue.DispatchAsync(() => /* open detail screen, etc. */);
};
```

`HighlightForBarcodeTappedEventArgs` exposes:

| Property | Type |
|----------|------|
| `BarcodeAr` | `BarcodeAr` |
| `Barcode` | `Barcode` |
| `Highlight` | `IBarcodeArHighlight` |

## Step 10 — Start scanning and lifecycle

After assigning providers and listeners, drive scanning from `ViewWillAppear` / `ViewWillDisappear`. **`BarcodeArView` on iOS does not expose `OnResume()` / `OnPause()`** — those are Android-only. Use `Start()` and `Stop()` (matching the official `MatrixScanARSimpleSample`).

```csharp
public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);
    // Start (or resume) the camera and scanning pipeline.
    // iOS prompts for the camera permission automatically here if it hasn't been granted yet
    // — provided NSCameraUsageDescription is set in Info.plist.
    this.barcodeArView.Start();
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);
    // Stop scanning and release the camera.
    this.barcodeArView.Stop();
}

protected override void Dispose(bool disposing)
{
    if (disposing)
    {
        this.barcodeAr.RemoveListener(this);                  // only if you used AddListener
        this.barcodeAr.SessionUpdated -= this.OnSessionUpdated; // only if you subscribed
        this.barcodeArView?.Dispose();
        this.barcodeAr?.Dispose();
    }
    base.Dispose(disposing);
}
```

`BarcodeArView` handles camera lifecycle internally once `Start()` is called — you don't need to call `Camera.GetDefaultCamera()` / `SwitchToDesiredStateAsync(...)` yourself. There is no `DataCaptureView` here either.

## Complete minimal example

This mirrors the structure of the official Scandit iOS `MatrixScanARSimpleSample`, adapted to the .NET binding.

```csharp
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

public partial class ScanViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeAr barcodeAr = null!;
    private BarcodeArView barcodeArView = null!;

    // Storyboard-loaded VCs: keep this constructor (the runtime calls it with a real handle).
    // Programmatically-instantiated VCs (no Main.storyboard): use the parameterless ctor below
    // and `new ScanViewController()`. DO NOT call `new ScanViewController(IntPtr.Zero)` —
    // that leaves the native peer uninitialized and ViewDidLoad may never fire.
    public ScanViewController(IntPtr handle) : base(handle) { }
    public ScanViewController() : base() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.SetupRecognition();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeArView.Start();
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeArView.Stop();
    }

    private void SetupRecognition()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Configure BarcodeAr.
        BarcodeArSettings settings = new BarcodeArSettings();
        HashSet<Symbology> symbologies = new()
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
            Symbology.Qr,
        };
        settings.EnableSymbologies(symbologies);

        this.barcodeAr = new BarcodeAr(this.dataCaptureContext, settings);
        this.barcodeAr.SessionUpdated += this.OnSessionUpdated;

        // Create the AR view. parentView = this.View — the factory attaches it for you.
        BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();
        this.barcodeArView = BarcodeArView.Create(
            parentView: this.View!,
            barcodeAr: this.barcodeAr,
            dataCaptureContext: this.dataCaptureContext,
            settings: viewSettings,
            cameraSettings: null);

        this.barcodeArView.HighlightProvider = new RectangleHighlightProvider();
        this.barcodeArView.HighlightForBarcodeTapped += (s, e) =>
            DispatchQueue.MainQueue.DispatchAsync(() => /* react to tap */ _ = e.Barcode.Data);
    }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        var addedData = args.Session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();
        if (addedData.Count == 0) return;

        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            foreach (var data in addedData)
            {
                _ = data; // handle the newly tracked barcode
            }
        });
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            this.barcodeAr.SessionUpdated -= this.OnSessionUpdated;
            this.barcodeArView?.Dispose();
            this.barcodeAr?.Dispose();
        }
        base.Dispose(disposing);
    }

    private sealed class RectangleHighlightProvider : IBarcodeArHighlightProvider
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
this.barcodeAr.Feedback = new BarcodeArFeedback();

// Restore defaults:
this.barcodeAr.Feedback = BarcodeArFeedback.DefaultFeedback;
```

`BarcodeArFeedback` exposes two `Core.Common.Feedback.Feedback` slots:

| Property | Type | Description |
|----------|------|-------------|
| `Scanned` | `Feedback` | Played when a barcode enters tracking. |
| `Tapped` | `Feedback` | Played when a highlight is tapped. |

To customize one of them:
```csharp
using Scandit.DataCapture.Core.Common.Feedback;

this.barcodeAr.Feedback = new BarcodeArFeedback
{
    Scanned = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
    Tapped  = new Feedback(null, null),  // silent on tap
};
```

> `BarcodeArFeedback.DefaultFeedback` is a **static property** in .NET — not the Swift `BarcodeArFeedback.default()` method. Calling it as a method (`BarcodeArFeedback.DefaultFeedback()`) is a compile error.

### Show built-in controls (torch, zoom, camera switch, macro mode)

```csharp
using Scandit.DataCapture.Core.Common.Geometry;

this.barcodeArView.ShouldShowTorchControl = true;
this.barcodeArView.TorchControlPosition = Anchor.BottomLeft;

this.barcodeArView.ShouldShowZoomControl = true;
this.barcodeArView.ZoomControlPosition = Anchor.BottomRight;

this.barcodeArView.ShouldShowCameraSwitchControl = true;
this.barcodeArView.CameraSwitchControlPosition = Anchor.TopRight;

// iOS-only: macro mode toggle (close-focus). Not available on .NET Android.
this.barcodeArView.ShouldShowMacroModeControl = true;
this.barcodeArView.MacroModeControlPosition = Anchor.TopRight;
```

`ShouldShowTorchControl`, `ShouldShowCameraSwitchControl`, and `ShouldShowMacroModeControl` all default to `false`. `ShouldShowMacroModeControl` and `MacroModeControlPosition` are **iOS-only** — they do not exist on the .NET Android `BarcodeArView`.

### Switch to circle highlights

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;

private sealed class DotProvider : IBarcodeArHighlightProvider
{
    public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
        Task.FromResult<IBarcodeArHighlight?>(
            new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot));
}
```

### Reset overlays

When the displayed information needs to be re-computed (e.g. the user switched filters in the app), call:

```csharp
this.barcodeArView.Reset();
```

This clears all current highlights and annotations and re-invokes both providers for every currently tracked barcode.

### Apply settings at runtime

```csharp
BarcodeArSettings updated = new BarcodeArSettings();
updated.EnableSymbology(Symbology.Qr, true);
await this.barcodeAr.ApplySettingsAsync(updated);
```

### Async work in the session handler

When responding to a scanned barcode requires a network or database call, do not block the recognition queue:

```csharp
private async void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
{
    var added = args.Session.AddedTrackedBarcodes.ToList();  // copy off the recognition queue

    foreach (TrackedBarcode tracked in added)
    {
        try
        {
            var info = await LookupAsync(tracked.Barcode.Data!);
            DispatchQueue.MainQueue.DispatchAsync(() => this.UpdateUi(tracked.Identifier, info));
        }
        catch (Exception ex)
        {
            // Log; BarcodeAr keeps tracking regardless.
        }
    }
}
```

> `async void` is acceptable here because the event handler signature is `void`. Provider methods (`HighlightForBarcodeAsync`, `AnnotationForBarcodeAsync`) return `Task<…>` and should themselves be `async Task<…>` (or return `Task.FromResult(...)`) — not `async void`.

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it for the lifetime of the view controller.
2. **`BarcodeAr` uses `new`, `BarcodeArView` uses `Create`** — `new BarcodeAr(context, settings)`, `new BarcodeArSettings()`, but `BarcodeArView.Create(parent, barcodeAr, context, settings, cameraSettings)`. Don't write `BarcodeAr.Create(...)` — it doesn't exist.
3. **`BarcodeArView.Create` auto-attaches to `parentView`** — pass any `UIView` (typically `this.View`). Do not call `AddSubview` on the `BarcodeArView` yourself.
4. **iOS lifecycle is `Start()` / `Stop()`** — call `barcodeArView.Start()` from `ViewWillAppear` and `barcodeArView.Stop()` from `ViewWillDisappear`. **`OnResume()` / `OnPause()` are Android-only** and don't exist on the iOS binding (using them is a compile error). `OnDestroy()` also does not exist — call `Dispose()` from `Dispose(bool)`.
5. **Event API is idiomatic** — prefer `barcodeAr.SessionUpdated += handler` over `AddListener`. Both work; the event is more idiomatic in C#.
6. **`IBarcodeArListener` has one callback** — `OnSessionUpdated(BarcodeAr, BarcodeArSession, IFrameData)`. There are no `OnObservationStarted` / `OnObservationStopped` callbacks.
7. **Background queue for session updates** — `OnSessionUpdated` / `SessionUpdated` runs on a recognition queue. Use `DispatchQueue.MainQueue.DispatchAsync(() => …)` for UI updates (matches the official Scandit .NET iOS samples).
8. **Providers are async** — `IBarcodeArHighlightProvider.HighlightForBarcodeAsync(barcode)` and `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync(barcode)` both return `Task<…?>`. No delegate / `completionHandler`; return `null` (or `Task.FromResult<…?>(null)`) to suppress the overlay for a given barcode.
9. **Highlight/annotation constructors take only `Barcode`** — no `context` argument: `new BarcodeArRectangleHighlight(barcode)`, `new BarcodeArInfoAnnotation(barcode)`, `new BarcodeArStatusIconAnnotation(barcode)`, `new BarcodeArPopoverAnnotation(barcode, buttons)`.
10. **Tap events via `HighlightForBarcodeTapped`** — there is no `UiListener` / `UIDelegate` property; subscribe to the event on `BarcodeArView`.
11. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Qr`, `Symbology.Code128`, not the Swift camelCase style (`.ean13UPCA`).
12. **SDK 8.0+ requires `AppDelegate` initialization** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` at the top of `FinishedLaunching` before any Scandit type is used.
13. **No runtime permission call** — iOS handles the camera prompt automatically once `NSCameraUsageDescription` is in `Info.plist`. There is no Android-style `RequestPermissions`.
14. **iOS-only `ShouldShowMacroModeControl`** — the macro-mode toggle exists only on the iOS binding; do not introduce it for Android cross-platform code paths.
15. **Don't retain the session** — `BarcodeArSession` and its collections are only safe within `OnSessionUpdated`. Copy data before dispatching.
