# Label Capture (Smart Label Capture) — .NET for Android Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

The .NET binding differs from the native Android (Kotlin) SDK in one big way: **there is no fluent `LabelCaptureSettings.builder()` chain.** You build each field with its own `.Builder()...Build("name")` factory, collect the fields into a list, wrap them in a `LabelDefinition`, and pass the definition(s) to `LabelCaptureSettings.Create(...)`.

Examples below use C# and an `AppCompatActivity`. The same APIs work in a Fragment — adapt ownership of `DataCaptureContext`, `Camera`, `LabelCapture`, `DataCaptureView`, and the overlay to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts the `DataCaptureView` as a XAML element and wires it through handlers, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Label/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all three packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Label with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.label/index.json` (last entry without a pre-release suffix) before proceeding.

Label Capture has been available on `dotnet.android` since **8.1**, so any current stable release supports it. If the project already pins an older Scandit major (6.x / 7.x), Label Capture is not available there — tell the user they must move to 8.1+ to use it.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add **three** packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Label" Version="<step-0-version>" />
  </ItemGroup>
  ```
  `Scandit.DataCapture.Label` always requires `Core` and `Barcode` (the `Symbology` enum and the barcode field types live in `Barcode`). **There is no separate `label-text-models` package** — the text recognizers (expiry date, prices, weight, custom text) are bundled in `Scandit.DataCapture.Label`. Do **not** add any `*.Maui` package — those are MAUI-only.
- `Xamarin.AndroidX.AppCompat` — required because the `CameraPermissionActivity` helper inherits from `AppCompatActivity`. The `dotnet new android` template pulls it in transitively; for manually scaffolded projects add it explicitly. When pinning the version, pick the highest available **including any Xamarin-revision suffix** — e.g. `1.7.0.5`, not bare `1.7.0`. The `.X` suffix marks Xamarin-binding patch revisions and carries critical transitive-dep updates.
- **`Theme.AppCompat` descendant required on the activity.** Because the activity inherits from `AppCompatActivity`, its theme must be a `Theme.AppCompat` descendant or `SetContentView` crashes at launch with `IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity`. Set `android:theme="@style/AppTheme"` (an AppCompat descendant) on `<application>` in the manifest, or on the `[Activity]` attribute:
  ```csharp
  [Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
  ```
- **`SupportedOSPlatformVersion` must be at least `24`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>
  ```
  Lower values fail the build because Scandit's Android AAR has `minSdkVersion=24`.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. **Three** initializers are required — missing `ScanditLabelCapture.Initialize()` crashes the first `LabelCapture.Create(...)` call.

  ```csharp
  using Android.Runtime;
  using Scandit.DataCapture.Barcode;
  using Scandit.DataCapture.Core;
  using Scandit.DataCapture.Label;

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
          ScanditLabelCapture.Initialize();
      }
  }
  ```

  If the project already has an `Application` subclass, add the three `Initialize()` calls to its existing `OnCreate()` rather than creating a second one (Android refuses to load two `[Application]`-decorated classes).
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- `AndroidManifest.xml` setup — two concerns:
  1. **Camera entry** (top-level, sibling to `<application>`):
     ```xml
     <uses-permission android:name="android.permission.CAMERA" />
     ```
  2. **Do not add `<activity>` declarations** for `MainActivity` (or any other `[Activity]`-decorated class). The attribute is the canonical registration in .NET for Android; a manual `<activity android:name=".MainActivity">` resolves against `<ApplicationId>` and won't match the generated class, producing `ClassNotFoundException` at launch.

  Request the camera permission at runtime before scanning starts (Android API 23+). The `CameraPermissionActivity` helper at the bottom of this guide encapsulates that flow.

### Project scaffolding (new projects only)

If a .NET Android project already exists, skip this and go to the Interactive Label Definition below.

**Recommended:** scaffold a buildable shell with the official template, then add Label Capture on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

Add the three Scandit packages and `Xamarin.AndroidX.AppCompat` from the bullets above, set `<SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>`, and continue.

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

**Question A — What's on your label?** Present this checklist of supported field types and ask the user to pick everything that applies.

*Barcode fields:*
- `CustomBarcode` — any barcode, user chooses symbologies
- `SerialNumberBarcode` — serial number (preset symbologies + regex)
- `PartNumberBarcode` — part number (preset symbologies + regex)
- `ImeiOneBarcode` / `ImeiTwoBarcode` — mobile device IMEI codes

*Text fields (preset recognizers):*
- `ExpiryDateText` — expiry date (optional date format)
- `PackingDateText` / `DateText` — packing date / generic date
- `TotalPriceText` — total price
- `UnitPriceText` — unit price
- `WeightText` — weight

*Text fields (custom):*
- `CustomText` — any text, user provides a value regex

**Question B — For each selected field:**
- Is it **required** or **optional**? (required = label is not considered complete until this field matches; optional = captured when/if it matches). Optional fields call `.IsOptional(true)`; required fields omit it (required is the default).
- For `CustomBarcode`: which **symbologies**? Mention that enabling only the symbologies they actually need improves scanning performance and accuracy. .NET symbology names are PascalCase: `Symbology.Ean13Upca`, `Symbology.Code128`, `Symbology.Gs1DatabarExpanded`, `Symbology.Qr`, `Symbology.DataMatrix`, etc.
- For `CustomText`: what **value regex** should the text match?
- For `ExpiryDateText` / `PackingDateText` / `DateText`: does the user need a specific date format? If so, ask for the component order (MDY, DMY, YMD, …) and whether partial dates are accepted.

**Question C — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

Each field also has a unique **name** string you pass to `.Build("name")`. You use that same name later to read the value out of the captured label, so keep the names in constants.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

this.dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Build the label definition and settings

Build each field with its own `.Builder()...Build("name")` factory, collect them into a `List<LabelFieldDefinition>`, wrap them in a `LabelDefinition`, and create the settings. **This is the part most often gotten wrong** — there is no `LabelCaptureSettings.builder()`/`addLabel()` chain.

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;

const string FieldBarcode = "Barcode";
const string FieldExpiryDate = "Expiry Date";
const string FieldTotalPrice = "Total Price";
const string LabelName = "Retail Item";

var fields = new List<LabelFieldDefinition>();

// A custom barcode field (required by default). SetSymbologies takes an IList<Symbology>.
LabelFieldDefinition barcode = CustomBarcode.Builder()
    .SetSymbologies(new List<Symbology>
    {
        Symbology.Ean13Upca,
        Symbology.Gs1DatabarExpanded,
        Symbology.Code128,
    })
    .Build(FieldBarcode);
fields.Add(barcode);

// An expiry date field with an explicit date format.
LabelFieldDefinition expiryDate = ExpiryDateText.Builder()
    .SetLabelDateFormat(new LabelDateFormat(LabelDateComponentFormat.MDY, acceptPartialDates: false))
    .Build(FieldExpiryDate);
fields.Add(expiryDate);

// An optional total-price field.
LabelFieldDefinition totalPrice = TotalPriceText.Builder()
    .IsOptional(true)
    .Build(FieldTotalPrice);
fields.Add(totalPrice);

LabelDefinition labelDefinition = LabelDefinition.Create(LabelName, fields);

LabelCaptureSettings settings =
    LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
```

### Notes when generating the definition

- Build **only** the field types the user selected. Don't add unused fields.
- The field-builder methods come in two layers:
  - **Shared (every field):** `IsOptional(bool)`, `SetValueRegex(string)` / `SetValueRegexes(IList<string>)`, `SetNumberOfMandatoryInstances(int?)`, `SetHiddenProperty/Properties`.
  - **Barcode fields:** `SetSymbology(Symbology)` (single) / `SetSymbologies(IList<Symbology>)` (set); `CustomBarcode` also has `SetAnchorRegex(es)` and `SetLocation(...)`.
  - **Custom text:** `SetValueRegex(es)` for the value pattern, `SetAnchorRegex(es)` for contextual anchor keywords, `SetLocation(...)`.
  - **Date fields** (`ExpiryDateText`/`PackingDateText`/`DateText`): `SetLabelDateFormat(LabelDateFormat)`.
- `SetSymbologies` takes an `IList<Symbology>` — use `new List<Symbology> { ... }`, **not** a vararg. For a single symbology use `SetSymbology(Symbology.X)`.
- Symbology values are PascalCase (`Symbology.Ean13Upca`), from `Scandit.DataCapture.Barcode.Data`. Do **not** use the Kotlin underscore form (`EAN13_UPCA`).
- For a custom text value pattern use `.SetValueRegex("<pattern>")` (or `.SetValueRegexes(new List<string>{...})`). Do **not** use `setPattern` / `setDataTypePattern` — those are old native names that don't exist in .NET.
- An equivalent way to assemble fields is `LabelDefinitionBuilder` (`new LabelDefinitionBuilder().AddCustomBarcode(barcode).AddExpiryDateText(expiry).Build(name)`), but the direct `LabelDefinition.Create(name, fields)` shown above is simplest.

### Prebuilt label definitions

For common documents, skip manual field building and use a prebuilt definition:

```csharp
LabelDefinition vin   = LabelDefinition.CreateVinLabelDefinition("VIN");           // 8.2+
LabelDefinition price = LabelDefinition.CreatePriceCaptureDefinition("Price Tag"); // 8.2+
LabelDefinition seg   = LabelDefinition.CreateSevenSegmentDisplayLabelDefinition("Meter"); // 8.2+
```

## Step 3 — Create the LabelCapture mode

`LabelCapture` is created with a **static factory** that attaches the mode to the context. There is **no** public `new LabelCapture(...)` and no `forDataCaptureContext`.

```csharp
this.labelCapture = LabelCapture.Create(this.dataCaptureContext, settings);
```

### LabelCapture members

| Member | Description |
|--------|-------------|
| `static LabelCapture Create(DataCaptureContext?, LabelCaptureSettings)` | Factory — creates the mode and attaches it to the context. |
| `Enabled` | `bool` (get/set) — **`true` to process frames.** Set `false` after a capture to stop re-capturing the same label; re-enable to scan again. |
| `static CameraSettings RecommendedCameraSettings` | Property — recommended camera settings for label capture. |
| `ApplySettingsAsync(LabelCaptureSettings)` | `Task` — apply new settings at runtime. |
| `AddListener(ILabelCaptureListener)` / `RemoveListener(...)` | Register / remove a listener. |
| `event EventHandler<LabelCaptureEventArgs> SessionUpdated` | Idiomatic C# alternative to a listener (corresponds to `OnSessionUpdated`). |
| `Feedback` | `LabelCaptureFeedback` (get/set) — sound / vibration. |
| `Context` | `DataCaptureContext?` (get). |
| `Dispose()` | Releases native resources. |

## Step 4 — Set up the camera (you manage it; the view does not)

Get the default camera with the recommended settings and set it as the context's frame source. Keep a reference so you can switch it on/off across the lifecycle.

```csharp
using Scandit.DataCapture.Core.Source;

CameraSettings cameraSettings = LabelCapture.RecommendedCameraSettings;
this.camera = Camera.GetDefaultCamera(cameraSettings);
if (this.camera is null)
{
    throw new InvalidOperationException("Smart Label Capture requires a camera.");
}

_ = this.dataCaptureContext.SetFrameSourceAsync(this.camera);
```

The camera is off by default. You turn it on in `OnResume` (after permission is granted) and off in `OnPause` (Step 7).

> **Do not make `OnCreate` `async` and do not `await` `SetFrameSourceAsync` inside it.** With `async void OnCreate`, the activity returns control to Android at the first `await`, and Android proceeds to call `OnStart` / `OnResume` before the rest of `OnCreate` has run. `OnResume` then touches `labelCapture` (or the camera) before it has been assigned, throwing `NullReferenceException` — surfaced as `Android.Runtime.JavaProxyThrowable` at startup. Keep `OnCreate` synchronous and discard the Task with `_ =`; the SDK handles the frame source being attached asynchronously.

## Step 5 — Visualize with DataCaptureView + LabelCaptureBasicOverlay

Label Capture uses the generic `DataCaptureView` (not a dedicated label view). Create it from the context, add it to your layout, then add a `LabelCaptureBasicOverlay` so detected labels/fields are highlighted.

```csharp
using Android.Views;
using Android.Widget;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.UI.Overlay;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);

// Add it to a container from your XML layout...
FrameLayout container = this.FindViewById<FrameLayout>(Resource.Id.data_capture_view_container)!;
container.AddView(
    this.dataCaptureView,
    new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));

// ...or host it full-screen in a FrameLayout created in code:
// var container = new FrameLayout(this);
// this.SetContentView(container);
// container.AddView(this.dataCaptureView);

this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
this.dataCaptureView.AddOverlay(this.overlay);

// Optional: guide the user with a viewfinder.
// this.overlay.Viewfinder = new RectangularViewfinder(RectangularViewfinderStyle.Square);
```

> `LabelCaptureBasicOverlay.Create(labelCapture)` takes only the mode. (There is also a `Create(labelCapture, dataCaptureView)` overload that auto-adds the overlay to that view — but the explicit `AddOverlay` form above is clearer.) Do **not** look for a native `newInstance(mode, view)`.

### Common LabelCaptureBasicOverlay members

| Member | Description |
|--------|-------------|
| `static Create(LabelCapture)` / `Create(LabelCapture, DataCaptureView?)` | Factory. |
| `Listener` | `ILabelCaptureBasicOverlayListener?` — custom brushes + tap callback. |
| `PredictedFieldBrush` / `CapturedFieldBrush` / `LabelBrush` | `Brush?` (get/set); static `Default*Brush` provide defaults. |
| `SetBrushForField(Brush?, LabelField, CapturedLabel)` / `SetBrushForLabel(Brush?, CapturedLabel)` | Per-field / per-label brush override. |
| `GetFieldBrush(LabelFieldState)` / `SetFieldBrush(LabelFieldState, Brush?)` | Default brush per field state. |
| `Viewfinder` | `IViewfinder?` (get/set). |
| `ShouldShowScanAreaGuides` | `bool` (get/set) — development only. |
| `Dispose()` | Releases native resources. |

## Step 6 — Handle captured labels

`OnSessionUpdated` (equivalently the `SessionUpdated` event) fires for **every processed frame**. It runs on a **background thread**. Check `session.CapturedLabels`; when a label is present, read its fields by name, disable the mode to avoid re-capturing, and dispatch UI work to the main thread.

The idiomatic C# pattern is the event:

```csharp
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;

// After creating labelCapture (or in OnResume — see Step 7):
this.labelCapture.SessionUpdated += this.OnSessionUpdated;

private void OnSessionUpdated(object? sender, LabelCaptureEventArgs args)
{
    IList<CapturedLabel> labels = args.Session.CapturedLabels;
    if (labels.Count == 0)
    {
        return;
    }

    CapturedLabel label = labels[0];

    // Match fields by the exact name passed to .Build("...").
    string? barcodeData = label.Fields
        .FirstOrDefault(f => f.Name == FieldBarcode)?.Barcode?.Data;
    string? expiryDate = label.Fields
        .FirstOrDefault(f => f.Name == FieldExpiryDate)?.Text;

    // Stop capturing the same label repeatedly.
    this.labelCapture.Enabled = false;

    this.RunOnUiThread(() =>
    {
        // Present barcodeData / expiryDate to the user.
    });
}
```

If you prefer the listener interface, implement `ILabelCaptureListener`:

```csharp
using Scandit.DataCapture.Core.Data;

public class LabelCaptureRepository : Java.Lang.Object, ILabelCaptureListener
{
    public void OnSessionUpdated(LabelCapture mode, LabelCaptureSession session, IFrameData data)
    {
        if (session.CapturedLabels.Count == 0) return;
        var label = session.CapturedLabels[0];
        // ...read fields, mode.Enabled = false, dispatch to UI...
    }

    public void OnObservationStarted(LabelCapture mode) { }
    public void OnObservationStopped(LabelCapture mode) { }
}

// In setup:
this.labelCapture.AddListener(new LabelCaptureRepository());
```

> Use **either** `AddListener` **or** the `SessionUpdated` event for a given handler — both deliver the same callback; subscribing to both double-processes.

### Reading field values

`LabelField` exposes typed accessors — pick the one matching the field type:

| Accessor | Type | Use for |
|----------|------|---------|
| `field.Barcode?.Data` | `string?` | barcode fields (`field.Barcode` is a `Barcode?`) |
| `field.Text` | `string?` | text fields (prices, weight, custom text, and the raw date string) |
| `field.Date` | `LabelDate?` | structured date — `Year` / `Month` / `Day` (`int?`) and `DayString` / `MonthString` / `YearString` |

Other `LabelField` members: `Name`, `Type` (`LabelFieldType.Barcode`/`Text`/`Unknown`), `State` (`LabelFieldState.Captured`/`Predicted`/`Unknown`), `Required` (`bool`), `PredictedLocation` (`Quadrilateral`). `CapturedLabel` exposes `Fields`, `Name`, `Complete` (all required fields captured), and `TrackingId`.

### LabelCaptureSession members

| Member | Type | Description |
|--------|------|-------------|
| `CapturedLabels` | `IList<CapturedLabel>` | Labels recognized in the current frame. |
| `FrameSequenceId` | `long` | Identifier of the underlying frame sequence. |
| `LastProcessedFrameId` | `int` | Id of the last processed frame. |

## Step 7 — Camera permission and lifecycle

Toggle the camera and the mode across the activity lifecycle. The camera — not the view — is the lifecycle handle.

```csharp
using Scandit.DataCapture.Core.Source;

protected override void OnResume()
{
    base.OnResume();

    this.labelCapture.SessionUpdated += this.OnSessionUpdated;
    this.labelCapture.Enabled = true;

    // Request camera permission; the camera is turned on once granted.
    this.RequestCameraPermission();
}

protected override void OnPause()
{
    base.OnPause();
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
}

protected override void OnCameraPermissionGranted()
{
    // Permission granted (or already held) — turn the camera on.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

protected override void OnDestroy()
{
    base.OnDestroy();
    this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
    this.overlay.Dispose();
    this.labelCapture.Dispose();
}
```

## Step 8 — Provide feedback (optional)

Label Capture emits sound/vibration automatically on a successful capture, configurable via `labelCapture.Feedback`.

```csharp
using Scandit.DataCapture.Core.Common.Feedback;
using Scandit.DataCapture.Label.Feedback;

// Default (vibration + beep):
this.labelCapture.Feedback = LabelCaptureFeedback.Default;

// Customize the single Success slot:
var feedback = LabelCaptureFeedback.Default;
feedback.Success = new Feedback(Vibration.DefaultVibration, sound: null); // vibrate only
this.labelCapture.Feedback = feedback;
```

> `LabelCaptureFeedback.Default` is a **static property**, and `LabelCaptureFeedback` exposes only a `Success` slot (there is no `Failure`). Audio plays only if the device is not muted.

## Step 9 — Customize the basic overlay (optional)

The basic overlay highlights detected labels and fields with a `Brush` (fill + stroke). You can change the highlight either **globally** (one brush for all fields/labels) or **per field/label** through a listener.

Globally — set the brush properties on the overlay instance:

```csharp
using Scandit.DataCapture.Core.UI.Style; // Brush

// All three are Brush? (get/set); the static Default*Brush values provide the SDK defaults.
this.overlay.CapturedFieldBrush  = new Brush(fillColor, strokeColor, strokeWidth: 2f); // matched this frame
this.overlay.PredictedFieldBrush = LabelCaptureBasicOverlay.DefaultPredictedFieldBrush; // predicted / in-progress
this.overlay.LabelBrush          = Brush.TransparentBrush;                              // hide the whole-label box
```

> `CapturedFieldBrush` is the brush for a field matched in the current frame; `PredictedFieldBrush` is the brush for a field the SDK has predicted but not yet confirmed. `LabelBrush` is the box around the whole label. Use `Brush.TransparentBrush` to hide a box entirely.

Per field / per label — implement `ILabelCaptureBasicOverlayListener` and return a `Brush?` (return `null` to fall back to the default). `BrushForField` is called once per field, `BrushForLabel` once per label; `OnLabelTapped` fires on a user tap.

```csharp
using Android.Content;
using Scandit.DataCapture.Core.UI.Style;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

public sealed class HighlightListener : Java.Lang.Object, ILabelCaptureBasicOverlayListener
{
    private readonly Brush expiryBrush;

    public HighlightListener(Brush expiryBrush) => this.expiryBrush = expiryBrush;

    // Per-field brush. Match by the name passed to .Build("...").
    public Brush? BrushForField(LabelCaptureBasicOverlay overlay, LabelField field, CapturedLabel label) =>
        field.Name == "Expiry Date" ? this.expiryBrush : null; // null => default brush

    // Per-label brush; return null to keep the default whole-label box (or Brush.TransparentBrush to hide it).
    public Brush? BrushForLabel(LabelCaptureBasicOverlay overlay, CapturedLabel label) => null;

    public void OnLabelTapped(LabelCaptureBasicOverlay overlay, CapturedLabel label)
    {
        // React to the user tapping a highlighted label.
    }
}

// Wire it up:
this.overlay.Listener = new HighlightListener(myExpiryBrush);
```

> `Brush` lives in `Scandit.DataCapture.Core.UI.Style`. Construct it with `new Brush(Color fillColor, Color strokeColor, float strokeWidth)`. On .NET, `Brush.Transparent` is exposed as the **property** `Brush.TransparentBrush`, not a method.

## Step 10 — Advanced overlay for custom Android views (optional)

For Augmented-Reality use cases — drawing your own Android `View` (e.g. a warning badge) anchored to a captured label or field — use `LabelCaptureAdvancedOverlay` instead of (or alongside) the basic overlay. You implement `ILabelCaptureAdvancedOverlayListener`; the overlay calls you back to supply a `View?` plus an `Anchor` and `PointWithUnit` offset for each captured label and field.

```csharp
using Android.Views;
using Scandit.DataCapture.Core.Common.Geometry; // Anchor, PointWithUnit, MeasureUnit
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

var advancedOverlay = LabelCaptureAdvancedOverlay.Create(this.labelCapture);
this.dataCaptureView.AddOverlay(advancedOverlay);
advancedOverlay.Listener = new ExpiryWarningOverlayListener(this);

public sealed class ExpiryWarningOverlayListener : Java.Lang.Object, ILabelCaptureAdvancedOverlayListener
{
    private readonly Context context;
    public ExpiryWarningOverlayListener(Context context) => this.context = context;

    // Whole-label view (return null to add views only to specific fields).
    public View? ViewForCapturedLabel(LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel) => null;

    public Anchor AnchorForCapturedLabel(LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel) =>
        Anchor.Center;

    public PointWithUnit OffsetForCapturedLabel(
        LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel, View view) =>
        new PointWithUnit(0f, 0f, MeasureUnit.Pixel);

    // Per-field view — return an Android View to anchor over the field, or null for none.
    public View? ViewForCapturedLabelField(LabelCaptureAdvancedOverlay overlay, LabelField labelField)
    {
        if (labelField.Name == "Expiry Date" && labelField.Type == LabelFieldType.Text)
        {
            var badge = new TextView(this.context) { Text = "Expires soon!" };
            return badge;
        }
        return null;
    }

    public Anchor AnchorForCapturedLabelField(LabelCaptureAdvancedOverlay overlay, LabelField labelField) =>
        Anchor.BottomCenter;

    public PointWithUnit OffsetForCapturedLabelField(
        LabelCaptureAdvancedOverlay overlay, LabelField labelField, View view) =>
        new PointWithUnit(0f, 22f, MeasureUnit.Dip);
}
```

> The advanced overlay is a separate `DataCaptureOverlay` from the basic one — you can add both to the same `DataCaptureView`. Use the basic overlay for highlight boxes (Step 9) and the advanced overlay for arbitrary AR content.

## Step 11 — Adaptive Recognition / Cloud Fallback (Beta, optional)

> **Beta.** The Adaptive Recognition Engine (ARE) is in beta and may change. It requires a license key with the ARE feature flag — contact `support@scandit.com` to enable it on a production subscription; trial keys are available for evaluation.

ARE is a cloud-based OCR fallback: when the on-device model fails to capture a field, the SDK escalates the frame to a larger cloud model so the user doesn't have to type the value by hand. It only kicks in through the **Validation Flow** (see `references/validation-flow.md`). Enable it with a single line on the `LabelDefinition` — set `AdaptiveRecognitionMode` to `AdaptiveRecognitionMode.Auto`:

```csharp
using Scandit.DataCapture.Label.Capture;

LabelDefinition labelDefinition = LabelDefinition.Create(LabelName, fields);
labelDefinition.AdaptiveRecognitionMode = AdaptiveRecognitionMode.Auto; // Beta: enables the cloud fallback

LabelCaptureSettings settings =
    LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
```

> `AdaptiveRecognitionMode.Off` (the default) keeps everything on-device. Cloud fallback only takes effect when the label is scanned through `LabelCaptureValidationFlowOverlay`.

## Setup checklist

After writing the integration code, show this checklist:

1. Add `Scandit.DataCapture.Core`, `Scandit.DataCapture.Barcode`, and `Scandit.DataCapture.Label` to the `.csproj` (use the version pinned in **Step 0** — do not guess). No separate text-models package is needed.
2. Ensure `<SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` to `AndroidManifest.xml`.
4. Request the `CAMERA` permission at runtime before scanning starts (the `CameraPermissionActivity` helper below).
5. Create `MainApplication.cs` with `ScanditCaptureCore.Initialize()`, `ScanditBarcodeCapture.Initialize()`, **and `ScanditLabelCapture.Initialize()`** (SDK 8.0+).
6. Ensure the activity uses a `Theme.AppCompat` descendant (manifest `<application android:theme=...>` or the `[Activity]` `Theme=` attribute).
7. Provide a layout with a container (e.g. a `FrameLayout`) for the `DataCaptureView`, or host it full-screen in a `FrameLayout` created in code.
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Complete minimal example

```csharp
using Android.OS;
using Android.Views;
using Android.Widget;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private const string FieldBarcode = "Barcode";
    private const string FieldExpiryDate = "Expiry Date";
    private const string FieldTotalPrice = "Total Price";
    private const string LabelName = "Retail Item";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private LabelCapture labelCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private LabelCaptureBasicOverlay overlay = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Camera (you manage it — the view does not).
        this.camera = Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            _ = this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        // Build the label definition.
        var fields = new List<LabelFieldDefinition>
        {
            CustomBarcode.Builder()
                .SetSymbologies(new List<Symbology> { Symbology.Ean13Upca, Symbology.Code128 })
                .Build(FieldBarcode),
            ExpiryDateText.Builder()
                .SetLabelDateFormat(new LabelDateFormat(LabelDateComponentFormat.MDY, acceptPartialDates: false))
                .Build(FieldExpiryDate),
            TotalPriceText.Builder()
                .IsOptional(true)
                .Build(FieldTotalPrice),
        };
        LabelDefinition labelDefinition = LabelDefinition.Create(LabelName, fields);
        LabelCaptureSettings settings =
            LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });

        this.labelCapture = LabelCapture.Create(this.dataCaptureContext, settings);

        // Host the preview.
        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        container.AddView(
            this.dataCaptureView,
            new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));
        this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.labelCapture.SessionUpdated += this.OnSessionUpdated;
        this.labelCapture.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
        this.overlay.Dispose();
        this.labelCapture.Dispose();
    }

    private void OnSessionUpdated(object? sender, LabelCaptureEventArgs args)
    {
        if (args.Session.CapturedLabels.Count == 0)
        {
            return;
        }

        CapturedLabel label = args.Session.CapturedLabels[0];
        string? barcodeData = label.Fields.FirstOrDefault(f => f.Name == FieldBarcode)?.Barcode?.Data;
        string? expiryDate = label.Fields.FirstOrDefault(f => f.Name == FieldExpiryDate)?.Text;
        string? totalPrice = label.Fields.FirstOrDefault(f => f.Name == FieldTotalPrice)?.Text;

        this.labelCapture.Enabled = false;

        this.RunOnUiThread(() =>
        {
            // Present barcodeData / expiryDate / totalPrice.
        });
    }
}
```

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

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **No settings builder** — build each field with `Type.Builder()...Build("name")`, collect into `List<LabelFieldDefinition>`, `LabelDefinition.Create(name, fields)`, `LabelCaptureSettings.Create(new List<LabelDefinition> { def })`.
3. **`LabelCapture.Create(...)`** — factory; the constructor is private and there is no `forDataCaptureContext`.
4. **Symbologies are PascalCase** from `Scandit.DataCapture.Barcode.Data`; `SetSymbologies` takes an `IList<Symbology>`.
5. **Three NuGet packages** — `Core`, `Barcode`, `Label`. No `label-text-models` package.
6. **Three initializers** — `ScanditCaptureCore.Initialize()`, `ScanditBarcodeCapture.Initialize()`, `ScanditLabelCapture.Initialize()` in `MainApplication.OnCreate()` (SDK 8.0+).
7. **You manage the camera** — `Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Off)` in `OnResume`/`OnPause`. `RecommendedCameraSettings` is a static property.
8. **`DataCaptureView.Create(context)` + `LabelCaptureBasicOverlay.Create(labelCapture)` + `dataCaptureView.AddOverlay(overlay)`** — the view is generic; the overlay factory takes only the mode.
9. **`OnSessionUpdated` runs on a background thread** — read fields by name, set `labelCapture.Enabled = false` after a capture, and `RunOnUiThread` for UI.
10. **Read values via `LabelField`** — `Barcode?.Data`, `Text`, or `Date` (`LabelDate`), matching the field's declared name.
11. **No `<activity>` in the manifest** — `[Activity(MainLauncher = true, ...)]` is the canonical registration.
12. **`Theme.AppCompat` descendant** + **`SupportedOSPlatformVersion` ≥ 24** are required for the build/launch to succeed.

## Where to go next

- [Label Definitions](https://docs.scandit.com/sdks/net/android/label-capture/label-definitions/) — full catalogue of pre-built field types and how to tune their value/anchor regexes.
- [Advanced Configurations](https://docs.scandit.com/sdks/net/android/label-capture/advanced/) — Validation Flow (see `references/validation-flow.md`), adaptive recognition, advanced overlay for arbitrary Android views.
