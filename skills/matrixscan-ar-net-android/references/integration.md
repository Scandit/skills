# MatrixScan AR (.NET for Android) Integration Guide

`BarcodeAr` is the multi-barcode AR scanning mode. It simultaneously tracks all barcodes in the camera feed and overlays interactive highlights and annotations on each one in real time. Unlike `BarcodeCapture`, `BarcodeAr` does **not** require a separate `Camera`, `DataCaptureView`, or `BarcodeCaptureOverlay` — the `BarcodeArView` manages its own camera and rendering. AR overlays are driven by **provider interfaces**: `IBarcodeArHighlightProvider` supplies a highlight per barcode, and `IBarcodeArAnnotationProvider` supplies an optional annotation. In the .NET binding both providers are **async / Task-based**.

Examples below use C# 12 and an `AppCompatActivity`. The same APIs work identically in a Fragment — adapt ownership of `DataCaptureContext`, `BarcodeAr`, and `BarcodeArView` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration uses a XAML-hosted `BarcodeArView` and a builder-based DI registration which are different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number like `8.13.0` when only `8.4.0` is the latest stable — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Core with version (>= 8.13.0)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last entry without a pre-release suffix) before proceeding.

`BarcodeAr` was introduced in **dotnet.android 7.2**. If the latest stable is older than 7.2 (extremely unlikely today), stop and tell the user — the integration cannot proceed.

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
- **`Theme.AppCompat` descendant required on the activity.** Because the activity inherits from `AppCompatActivity`, its theme must be a `Theme.AppCompat` descendant or `SetContentView` crashes at launch with `IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity`. The `dotnet new android` template's default theme is **not** AppCompat-based, so set one explicitly on the `[Activity]` attribute (`NoActionBar` because `BarcodeArView` covers the screen with its own controls):
  ```csharp
  [Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
  ```
- **`SupportedOSPlatformVersion` must be at least `24`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>
  ```
  Lower values fail the build because Scandit's Android AAR has `minSdkVersion=24`.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. Without this, the first `new BarcodeAr(...)` / `BarcodeArView.Create(...)` call crashes because the container has no registrations.

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

**Recommended:** scaffold a buildable shell with the official template, then add `BarcodeAr` on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

Add the Scandit and `Xamarin.AndroidX.AppCompat` packages from the bullets above, bump `<SupportedOSPlatformVersion>` to `24.0`, and continue with Step 1.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves tracking performance and accuracy.

Once the user responds, ask which Activity (or Fragment) they'd like to integrate `BarcodeAr` into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />` to the `.csproj` (use the version pinned in **Step 0** above — do not guess).
2. Ensure `<SupportedOSPlatformVersion>24.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
4. Request the `CAMERA` permission at runtime before scanning starts (the `CameraPermissionActivity` helper below).
5. Create `MainApplication.cs` with `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` (SDK 8.0+).
6. Set `Theme = "@style/Theme.AppCompat.Light.NoActionBar"` on the `[Activity]` attribute (required by `AppCompatActivity`).
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

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

`BarcodeAr` uses a direct constructor that takes the context — unlike `SparkScan` which is context-less until the view is created.

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;

this.barcodeAr = new BarcodeAr(this.dataCaptureContext, settings);
```

There is no `BarcodeAr.Create(...)` factory and no `BarcodeAr.ForDataCaptureContext(...)` static.

### BarcodeAr members

| Member | Description |
|--------|-------------|
| `new BarcodeAr(DataCaptureContext? context, BarcodeArSettings settings)` | Constructor — creates the mode and attaches it to the context. |
| `Feedback` | `BarcodeArFeedback` (get/set) — sound / vibration for scan and tap events. See Step 7. |
| `ApplySettingsAsync(BarcodeArSettings)` | `Task` — applies new settings on the next processed frame. |
| `AddListener(IBarcodeArListener)` / `RemoveListener(IBarcodeArListener)` | Register or remove a listener. |
| `event EventHandler<BarcodeArEventArgs> SessionUpdated` | Raised on every processed frame. **Recommended** in idiomatic C#. |
| `static CameraSettings RecommendedCameraSettings` | Get the recommended camera settings (used implicitly when `BarcodeArView.Create` is passed `null` for `cameraSettings`). |
| `Dispose()` | Releases native resources. |

> **Use either `AddListener` or the event — not both for the same handler.** They both fire `OnSessionUpdated`/`SessionUpdated`; subscribing to both leads to double-processing.

## Step 4 — Configure BarcodeArViewSettings (optional)

`BarcodeArViewSettings` is intentionally minimal. It only exposes three properties; if all you want is the defaults, you can pass `new BarcodeArViewSettings()` straight to `BarcodeArView.Create(...)`.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Core.Source;

BarcodeArViewSettings viewSettings = new BarcodeArViewSettings
{
    SoundEnabled = true,                        // beep on each tracked barcode (default true)
    HapticEnabled = true,                       // vibrate on each tracked barcode (default true)
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

`BarcodeArView` is the AR rendering surface. The `Create` factory attaches the view to the `parentView` you pass — a `ViewGroup` such as a `FrameLayout`, `ConstraintLayout`, or any layout you already have. There is no special "coordinator" container required.

The factory takes a nullable `cameraSettings` — pass `null` to use `BarcodeAr.RecommendedCameraSettings` automatically.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI;
using Android.Widget;

// Either: use a full-screen FrameLayout as the host
var container = new FrameLayout(this);
this.SetContentView(container);

// Or: use an existing layout from XML
// SetContentView(Resource.Layout.activity_main);
// var container = this.FindViewById<FrameLayout>(Resource.Id.barcode_ar_container)!;

BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();
this.barcodeArView = BarcodeArView.Create(
    parentView: container,
    barcodeAr: this.barcodeAr,
    dataCaptureContext: this.dataCaptureContext,
    settings: viewSettings,
    cameraSettings: null);
```

You do **not** call `container.AddView(barcodeArView)` — the `Create` factory wires it in. If you need the underlying `Android.Views.View` (e.g. to query it from a test), `BarcodeArView` declares an `implicit operator View(BarcodeArView)` for that purpose; do not depend on it for normal use.

### BarcodeArView members

| Member | Description |
|--------|-------------|
| `static BarcodeArView Create(View parentView, BarcodeAr barcodeAr, DataCaptureContext dataCaptureContext, BarcodeArViewSettings settings, CameraSettings? cameraSettings)` | Static factory — creates the view and attaches it to `parentView`. Pass `null` for `cameraSettings` to use `BarcodeAr.RecommendedCameraSettings`. |
| `HighlightProvider` | `IBarcodeArHighlightProvider?` — supplies a highlight per tracked barcode. If `null`, a default rectangle highlight is shown. |
| `AnnotationProvider` | `IBarcodeArAnnotationProvider?` — supplies an annotation per tracked barcode. If `null`, no annotation is shown. |
| `ShouldShowTorchControl` | `bool` (default `false`) — whether to render the built-in torch toggle button. |
| `ShouldShowZoomControl` | `bool` — whether to render the built-in zoom switch button. |
| `ShouldShowCameraSwitchControl` | `bool` (default `false`) — whether to render the camera-switch button (between world-facing and user-facing cameras). |
| `TorchControlPosition` | `Anchor` (default `TopLeft`) — where the torch button sits. |
| `ZoomControlPosition` | `Anchor` (default `BottomRight`). |
| `CameraSwitchControlPosition` | `Anchor` (default `TopRight`). |
| `Start()` | Begin scanning. Call after providers are assigned. On Android the actual scan loop only runs once the view is in the `Resumed` lifecycle state — invoke `OnResume()` from your activity's `OnResume`. |
| `Stop()` | Stop scanning and clear all overlays. |
| `Pause()` | Pause scanning (keeps overlays and camera attached). |
| `Reset()` | Clear all current highlights/annotations and re-query the providers for each tracked barcode. |
| `OnResume()` (Android-only) | Forward from `Activity.OnResume` — **required** for correct camera lifecycle. |
| `OnPause()` (Android-only) | Forward from `Activity.OnPause` — **required**. |
| `GetNotificationPresenter()` | Returns an `INotificationPresenter` that can render notifications inside the AR view (8.5+). |
| `event EventHandler<HighlightForBarcodeTappedEventArgs> HighlightForBarcodeTapped` | Fires when the user taps a highlight. See Step 9. |
| `Dispose()` | Releases native resources and clears the cache. Call from the activity's `OnDestroy()` (or via `using` semantics). |
| `implicit operator View(BarcodeArView)` | Implicit conversion to `Android.Views.View` for native interop. |

> The .NET `BarcodeArView` does **not** expose an `OnDestroy()` method or a `UiListener` property. Use `Dispose()` for teardown and the `HighlightForBarcodeTapped` event for tap interactions.

## Step 6 — Handle session updates

The session is updated on every processed frame. The recommended idiomatic C# pattern is the `SessionUpdated` event on `BarcodeAr`:

```csharp
using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;

// In OnCreate / setup, after creating barcodeAr:
this.barcodeAr.SessionUpdated += this.OnSessionUpdated;

private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
{
    // SessionUpdated runs on a background recognition thread — dispatch UI work.
    IReadOnlyList<TrackedBarcode> added = args.Session.AddedTrackedBarcodes;
    if (added.Count == 0) return;

    this.RunOnUiThread(() =>
    {
        foreach (TrackedBarcode tracked in added)
        {
            // tracked.Barcode.Data, tracked.Barcode.Symbology, tracked.Identifier
        }
    });
}
```

If you prefer the listener interface, implement `IBarcodeArListener` directly on the activity. **`IBarcodeArListener` has only one method** — there are no `OnObservationStarted` / `OnObservationStopped` callbacks (unlike Kotlin):

```csharp
public class MainActivity : CameraPermissionActivity, IBarcodeArListener
{
    public void OnSessionUpdated(BarcodeAr barcodeAr, BarcodeArSession session, IFrameData frameData)
    {
        IReadOnlyList<TrackedBarcode> added = session.AddedTrackedBarcodes;
        this.RunOnUiThread(() => /* update UI */);
    }
}

// In OnCreate:
this.barcodeAr.AddListener(this);
```

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

**The .NET provider is async.** It returns `Task<IBarcodeArHighlight?>` — there is **no** `Callback` parameter and **no** `callback.OnData(...)` method (those are the Kotlin pattern). Return `null` (or `Task.FromResult<IBarcodeArHighlight?>(null)`) to hide a barcode entirely.

Highlight constructors take only the `Barcode` — no `Context` argument.

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
highlight.Brush = new Brush(...);              // optional
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

All three types take only the `Barcode` in the constructor (no `Context`).

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

**`BarcodeArResponsiveAnnotation`** — switches between two `BarcodeArInfoAnnotation` variations based on the barcode's on-screen size. Constructor takes only `Barcode` plus the close-up and far-away annotations (each may be `null`):

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;

var closeUp = new BarcodeArInfoAnnotation(barcode);
var farAway = new BarcodeArInfoAnnotation(barcode);
var annotation = new BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
```

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeArResponsiveAnnotation(Barcode, BarcodeArInfoAnnotation?, BarcodeArInfoAnnotation?)` | constructor | `(barcode, closeUpAnnotation, farAwayAnnotation)`. Either annotation may be `null`. |
| `Threshold` | `static float` (get/set) | Barcode-area / screen-area ratio at which the close-up variation is shown (0.0–1.0, default `0.05`). It is a **static** class-level property — set `BarcodeArResponsiveAnnotation.Threshold`, not a per-instance value. |
| `CloseUpAnnotation` | `BarcodeArInfoAnnotation?` (get) | Shown when the barcode area exceeds `Threshold`. |
| `FarAwayAnnotation` | `BarcodeArInfoAnnotation?` (get) | Shown otherwise. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | Defaults to `HighlightTapAndBarcodeScan`. |
| `Barcode` | `Barcode` (get) | |

### Building a `ScanditIcon`

`BarcodeArStatusIconAnnotation.Icon` and `BarcodeArPopoverAnnotationButton` require a `ScanditIcon` (namespace `Scandit.DataCapture.Core.UI.Icon`). Build one with `ScanditIconBuilder` (a fluent builder; each `With...` returns the builder, `Build()` returns the icon):

```csharp
using Scandit.DataCapture.Core.UI.Icon;

var icon = new ScanditIconBuilder()
    .WithIcon(ScanditIconType.ExclamationMark)
    .WithBackgroundShape(ScanditIconShape.Circle)
    .Build();
```

Builder methods: `WithIcon(ScanditIconType?)`, `WithIconColor(Color)`, `WithBackgroundColor(Color)`, `WithBackgroundStrokeColor(Color)`, `WithBackgroundStrokeWidth(float)`, `WithBackgroundShape(ScanditIconShape?)`, then `Build()`. The color arguments take `Scandit.DataCapture.Core.Common.Color`. `ScanditIconType` values include `ExclamationMark`, `Checkmark`, `XMark`, `QuestionMark`, `LowStock`; `ScanditIconShape` is `Circle` or `Square`.

### Annotation trigger

`BarcodeArAnnotationTrigger` controls when an annotation appears. Values: `HighlightTapAndBarcodeScan` (default — shown on scan, toggleable by highlight tap), `HighlightTap` (only on highlight tap), and `BarcodeScan` (shown on scan, not toggleable).

### Tap interactions on annotations

Highlight taps use the `BarcodeArView.HighlightForBarcodeTapped` event (Step 9). Annotation taps are delivered through a per-annotation listener instead:

- `BarcodeArInfoAnnotation.Listener` (`IBarcodeArInfoAnnotationListener`) — `OnInfoAnnotationTapped(annotation)`, `OnInfoAnnotationHeaderTapped(annotation)`, `OnInfoAnnotationFooterTapped(annotation)`, `OnInfoAnnotationLeftIconTapped(annotation, component, componentIndex)`, `OnInfoAnnotationRightIconTapped(annotation, component, componentIndex)`. Whole-annotation taps only fire when `EntireAnnotationTappable` is `true`.
- `BarcodeArPopoverAnnotation.Listener` (`IBarcodeArPopoverAnnotationListener`) — `OnPopoverButtonTapped(popover, button, buttonIndex)` (fires when `EntirePopoverTappable` is `false`) and `OnPopoverTapped(popover)` (fires when `EntirePopoverTappable` is `true`).

Returning `null` from `AnnotationForBarcodeAsync` simply omits the annotation for that barcode.

## Step 9 — Tap interactions on highlights

The .NET `BarcodeArView` exposes tap events as a C# event. There is **no `UiListener` property** — use the event instead:

```csharp
this.barcodeArView.HighlightForBarcodeTapped += (sender, args) =>
{
    // args.BarcodeAr, args.Barcode, args.Highlight
    var data = args.Barcode.Data;
    this.RunOnUiThread(() => /* open detail screen, etc. */);
};
```

`HighlightForBarcodeTappedEventArgs` exposes:

| Property | Type |
|----------|------|
| `BarcodeAr` | `BarcodeAr` |
| `Barcode` | `Barcode` |
| `Highlight` | `IBarcodeArHighlight` |

## Step 10 — Start scanning and lifecycle

After assigning providers and listeners, call `Start()` to begin tracking. Then forward the activity's `OnPause` / `OnResume` calls into the `BarcodeArView`. **Both calls are required** — without them, the camera and preview won't behave correctly across backgrounding. There is no `OnDestroy()` method on the .NET `BarcodeArView`; call `Dispose()` from the activity's `OnDestroy` instead.

```csharp
// Call once after providers are assigned, e.g. at the end of OnCreate or after permission is granted:
this.barcodeArView.Start();

protected override void OnResume()
{
    base.OnResume();
    this.barcodeArView.OnResume();
    this.RequestCameraPermission();   // see CameraPermissionActivity below
}

protected override void OnPause()
{
    base.OnPause();
    this.barcodeArView.OnPause();
}

protected override void OnDestroy()
{
    base.OnDestroy();
    this.barcodeAr.RemoveListener(this);   // only if you used AddListener
    this.barcodeAr.SessionUpdated -= this.OnSessionUpdated;
    this.barcodeArView.Dispose();
    this.barcodeAr.Dispose();
}

protected override void OnCameraPermissionGranted()
{
    // BarcodeArView starts the camera on its own once the view is resumed.
}
```

`BarcodeArView` handles camera lifecycle internally — you don't need to call `Camera.GetDefaultCamera()` / `SwitchToDesiredStateAsync(...)` yourself.

## Camera permission helper

The same permission helper as the official Scandit .NET Android samples — copy verbatim:

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
using Android.OS;
using Android.Widget;

using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeAr barcodeAr = null!;
    private BarcodeArView barcodeArView = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

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

        // Host the BarcodeArView in a full-screen FrameLayout.
        var container = new FrameLayout(this);
        this.SetContentView(container);

        BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();
        this.barcodeArView = BarcodeArView.Create(
            parentView: container,
            barcodeAr: this.barcodeAr,
            dataCaptureContext: this.dataCaptureContext,
            settings: viewSettings,
            cameraSettings: null);

        this.barcodeArView.HighlightProvider = new RectangleHighlightProvider();
        this.barcodeArView.HighlightForBarcodeTapped += (s, e) =>
            this.RunOnUiThread(() => /* react to tap */ _ = e.Barcode.Data);

        this.barcodeArView.Start();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeArView.OnResume();
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeArView.OnPause();
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.barcodeAr.SessionUpdated -= this.OnSessionUpdated;
        this.barcodeArView.Dispose();
        this.barcodeAr.Dispose();
    }

    protected override void OnCameraPermissionGranted() { }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        IReadOnlyList<TrackedBarcode> added = args.Session.AddedTrackedBarcodes;
        if (added.Count == 0) return;
        this.RunOnUiThread(() =>
        {
            foreach (TrackedBarcode tracked in added)
            {
                _ = tracked.Barcode.Data;
            }
        });
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

> `BarcodeArFeedback.DefaultFeedback` is a **static property** in .NET — not the Kotlin `defaultFeedback()` method. Calling it as a method (`BarcodeArFeedback.DefaultFeedback()`) is a compile error.

### Show built-in controls (torch, zoom, camera switch)

```csharp
using Scandit.DataCapture.Core.Common.Geometry;

this.barcodeArView.ShouldShowTorchControl = true;
this.barcodeArView.TorchControlPosition = Anchor.BottomLeft;

this.barcodeArView.ShouldShowZoomControl = true;
this.barcodeArView.ZoomControlPosition = Anchor.BottomRight;

this.barcodeArView.ShouldShowCameraSwitchControl = true;
this.barcodeArView.CameraSwitchControlPosition = Anchor.TopRight;
```

`ShouldShowTorchControl` and `ShouldShowCameraSwitchControl` default to `false`.

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

When responding to a scanned barcode requires a network or database call, do not block the recognition thread:

```csharp
private async void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
{
    foreach (TrackedBarcode tracked in args.Session.AddedTrackedBarcodes)
    {
        try
        {
            var info = await LookupAsync(tracked.Barcode.Data!);
            this.RunOnUiThread(() => this.UpdateUi(tracked.Identifier, info));
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

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it for the lifetime of the activity.
2. **`BarcodeAr` uses `new`, `BarcodeArView` uses `Create`** — `new BarcodeAr(context, settings)`, `new BarcodeArSettings()`, but `BarcodeArView.Create(parent, barcodeAr, context, settings, cameraSettings)`. Don't write `BarcodeAr.Create(...)` — it doesn't exist.
3. **`BarcodeArView.Create` auto-attaches to `parentView`** — pass any `ViewGroup` (`FrameLayout`, etc.). There is no `BarcodeArCoordinatorLayout`; do not invent one.
4. **Forward `OnPause` / `OnResume` into `barcodeArView`** — `barcodeArView.OnPause()` / `OnResume()` are mandatory for correct camera lifecycle. `OnDestroy()` does **not** exist on `BarcodeArView`; call `Dispose()` instead.
5. **Call `Start()`** — after providers are assigned, call `barcodeArView.Start()` to begin tracking. Scanning only actually runs once the view is in the `Resumed` lifecycle state.
6. **Event API is idiomatic** — prefer `barcodeAr.SessionUpdated += handler` over `AddListener`. Both work; the event is more idiomatic in C#.
7. **`IBarcodeArListener` has one callback** — `OnSessionUpdated(BarcodeAr, BarcodeArSession, IFrameData)`. There are no `OnObservationStarted` / `OnObservationStopped` callbacks.
8. **Providers are async** — `IBarcodeArHighlightProvider.HighlightForBarcodeAsync(barcode)` and `IBarcodeArAnnotationProvider.AnnotationForBarcodeAsync(barcode)` both return `Task<…?>`. No callback object; return `null` (or `Task.FromResult<…?>(null)`) to suppress the overlay for a given barcode.
9. **Highlight/annotation constructors take only `Barcode`** — no `Context` argument: `new BarcodeArRectangleHighlight(barcode)`, `new BarcodeArInfoAnnotation(barcode)`, `new BarcodeArStatusIconAnnotation(barcode)`, `new BarcodeArPopoverAnnotation(barcode, buttons)`.
10. **Background thread for session updates** — `OnSessionUpdated` / `SessionUpdated` runs on a recognition thread. `RunOnUiThread(() => …)` is required for UI updates.
11. **Tap events via `HighlightForBarcodeTapped`** — there is no `UiListener` property; subscribe to the event on `BarcodeArView`.
12. **Symbologies are PascalCase** — `Symbology.Ean13Upca`, `Symbology.Qr`, `Symbology.Code128`, not the Kotlin underscore style.
13. **SDK 8.0+ requires `MainApplication`** — `ScanditCaptureCore.Initialize()` + `ScanditBarcodeCapture.Initialize()` in `OnCreate()` before any Scandit type is used.
14. **No `<activity>` in the manifest** — `[Activity(MainLauncher = true, ...)]` is the canonical registration.
15. **Set a `Theme.AppCompat` descendant on the activity** — `[Activity(..., Theme = "@style/Theme.AppCompat.Light.NoActionBar")]`. Required because the activity inherits from `AppCompatActivity`; without it `SetContentView` throws `IllegalStateException` at launch.
