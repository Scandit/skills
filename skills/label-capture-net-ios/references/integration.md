# Label Capture (Smart Label Capture) — .NET for iOS Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

The .NET binding differs from the native iOS (Swift) SDK in one big way: **there is no fluent `LabelCaptureSettings` builder chain.** You build each field with its own `.Builder()...Build("name")` factory, collect the fields into a list, wrap them in a `LabelDefinition`, and pass the definition(s) to `LabelCaptureSettings.Create(...)`.

Examples below use C# and a `UIViewController`. The same APIs work from any controller — adapt ownership of `DataCaptureContext`, `Camera`, `LabelCapture`, `DataCaptureView`, and the overlay to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts the `DataCaptureView` as a XAML element and wires it through handlers, which is different. **Also note:** the official iOS Get Started page contains some MAUI (XAML / `*.Maui`) snippets — ignore those here.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Label/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all three packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.Label with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.label/index.json` (last entry without a pre-release suffix) before proceeding.

Label Capture has been available on `dotnet.ios` since **8.2**, so any current stable release supports it. If the project already pins an older Scandit major (6.x / 7.x), Label Capture is not available there — tell the user they must move to 8.2+ to use it.

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
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj`:
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
  This is the Scandit iOS framework's minimum deployment target. A matching `MinimumOSVersion` belongs in `Info.plist`.
- **Camera usage description in `Info.plist`.** iOS requires `NSCameraUsageDescription` or the app crashes the moment the camera starts. iOS shows the permission prompt automatically the first time the camera switches on — there is no runtime-permission helper to write (unlike Android).
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan labels.</string>
  ```
- **SDK initialization (Scandit 8.0+).** In `AppDelegate.FinishedLaunching` (`application:didFinishLaunchingWithOptions:`), call **three** initializers before any Scandit type is constructed. Missing `ScanditLabelCapture.Initialize()` crashes the first `LabelCapture.Create(...)` call.

  ```csharp
  using Foundation;
  using UIKit;
  using Scandit.DataCapture.Barcode;
  using Scandit.DataCapture.Core;
  using Scandit.DataCapture.Label;

  namespace MyApp;

  [Register("AppDelegate")]
  public class AppDelegate : UIResponder, IUIApplicationDelegate
  {
      [Export("window")]
      public UIWindow? Window { get; set; }

      [Export("application:didFinishLaunchingWithOptions:")]
      public bool FinishedLaunching(UIApplication application, NSDictionary? launchOptions)
      {
          ScanditCaptureCore.Initialize();
          ScanditBarcodeCapture.Initialize();
          ScanditLabelCapture.Initialize();

          // ... existing launch code (root view controller, navigation controller, etc.)
          return true;
      }
  }
  ```

  If the project already has an `AppDelegate`, add the three `Initialize()` calls at the top of its existing `FinishedLaunching`. **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip it entirely** (though Label Capture itself needs 8.2+ on iOS).
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.

### Project scaffolding (new projects only)

If a .NET iOS project already exists, skip this and go to the Interactive Label Definition below.

**Recommended:** scaffold a buildable shell with the official template, then add Label Capture on top:

```bash
dotnet new ios -o MyApp
cd MyApp
```

Add the three Scandit packages from the bullets above, set `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>`, add `NSCameraUsageDescription` to `Info.plist`, add the three `Initialize()` calls to `AppDelegate`, and continue.

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

**Question C — Which file/`UIViewController` should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

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
- Symbology values are PascalCase (`Symbology.Ean13Upca`), from `Scandit.DataCapture.Barcode.Data`. Do **not** use the Swift form (`.ean13UPCA`).
- For a custom text value pattern use `.SetValueRegex("<pattern>")` (or `.SetValueRegexes(new List<string>{...})`). Do **not** use `setPattern` / `setDataTypePattern` — those are old native names that don't exist in .NET.
- An equivalent way to assemble fields is `LabelDefinitionBuilder` (`new LabelDefinitionBuilder().AddCustomBarcode(barcode).AddExpiryDateText(expiry).Build(name)`), but the direct `LabelDefinition.Create(name, fields)` shown above is simplest.

### Pre-built barcode fields (serial number, part number, IMEI)

For smart-device and electronics labels you rarely need to hand-write symbologies and regexes — the SDK ships **pre-built barcode field types** whose `Symbologies`, `ValueRegexes`, and `AnchorRegexes` are already configured. Build them exactly like `CustomBarcode`: a static `Builder()` then `.Build("name")`. The shared builder members (`IsOptional`, `SetValueRegex(es)`, `SetNumberOfMandatoryInstances`) still apply and **override** the pre-built defaults.

```csharp
using Scandit.DataCapture.Label.Data;

var fields = new List<LabelFieldDefinition>();

// Hard-disk-drive label: serial number + part number.
fields.Add(SerialNumberBarcode.Builder().Build("Serial Number"));
fields.Add(PartNumberBarcode.Builder().Build("Part Number"));

// Smart-device label: IMEI1 and IMEI2.
fields.Add(ImeiOneBarcode.Builder().Build("IMEI1"));
fields.Add(ImeiTwoBarcode.Builder().Build("IMEI2"));

LabelDefinition definition = LabelDefinition.Create("Device Label", fields);
LabelCaptureSettings settings =
    LabelCaptureSettings.Create(new List<LabelDefinition> { definition });
```

> On .NET, the native init factories `SerialNumberBarcode.FieldWithName(...)`, `ImeiOneBarcode.InitWithName(...)`, etc. are **not** available — always use `Type.Builder()...Build("name")`. These are barcode fields, so read their values via `field.Barcode?.Data` matching the declared name. `IsOptional`, `ValueRegexes`, and `NumberOfMandatoryInstances` are inherited from the shared field builder (they are not declared on the `ImeiOneBarcode`/`ImeiTwoBarcode` class itself, but are callable on the builder).

### Prebuilt label definitions (VIN, price label, 7-segment)

For whole common documents, skip manual field building and use a prebuilt **definition** factory — each returns a ready-to-use `LabelDefinition`:

```csharp
LabelDefinition vin   = LabelDefinition.CreateVinLabelDefinition("VIN");
LabelDefinition price = LabelDefinition.CreatePriceCaptureDefinition("Price Tag");
LabelDefinition seg   = LabelDefinition.CreateSevenSegmentDisplayLabelDefinition("Meter");

// Use it like any other definition:
LabelCaptureSettings settings =
    LabelCaptureSettings.Create(new List<LabelDefinition> { price });
```

> `CreatePriceCaptureDefinition` is for retail price labels, `CreateVinLabelDefinition` for vehicle VIN plates, and `CreateSevenSegmentDisplayLabelDefinition` for numeric 7-segment displays (digital scales, meters). Read their fields the same way — match by `Name` and use `Barcode?.Data` / `Text` / `Date`.

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

Get the default camera with the recommended settings and set it as the context's frame source. Keep a reference so you can switch it on/standby/off across the lifecycle.

```csharp
using Scandit.DataCapture.Core.Source;

CameraSettings cameraSettings = LabelCapture.RecommendedCameraSettings;
this.camera = Camera.GetDefaultCamera(cameraSettings);
if (this.camera is null)
{
    throw new InvalidOperationException("Smart Label Capture requires a camera.");
}

this.dataCaptureContext.SetFrameSourceAsync(this.camera);
```

The camera is off by default. You turn it on in `ViewWillAppear` and off in `ViewWillDisappear` (Step 7).

> **Do not make `ViewDidLoad` `async void` and do not `await` `SetFrameSourceAsync` inside it.** With `async void ViewDidLoad`, the controller returns control to UIKit at the first `await`, and UIKit proceeds to call `ViewWillAppear` before the rest of `ViewDidLoad` has run. `ViewWillAppear` then touches `labelCapture` (or the camera) before it has been assigned — leaving you with a black screen and no scans, or a `NullReferenceException`. Keep `ViewDidLoad` synchronous; the SDK handles the frame source being attached asynchronously. If you genuinely need to await camera setup, do it before pushing the view controller (e.g. in the parent).

## Step 5 — Visualize with DataCaptureView + LabelCaptureBasicOverlay

Label Capture uses the generic `DataCaptureView` (not a dedicated label view). On iOS, `DataCaptureView.Create` takes the context **and a `CGRect` frame** (typically `this.View!.Bounds`). The returned view **is** a `UIView` (implicit conversion), so add it with `AddSubview` and let it resize with its parent. Then add a `LabelCaptureBasicOverlay` so detected labels/fields are highlighted.

```csharp
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.UI.Overlay;
using UIKit;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);

UIView platformView = this.dataCaptureView;
platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
this.View.AddSubview(this.dataCaptureView);

this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
this.dataCaptureView.AddOverlay(this.overlay);

// Optional: guide the user with a viewfinder.
// this.overlay.Viewfinder = new RectangularViewfinder(RectangularViewfinderStyle.Square);
```

> `DataCaptureView.Create(context, frame)` — the second argument is a `CGRect`, **not** a parent view (that's the Android binding). `LabelCaptureBasicOverlay.Create(labelCapture)` takes only the mode. (There is also a `Create(labelCapture, dataCaptureView)` overload that auto-adds the overlay to that view — but the explicit `AddOverlay` form above is clearer.)

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
using UIKit;

// After creating labelCapture (or in ViewWillAppear — see Step 7):
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

    UIApplication.SharedApplication.InvokeOnMainThread(() =>
    {
        // Present barcodeData / expiryDate to the user.
    });
}
```

If you prefer the listener interface, implement `ILabelCaptureListener` (derive from `NSObject`):

```csharp
using Foundation;
using Scandit.DataCapture.Core.Data;

public class LabelCaptureRepository : NSObject, ILabelCaptureListener
{
    public void OnSessionUpdated(LabelCapture mode, LabelCaptureSession session, IFrameData data)
    {
        if (session.CapturedLabels.Count == 0) return;
        var label = session.CapturedLabels[0];
        // ...read fields, mode.Enabled = false, dispatch to the main thread...
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

A convenient pattern for "barcode value, falling back to text" (also used by the official iOS sample) is `field.Barcode?.Data ?? field.Text`.

Other `LabelField` members: `Name`, `Type` (`LabelFieldType.Barcode`/`Text`/`Unknown`), **`ValueType` (`LabelFieldValueType.Date`/`Price`/`Weight`/`Text`/`Numeric`, iOS-only)**, `State` (`LabelFieldState.Captured`/`Predicted`/`Unknown`), `Required` (`bool`), `PredictedLocation` (`Quadrilateral`). `CapturedLabel` exposes `Fields`, `Name`, `Complete` (all required fields captured), and `TrackingId`.

### LabelCaptureSession members

| Member | Type | Description |
|--------|------|-------------|
| `CapturedLabels` | `IList<CapturedLabel>` | Labels recognized in the current frame. |
| `FrameSequenceId` | `long` | Identifier of the underlying frame sequence. |
| `LastProcessedFrameId` | `int` | Id of the last processed frame. |

## Step 7 — Camera lifecycle

Toggle the camera and the mode across the view-controller lifecycle. The camera — not the view — is the lifecycle handle. iOS shows the camera permission prompt automatically the first time the camera turns on (because of `NSCameraUsageDescription`), so there is no permission code to write.

```csharp
using Scandit.DataCapture.Core.Source;

public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);

    this.labelCapture.SessionUpdated += this.OnSessionUpdated;
    this.labelCapture.Enabled = true;

    // Turn the camera on (iOS prompts for permission the first time).
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);

    // Standby keeps the camera warm when navigating within the app;
    // use FrameSourceState.Off when actually leaving / backgrounding.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
}
```

> Use `FrameSourceState.Standby` (not `Off`) if you navigate to a results screen *within* the app and want the camera to stay warm; use `Off` when actually backgrounding.

Release native resources when the controller is torn down (e.g. in `Dispose`):

```csharp
protected override void Dispose(bool disposing)
{
    if (disposing)
    {
        this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
        this.overlay?.Dispose();
        this.labelCapture?.Dispose();
    }

    base.Dispose(disposing);
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

## Setup checklist

After writing the integration code, show this checklist:

1. Add `Scandit.DataCapture.Core`, `Scandit.DataCapture.Barcode`, and `Scandit.DataCapture.Label` to the `.csproj` (use the version pinned in **Step 0** — do not guess). No separate text-models package is needed.
2. Ensure `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<key>NSCameraUsageDescription</key>` with a usage string to `Info.plist` (iOS prompts for camera permission automatically; no runtime-permission helper).
4. Add `ScanditCaptureCore.Initialize()`, `ScanditBarcodeCapture.Initialize()`, **and `ScanditLabelCapture.Initialize()`** to `AppDelegate.FinishedLaunching` (SDK 8.0+).
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Complete minimal example

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp;

// Code-only host (no Storyboard/XIB). If the controller is paired with a XIB,
// add [Register], `partial`, and the `IntPtr handle` constructor instead —
// see "Host UIViewController boilerplate" earlier in this guide.
public class ScanViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private const string FieldBarcode = "Barcode";
    private const string FieldExpiryDate = "Expiry Date";
    private const string FieldTotalPrice = "Total Price";
    private const string LabelName = "Retail Item";

    private DataCaptureContext? dataCaptureContext;
    private Camera? camera;
    private LabelCapture? labelCapture;
    private DataCaptureView? dataCaptureView;
    private LabelCaptureBasicOverlay? overlay;

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Camera (you manage it — the view does not). Keep ViewDidLoad SYNCHRONOUS —
        // fire-and-forget the async frame-source setup.
        this.camera = Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
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

        // Host the preview. DataCaptureView IS a UIView — add it yourself.
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        if (this.labelCapture is null) return;
        this.labelCapture.SessionUpdated += this.OnSessionUpdated;
        this.labelCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        if (this.labelCapture is not null)
        {
            this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
        }
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

        UIApplication.SharedApplication.InvokeOnMainThread(() =>
        {
            // Present barcodeData / expiryDate / totalPrice.
        });
    }
}
```

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **No settings builder** — build each field with `Type.Builder()...Build("name")`, collect into `List<LabelFieldDefinition>`, `LabelDefinition.Create(name, fields)`, `LabelCaptureSettings.Create(new List<LabelDefinition> { def })`.
3. **`LabelCapture.Create(...)`** — factory; the constructor is private and there is no `forDataCaptureContext`.
4. **Symbologies are PascalCase** from `Scandit.DataCapture.Barcode.Data`; `SetSymbologies` takes an `IList<Symbology>`.
5. **Three NuGet packages** — `Core`, `Barcode`, `Label`. No `label-text-models` package, no `*.Maui`.
6. **Three initializers** — `ScanditCaptureCore.Initialize()`, `ScanditBarcodeCapture.Initialize()`, `ScanditLabelCapture.Initialize()` in `AppDelegate.FinishedLaunching` (SDK 8.0+).
7. **You manage the camera** — `Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Standby/Off)` in `ViewWillAppear`/`ViewWillDisappear`. `RecommendedCameraSettings` is a static property.
8. **`DataCaptureView.Create(context, CGRect)` + `LabelCaptureBasicOverlay.Create(labelCapture)` + `dataCaptureView.AddOverlay(overlay)`** — the view's second arg is a `CGRect` frame; the view is a `UIView` you add with `this.View.AddSubview(...)`.
9. **`OnSessionUpdated` runs on a background thread** — read fields by name, set `labelCapture.Enabled = false` after a capture, and dispatch UI work via `UIApplication.SharedApplication.InvokeOnMainThread(...)` / `DispatchQueue.MainQueue.DispatchAsync(...)`.
10. **Read values via `LabelField`** — `Barcode?.Data`, `Text`, or `Date` (`LabelDate`), matching the field's declared name.
11. **`NSCameraUsageDescription` in `Info.plist`** — required; iOS prompts for camera permission automatically. No runtime-permission helper to write.
12. **Keep `ViewDidLoad` synchronous** + **`SupportedOSPlatformVersion` ≥ 15.0** are required for a working launch.

## Where to go next

- [Label Definitions](https://docs.scandit.com/sdks/net/ios/label-capture/label-definitions/) — full catalogue of pre-built field types and how to tune their value/anchor regexes.
- `references/advanced-overlays.md` — overlay brush customization, the advanced overlay for arbitrary native views, Adaptive Recognition cloud fallback (beta), and Receipt Scanning (beta).
- [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) — Validation Flow (see `references/validation-flow.md`), adaptive recognition, advanced overlay for arbitrary native views.
