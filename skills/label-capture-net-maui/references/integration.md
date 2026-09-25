# Label Capture (Smart Label Capture) — .NET MAUI Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

On .NET MAUI you combine the cross-platform `Scandit.DataCapture.Core` / `Scandit.DataCapture.Barcode` / `Scandit.DataCapture.Label` APIs (a `DataCaptureContext`, a `Camera`, a `LabelCapture` mode, the listener / `SessionUpdated` event) with two MAUI-specific pieces: the generic **`<scandit:DataCaptureView>`** XAML control from `Scandit.DataCapture.Core.UI.Maui`, and a **`LabelCaptureBasicOverlay` created after the view's platform handler has attached** (`HandlerChanged`).

The .NET binding differs from the native Swift/Kotlin SDKs in one big way: **there is no fluent `LabelCaptureSettings` builder chain.** You build each field with its own `.Builder()...Build("name")` factory, collect the fields into a list, wrap them in a `LabelDefinition`, and pass the definition(s) to `LabelCaptureSettings.Create(...)`.

The examples below follow the structure of the official Scandit MAUI `LabelCaptureSimpleSample`: a `MainPage` (`ContentPage`) wired to a `MainPageViewModel` via `BindingContext`, with small services (`ICameraService`, `ILabelCaptureService`) owning the SDK objects, and `DataCaptureContext` / `Camera` registered through dependency injection in `MauiProgram.cs`. You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `label-capture-net-android` (for `net*-android`) or `label-capture-net-ios` (for `net*-ios`). Those skills host the preview through a native `Activity` / `UIViewController`, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Label/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all four packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `NU1103` / `Unable to find package … with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.label/index.json` (last entry without a pre-release suffix) before proceeding.

Label Capture has been available on `dotnet.android` since **8.1** and `dotnet.ios` since **8.2**, so any current stable release supports it in MAUI. If the project already pins an older Scandit major (6.x / 7.x), Label Capture is not available there — tell the user they must move to 8.2+.

### Other prerequisites

- Add **four** NuGet packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Label" Version="<step-0-version>" />
  </ItemGroup>
  ```
  - `Core.Maui` provides the `<scandit:DataCaptureView>` XAML control, the `UseScanditCore` builder extension, and the `AddDataCaptureContext` / `AddCamera` DI helpers.
  - `Barcode` is required because the `Symbology` enum and the barcode field types (`CustomBarcode`, etc.) live there.
  - `Label` is the mode plus all text recognizers (expiry date, prices, weight, custom text). **There is no separate `label-text-models` package.**
  - **There is NO `Scandit.DataCapture.Label.Maui` package** — Label Capture has no MAUI-specific assembly. Do not add one. (This is unlike Barcode/MatrixScan, which has `Barcode.Maui`.)
- A `<UseMaui>true</UseMaui>` project targeting at least one of `net10.0-android` / `net10.0-ios` (adjust the TFM to the project's .NET version).
- **`SupportedOSPlatformVersion`** — iOS must be ≥ `15.0` (the MAUI template default) and **Android must be ≥ `24`**. The MAUI template defaults Android to `21`, which is below Scandit's Android AAR minimum and fails the build with `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library`. Bump it:
  ```xml
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'ios'">15.0</SupportedOSPlatformVersion>
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">24.0</SupportedOSPlatformVersion>
  ```
- **Camera permission / platform config:**
  - **iOS**: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` (and a matching `MinimumOSVersion` of `15.0`). Without it the app crashes the moment the camera starts.
    ```xml
    <key>NSCameraUsageDescription</key>
    <string>Used to scan labels.</string>
    ```
  - **Android**: `Permissions.Camera` (requested at runtime, Step 6) makes MAUI add `android.permission.CAMERA`; you can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.

## Step 1 — Initialize the SDK in MauiProgram.cs

This is the **most MAUI-specific step** and the one most often gotten wrong. Call **`ScanditLabelCapture.Initialize()` directly** (it registers all the Label Capture types and the barcode field builders), and chain **`.UseScanditCore(configure => configure.AddDataCaptureView())`** (which calls `ScanditCaptureCore.Initialize()` and registers the `DataCaptureView` MAUI handler). Then register the context and camera through DI.

```csharp
using Scandit.DataCapture.Core;          // UseScanditCore
using Scandit.DataCapture.Core.Source;   // CameraPosition
using Scandit.DataCapture.Label;         // ScanditLabelCapture
using Scandit.DataCapture.Label.Capture; // LabelCapture (RecommendedCameraSettings)
#if IOS
using Microsoft.Maui.Platform;
#endif

namespace MyApp;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        // Registers the LabelCapture mode, settings, all field builders, overlays, feedback.
        ScanditLabelCapture.Initialize();

#if IOS
        // Only needed if you use the Validation Flow's manual-entry text field on iOS 18+.
        // MAUI's KeyboardAutoManagerScroll prevents the UITextField from becoming first
        // responder inside the validation-flow's hosted view. Harmless otherwise.
        KeyboardAutoManagerScroll.Disconnect();
#endif

        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>()
               .ConfigureFonts(fonts => fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular"))
               // Registers the DataCaptureView handler AND calls ScanditCaptureCore.Initialize().
               .UseScanditCore(configure => configure.AddDataCaptureView());

        // DI: create the shared DataCaptureContext and a camera with the recommended settings.
        builder.Services.AddDataCaptureContext(App.SCANDIT_LICENSE_KEY);
        builder.Services.AddCamera(configure =>
        {
            configure.Position = CameraPosition.WorldFacing;
            configure.Settings = LabelCapture.RecommendedCameraSettings;
        });

        // Your services / view models / pages.
        builder.Services.AddSingleton<ICameraService, CameraService>();
        builder.Services.AddSingleton<ILabelCaptureService, LabelCaptureService>();
        builder.Services.AddTransient<MainPageViewModel>();
        builder.Services.AddTransient<MainPage>();

        return builder.Build();
    }
}
```

> **Key init rules:**
> - **`ScanditLabelCapture.Initialize()` is called manually** — there is no `UseScanditLabel()` builder extension.
> - **Do NOT call `UseScanditBarcode()` or `ScanditBarcodeCapture.Initialize()`** for Label Capture. `Symbology` is just an enum, and the barcode *field* builders are registered by `ScanditLabelCapture.Initialize()`.
> - **Do NOT add `ScanditCaptureCore.Initialize()` etc. to `MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`.** `UseScanditCore` handles core init. The MAUI `MainApplication` / `AppDelegate` stay as the template generates them (just forwarding to `MauiProgram.CreateMauiApp()`).
> - `AddDataCaptureContext(licenseKey)` and `AddCamera(...)` come from `Scandit.DataCapture.Core` (the `Core.Maui` assembly). They register a singleton `DataCaptureContext` and `Camera` for injection. For a tiny app you can skip DI and use `DataCaptureContext.ForLicenseKey(key)` + `Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings)` directly instead.

Put the license key on `App`:

```csharp
public partial class App : Application
{
    // Your Scandit License key is available via your Scandit SDK web account.
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";
    // ...
}
```

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
- Is it **required** or **optional**? Optional fields call `.IsOptional(true)`; required fields omit it (required is the default).
- For `CustomBarcode`: which **symbologies**? Mention that enabling only the symbologies they actually need improves scanning performance. .NET symbology names are PascalCase: `Symbology.Ean13Upca`, `Symbology.Code128`, `Symbology.Gs1DatabarExpanded`, `Symbology.Qr`, `Symbology.DataMatrix`, etc.
- For `CustomText`: what **value regex** should the text match?
- For `ExpiryDateText` / `PackingDateText` / `DateText`: a specific date format? If so, ask the component order (MDY, DMY, YMD, …) and whether partial dates are accepted.

**Question C — Which page/view model should the integration go in?** Then write the code directly into those files. Do not just show it in chat.

Each field also has a unique **name** string you pass to `.Build("name")`. You use that same name later to read the value out of the captured label, so keep the names in constants.

## Step 2 — Build the label definition, settings, and the LabelCapture mode

Build each field with its own `.Builder()...Build("name")` factory, collect them into a `List<LabelFieldDefinition>`, wrap them in a `LabelDefinition`, create the settings, and create the mode with `LabelCapture.Create`. **This is the part most often gotten wrong** — there is no `LabelCaptureSettings.builder()`/`addLabel()` chain.

A clean MAUI shape is a small service that owns the `LabelCapture` mode (injected `DataCaptureContext`):

```csharp
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;
using Brush = Scandit.DataCapture.Core.UI.Style.Brush;

namespace MyApp.Services;

internal class LabelCaptureService(DataCaptureContext dataCaptureContext) : ILabelCaptureService
{
    public const string FIELD_BARCODE = "Barcode";
    public const string FIELD_EXPIRY_DATE = "Expiry Date";
    public const string FIELD_TOTAL_PRICE = "Total Price";
    public const string LABEL_RETAIL_ITEM = "Retail Item";

    private readonly LabelCapture labelCapture =
        LabelCapture.Create(dataCaptureContext, BuildLabelCaptureSettings());

    public bool IsEnabled => this.labelCapture.Enabled;
    public void Enable() => this.labelCapture.Enabled = true;
    public void Disable() => this.labelCapture.Enabled = false;

    public LabelCaptureBasicOverlay BuildOverlay()
    {
        // Single-arg Create in MAUI; attach to the DataCaptureView in HandlerChanged (Step 4).
        var overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        return overlay;
    }

    private static LabelCaptureSettings BuildLabelCaptureSettings()
    {
        var fields = new List<LabelFieldDefinition>();

        // A custom barcode field (required by default). SetSymbologies takes an IList<Symbology>.
        fields.Add(CustomBarcode.Builder()
            .SetSymbologies(new List<Symbology>
            {
                Symbology.Ean13Upca,
                Symbology.Gs1DatabarExpanded,
                Symbology.Code128,
            })
            .Build(FIELD_BARCODE));

        // An expiry date field with an explicit date format.
        fields.Add(ExpiryDateText.Builder()
            .SetLabelDateFormat(new LabelDateFormat(LabelDateComponentFormat.MDY, acceptPartialDates: false))
            .Build(FIELD_EXPIRY_DATE));

        // An optional total-price field.
        fields.Add(TotalPriceText.Builder()
            .IsOptional(true)
            .Build(FIELD_TOTAL_PRICE));

        var labelDefinition = LabelDefinition.Create(LABEL_RETAIL_ITEM, fields);
        return LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
    }
}
```

### Notes when generating the definition

- Build **only** the field types the user selected. Don't add unused fields.
- The field-builder methods come in two layers:
  - **Shared (every field):** `IsOptional(bool)`, `SetValueRegex(string)` / `SetValueRegexes(IList<string>)`, `SetNumberOfMandatoryInstances(int?)`, `SetHiddenProperty/Properties`.
  - **Barcode fields:** `SetSymbology(Symbology)` (single) / `SetSymbologies(IList<Symbology>)` (set); `CustomBarcode` also has `SetAnchorRegex(es)` and `SetLocation(...)`.
  - **Custom text:** `SetValueRegex(es)` for the value pattern, `SetAnchorRegex(es)` for contextual anchor keywords, `SetLocation(...)`.
  - **Date fields** (`ExpiryDateText`/`PackingDateText`/`DateText`): `SetLabelDateFormat(LabelDateFormat)`.
- `SetSymbologies` takes an `IList<Symbology>` — use `new List<Symbology> { ... }`, **not** a vararg. For a single symbology use `SetSymbology(Symbology.X)`.
- Symbology values are PascalCase (`Symbology.Ean13Upca`), from `Scandit.DataCapture.Barcode.Data`. Do **not** use Swift's `.ean13UPCA` or Kotlin's `EAN13_UPCA`.
- For a custom text value pattern use `.SetValueRegex("<pattern>")`. Do **not** use the old native `setPattern` / `setDataTypePattern`.
- `LabelCapture.Create(context, settings)` is a **static factory** — the constructor is private and there is no `forDataCaptureContext`.

### Semantic barcode fields (serial number / part number / IMEI)

For common identifiers, use the preset barcode field types instead of a `CustomBarcode` with hand-written symbologies/regexes — their `Symbologies` and `ValueRegexes` are already tuned. Each is built with the same `.Builder()...Build("name")` shape and reads back as a barcode field (`field.Barcode?.Data`):

```csharp
// Electronics / asset label: serial + part number (HDD-style label).
fields.Add(SerialNumberBarcode.Builder().Build("Serial Number"));
fields.Add(PartNumberBarcode.Builder().Build("Part Number"));

// Mobile-device label: IMEI codes (ImeiTwo for dual-SIM devices).
fields.Add(ImeiOneBarcode.Builder().Build("IMEI"));
fields.Add(ImeiTwoBarcode.Builder().Build("IMEI2"));
```

These live in `Scandit.DataCapture.Label.Data` (the same namespace as `CustomBarcode`). They accept the shared builder members (`IsOptional(bool)`, `SetSymbologies`/`SetSymbology`, `SetValueRegex(es)`) if you need to narrow the presets, but for standard labels the defaults are enough. Read their values exactly like any barcode field, matching the `Name` you passed to `.Build("...")`.

### Prebuilt label definitions

For whole common documents, skip manual field building entirely and use a prebuilt `LabelDefinition` factory. Each takes only a name and returns a definition you pass straight to `LabelCaptureSettings.Create(...)`:

```csharp
LabelDefinition vin   = LabelDefinition.CreateVinLabelDefinition("VIN");
LabelDefinition price = LabelDefinition.CreatePriceCaptureDefinition("Price Tag");
LabelDefinition seg   = LabelDefinition.CreateSevenSegmentDisplayLabelDefinition("Meter");

// Use one (or several) directly as the settings:
var settings = LabelCaptureSettings.Create(new List<LabelDefinition> { price });
```

- `CreatePriceCaptureDefinition(name)` — retail price tags (product barcode + price/weight text).
- `CreateVinLabelDefinition(name)` — vehicle VIN labels.
- `CreateSevenSegmentDisplayLabelDefinition(name)` — seven-segment digital displays (e.g. utility meters, scales).

Read the captured fields by their built-in names the same way as custom fields. If you don't know the field names a prebuilt definition exposes, iterate `label.Fields` and switch on `field.Type` (`LabelFieldType.Barcode` → `field.Barcode?.Data`, `LabelFieldType.Text` → `field.Text`). All three factories are available on `dotnet.android` since 8.1 and `dotnet.ios` since 8.2.

### LabelCapture members

| Member | Description |
|--------|-------------|
| `static LabelCapture Create(DataCaptureContext?, LabelCaptureSettings)` | Factory — creates the mode and attaches it to the context. |
| `Enabled` | `bool` (get/set) — **`true` to process frames.** Set `false` after a capture to stop re-capturing the same label; re-enable to scan again. |
| `static CameraSettings RecommendedCameraSettings` | **Property** — recommended camera settings for label capture. |
| `ApplySettingsAsync(LabelCaptureSettings)` | `Task` — apply new settings at runtime. |
| `AddListener(ILabelCaptureListener)` / `RemoveListener(...)` | Register / remove a listener. |
| `event EventHandler<LabelCaptureEventArgs> SessionUpdated` | Idiomatic C# alternative to a listener. |
| `Feedback` | `LabelCaptureFeedback` (get/set) — sound / vibration. |
| `Context` | `DataCaptureContext?` (get). |
| `Dispose()` | Releases native resources. |

## Step 3 — Add the DataCaptureView in XAML

Label Capture uses the generic `<scandit:DataCaptureView>` (not a dedicated label view). Add the XAML namespace and place it on the page; bind its `DataCaptureContext` to a view-model property.

```xml
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"
             xmlns:viewModels="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage"
             x:DataType="viewModels:MainPageViewModel">
    <ContentPage.Content>
        <AbsoluteLayout>
            <scandit:DataCaptureView
                x:Name="dataCaptureView"
                AbsoluteLayout.LayoutBounds="0,0,1,1"
                AbsoluteLayout.LayoutFlags="All"
                DataCaptureContext="{Binding DataCaptureContext}" />
        </AbsoluteLayout>
    </ContentPage.Content>
</ContentPage>
```

> ⚠️ **`DataCaptureContext="{Binding DataCaptureContext}"` is mandatory.** Without this binding the frame source is never attached to the preview and the camera renders as a **black/blank screen** even though the code-behind compiles and the camera is started. The page's `BindingContext` must expose a `DataCaptureContext` property of type `Scandit.DataCapture.Core.Capture.DataCaptureContext`. Setting only `x:Name` does **not** wire the context — the binding is separate and required.

`DataCaptureView` (MAUI) exposes: the `DataCaptureContext` bindable property, `AddOverlay(IDataCaptureOverlay)` / `RemoveOverlay(...)`, `MapFrameQuadrilateralToView(Quadrilateral)`, and the inherited `HandlerChanged` event.

The view model exposes the context (injected from DI):

```csharp
public class MainPageViewModel(
    DataCaptureContext dataCaptureContext,
    ICameraService cameraService,
    ILabelCaptureService labelCaptureService,
    IMessageService messageService) : BaseViewModel
{
    public DataCaptureContext DataCaptureContext { get; } = dataCaptureContext;
    // ...overlay builders + lifecycle below...
}
```

## Step 4 — Create the LabelCaptureBasicOverlay after `HandlerChanged`

The overlay must be created **after** the MAUI handler attaches a native view. Subscribe to `dataCaptureView.HandlerChanged` in the page constructor and add the overlay there. Creating it earlier fails silently — there's no native view to attach to yet.

```csharp
using Scandit.DataCapture.Label.UI.Overlay;
using MyApp.ViewModels;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private LabelCaptureBasicOverlay? overlay;
    private readonly MainPageViewModel viewModel;

    public MainPage(MainPageViewModel viewModel)
    {
        this.viewModel = viewModel;
        this.InitializeComponent();
        this.BindingContext = viewModel;

        // Build the overlay only once the native view exists.
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = this.viewModel.BuildOverlay();
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();
        _ = this.viewModel.ResumeAsync();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        _ = this.viewModel.SleepAsync();
    }
}
```

> Use the single-arg `LabelCaptureBasicOverlay.Create(labelCapture)` in MAUI and attach via `dataCaptureView.AddOverlay(overlay)`. The two-arg `Create(labelCapture, dataCaptureView)` overload expects a **native** iOS/Android view, not the MAUI XAML control.

### Common LabelCaptureBasicOverlay members

| Member | Description |
|--------|-------------|
| `static Create(LabelCapture)` | Factory (use this in MAUI). |
| `Listener` | `ILabelCaptureBasicOverlayListener?` — custom brushes + tap callback. |
| `PredictedFieldBrush` / `CapturedFieldBrush` / `LabelBrush` | `Brush?` (get/set); static `Default*Brush` provide defaults. Set `LabelBrush = Brush.TransparentBrush` to hide the label outline (e.g. when pairing with the validation flow). |
| `SetBrushForField(Brush?, LabelField, CapturedLabel)` / `SetBrushForLabel(Brush?, CapturedLabel)` | Per-field / per-label brush override. |
| `Viewfinder` | `IViewfinder?` (get/set). |
| `ShouldShowScanAreaGuides` | `bool` — development only. |
| `Dispose()` | Releases native resources. |

## Step 5 — Handle captured labels

`OnSessionUpdated` (equivalently the `SessionUpdated` event) fires for **every processed frame** and runs on a **background thread**. Check `session.CapturedLabels`; when a label is present, read its fields by name, disable the mode to avoid re-capturing, and dispatch UI work to the main thread with `MainThread.BeginInvokeOnMainThread(...)`.

The idiomatic C# pattern is the event (wire it in the service or view model):

```csharp
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;

// after creating labelCapture:
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
    string? barcodeData = label.Fields.FirstOrDefault(f => f.Name == FIELD_BARCODE)?.Barcode?.Data;
    string? expiryDate  = label.Fields.FirstOrDefault(f => f.Name == FIELD_EXPIRY_DATE)?.Text;
    string? totalPrice  = label.Fields.FirstOrDefault(f => f.Name == FIELD_TOTAL_PRICE)?.Text;

    // Stop capturing the same label repeatedly.
    this.labelCapture.Enabled = false;

    MainThread.BeginInvokeOnMainThread(() =>
    {
        // Present barcodeData / expiryDate / totalPrice to the user.
    });
}
```

If you prefer the listener interface, implement `ILabelCaptureListener` with a **plain C# class** (no `NSObject` / `Java.Lang.Object` base in MAUI):

```csharp
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;

public class LabelCaptureListener : ILabelCaptureListener
{
    public void OnSessionUpdated(LabelCapture mode, LabelCaptureSession session, IFrameData data)
    {
        if (session.CapturedLabels.Count == 0) return;
        var label = session.CapturedLabels[0];
        // ...read fields, mode.Enabled = false, dispatch via MainThread.BeginInvokeOnMainThread...
    }

    public void OnObservationStarted(LabelCapture mode) { }
    public void OnObservationStopped(LabelCapture mode) { }
}

// In setup:
this.labelCapture.AddListener(new LabelCaptureListener());
```

> Use **either** `AddListener` **or** the `SessionUpdated` event for a given handler — both deliver the same callback; subscribing to both double-processes.

### Reading field values

`LabelField` exposes typed accessors — pick the one matching the field type:

| Accessor | Type | Use for |
|----------|------|---------|
| `field.Barcode?.Data` | `string?` | barcode fields (`field.Barcode` is a `Barcode?`) |
| `field.Text` | `string?` | text fields (prices, weight, custom text, and the raw date string) |
| `field.Date` | `LabelDate?` | structured date — `Year` / `Month` / `Day` (`int?`) and `DayString` / `MonthString` / `YearString` |

A convenient pattern for "barcode value, falling back to text" (also used by the official sample) is `field.Barcode?.Data ?? field.Text`. This matters for the validation flow, where a manually-typed barcode value comes back as `Text`.

When you don't want to hard-code field names — e.g. a prebuilt definition (`CreateVinLabelDefinition`, `CreatePriceCaptureDefinition`) whose internal field names you shouldn't guess — iterate `label.Fields` and switch on `field.Type` to pick the right accessor:

```csharp
foreach (LabelField field in label.Fields)
{
    string? value = field.Type switch
    {
        LabelFieldType.Barcode => field.Barcode?.Data,
        LabelFieldType.Text => field.Text,
        _ => null,
    };
    // field.Name identifies which field this is; value holds its captured content.
}
```

> Read captured values by the field's **`Type`** (or by the `Name` you passed to `.Build("...")`), never by guessing internal field-name strings.

Other `LabelField` members: `Name`, `Type` (`LabelFieldType.Barcode`/`Text`/`Unknown`), `State` (`LabelFieldState.Captured`/`Predicted`/`Unknown`), `Required` (`bool`), `PredictedLocation` (`Quadrilateral`). (`ValueType` is iOS-only — avoid in portable MAUI code.) `CapturedLabel` exposes `Fields`, `Name`, `Complete` (all required fields captured), and `TrackingId`. `LabelCaptureSession` exposes `CapturedLabels` (`IList<CapturedLabel>`), `FrameSequenceId` (`long`), `LastProcessedFrameId` (`int`).

## Step 6 — Camera lifecycle and permission

Drive the camera from the page's MAUI lifecycle, usually delegated to a view model's `ResumeAsync` / `SleepAsync`. Request `Permissions.Camera` in the resume path before turning the camera on. A tiny `ICameraService` over the injected `Camera` keeps things clean:

```csharp
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

internal sealed class CameraService : ICameraService
{
    private readonly Camera? camera;

    public CameraService(Camera camera, DataCaptureContext dataCaptureContext)
    {
        this.camera = camera;
        // The camera is off by default; bind it as the context's frame source once.
        if (this.camera != null)
        {
            dataCaptureContext.SetFrameSourceAsync(this.camera);
        }
    }

    public Task ResumeFrameSourceAsync() =>
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On) ?? Task.CompletedTask;

    public Task PauseFrameSourceAsync() =>
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off) ?? Task.CompletedTask;
}
```

```csharp
public override async Task ResumeAsync()
{
    var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
    if (status != PermissionStatus.Granted)
    {
        status = await Permissions.RequestAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            // Surface a message; do not start the camera.
            return;
        }
    }

    await cameraService.ResumeFrameSourceAsync();
    labelCaptureService.Enable();
}

public override async Task SleepAsync()
{
    await cameraService.PauseFrameSourceAsync();
    labelCaptureService.Disable();
}
```

> On iOS the OS shows the camera permission prompt automatically (driven by `NSCameraUsageDescription`); `Permissions.RequestAsync` ties into that. On Android `Permissions.Camera` triggers the runtime prompt and ensures the manifest permission is present.

## Step 7 — Provide feedback (optional)

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

1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.Label/` and read the latest **stable** version (skip `-beta`/`-preview`/`-rc`). Do not skip — versions from training data are stale and fail `dotnet restore` with `NU1103`.
2. Add the four `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.Barcode`, `Scandit.DataCapture.Label`), all pinned to that version. **No `Label.Maui`, no `label-text-models`.**
3. Set Android `SupportedOSPlatformVersion` to `24.0` (MAUI defaults to `21`, which fails the build) and iOS to `15.0`.
4. In `MauiProgram.cs`: call `ScanditLabelCapture.Initialize()` and chain `.UseScanditCore(c => c.AddDataCaptureView())`. **No `UseScanditBarcode()`, no manual init in `MainApplication`/`AppDelegate`.**
5. Add the `<scandit:DataCaptureView>` element (with `DataCaptureContext="{Binding DataCaptureContext}"`) and the `xmlns:scandit` namespace to the page.
6. iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. Android: rely on `Permissions.Camera` or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
7. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Troubleshooting

### Black / blank camera preview

**Cause:** The `<scandit:DataCaptureView>` does not have its `DataCaptureContext` bindable property set. **Fix:** Add `DataCaptureContext="{Binding DataCaptureContext}"` and make sure the page's `BindingContext` exposes a `DataCaptureContext` property. `x:Name` alone is not enough.

### Overlay never appears / no highlights

**Cause:** The overlay was created before `dataCaptureView.HandlerChanged` fired (no native view yet). **Fix:** Create `LabelCaptureBasicOverlay.Create(labelCapture)` inside the `HandlerChanged` handler and attach with `AddOverlay`.

### First `LabelCapture.Create(...)` crashes

**Cause:** `ScanditLabelCapture.Initialize()` was not called in `MauiProgram.CreateMauiApp()`. **Fix:** Add it before `MauiApp.CreateBuilder()` work that constructs Scandit types, alongside `.UseScanditCore(c => c.AddDataCaptureView())`.

### `dotnet restore` fails with `NU1103`

**Cause:** A guessed/stale version, or an attempt to reference a non-existent `Scandit.DataCapture.Label.Maui`. **Fix:** Use the version from the live NuGet page for the four real packages; there is no `Label.Maui`.

## Key rules

1. **Four NuGet packages** — `Core`, `Core.Maui`, `Barcode`, `Label`. **No `Label.Maui`, no `label-text-models`.** Fetch the version from NuGet; don't guess.
2. **Init = `ScanditLabelCapture.Initialize()` + `.UseScanditCore(c => c.AddDataCaptureView())`** in `MauiProgram.cs`. No `UseScanditLabel()`, no `UseScanditBarcode()`, no manual init in `MainApplication`/`AppDelegate`.
3. **No settings builder** — build each field with `Type.Builder()...Build("name")`, collect into `List<LabelFieldDefinition>`, `LabelDefinition.Create(name, fields)`, `LabelCaptureSettings.Create(new List<LabelDefinition> { def })`.
4. **`LabelCapture.Create(context, settings)`** — factory; the constructor is private.
5. **Symbologies are PascalCase** from `Scandit.DataCapture.Barcode.Data`; `SetSymbologies` takes an `IList<Symbology>`.
6. **`<scandit:DataCaptureView>` + `DataCaptureContext="{Binding DataCaptureContext}"`** — the binding is mandatory or the preview is black.
7. **Overlay after `HandlerChanged`** — `LabelCaptureBasicOverlay.Create(labelCapture)` then `dataCaptureView.AddOverlay(overlay)`.
8. **`OnSessionUpdated` runs on a background thread** — read fields by name, set `labelCapture.Enabled = false` after a capture, dispatch UI work via `MainThread.BeginInvokeOnMainThread(...)`.
9. **Listeners are plain C# classes** — no `NSObject` / `Java.Lang.Object` base.
10. **Read values via `LabelField`** — `Barcode?.Data`, `Text`, or `Date` (`LabelDate`), matching the field's declared name.
11. **Camera lifecycle in `OnAppearing`/`OnDisappearing`** (via `ResumeAsync`/`SleepAsync`); request `Permissions.Camera` before turning the camera on.
12. **Android `SupportedOSPlatformVersion` ≥ 24, iOS ≥ 15**; `NSCameraUsageDescription` in `Info.plist`.

## Advanced overlay (custom / AR views over labels)

For augmented-reality style use cases — showing a custom view anchored to a captured label or field (e.g. an "expires soon" badge over an expiry date) — use `LabelCaptureAdvancedOverlay` instead of the basic overlay. It is created like the basic overlay (`LabelCaptureAdvancedOverlay.Create(labelCapture)` in `HandlerChanged`, then `dataCaptureView.AddOverlay(...)`) and driven by an `ILabelCaptureAdvancedOverlayListener`.

> **MAUI caveat (important):** the advanced-overlay listener returns a **native platform view** — `Android.Views.View` on Android, `UIKit.UIView` on iOS — not a MAUI `View`. There is no cross-platform overload. So in a MAUI app you must implement the listener with the `partial`-class split per platform (under `Platforms/Android` / `Platforms/iOS`), or build a MAUI `View` and call `.ToPlatform(mauiContext)` to get the native view. This is the same pattern the MatrixScan AR overlays use in MAUI. The basic overlay (`LabelCaptureBasicOverlay`) needs none of this — prefer it unless you genuinely need custom views.

```csharp
using Scandit.DataCapture.Label.UI.Overlay;

// In HandlerChanged, alongside (or instead of) the basic overlay:
var advancedOverlay = LabelCaptureAdvancedOverlay.Create(labelCapture);
this.dataCaptureView.AddOverlay(advancedOverlay);
advancedOverlay.Listener = new MyAdvancedOverlayListener();

// Plain C# class implementing the listener. The View?/Anchor/PointWithUnit
// return values are platform-native — split per platform in MAUI.
public partial class MyAdvancedOverlayListener : ILabelCaptureAdvancedOverlayListener
{
    public Anchor AnchorForCapturedLabel(LabelCaptureAdvancedOverlay overlay, CapturedLabel label) => Anchor.Center;
    public Anchor AnchorForCapturedLabelField(LabelCaptureAdvancedOverlay overlay, LabelField field) => Anchor.BottomCenter;
    // ViewForCapturedLabel / ViewForCapturedLabelField / OffsetForCapturedLabel(Field)
    // return native views/offsets — implement in the per-platform partial.
}
```

The listener callbacks (`ViewForCapturedLabel`, `ViewForCapturedLabelField`, `AnchorForCapturedLabel(Field)`, `OffsetForCapturedLabel(Field)`) are documented on the Advanced Configurations page. **Do not claim these callbacks return a plain cross-platform MAUI `View`** — they return native `Android.Views.View` / `UIKit.UIView`, so the native view construction must be written per platform. Point the user to the [Advanced Configurations](https://docs.scandit.com/sdks/net/android/label-capture/advanced/) ([iOS](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/)) reference and fetch it before writing the per-platform view code — don't guess the native view construction.

## Adaptive Recognition — cloud fallback (Beta)

> ⚠️ **Beta.** The Adaptive Recognition Engine is in beta and may change. It must be enabled on your Scandit subscription — contact support@scandit.com. Do not enable it speculatively.

When the on-device model can't capture a field, Adaptive Recognition can fall back to a larger cloud-hosted model so the user doesn't have to type the value. It is turned on **per label definition** with a single property — no extra overlay or package:

```csharp
var labelDefinition = LabelDefinition.Create(LABEL_RETAIL_ITEM, fields);
labelDefinition.AdaptiveRecognitionMode = AdaptiveRecognitionMode.Auto; // default is Off
var settings = LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
```

`AdaptiveRecognitionMode` is an enum on `LabelDefinition` (`Off` is the default; `Auto` enables the cloud fallback). It pairs naturally with the Validation Flow (see `references/validation-flow.md`). Everything else in the integration stays the same.

## Receipt Scanning (Beta)

> ⚠️ **Beta.** Receipt Scanning requires the Adaptive Recognition Engine (beta) and must be enabled on your subscription — contact support@scandit.com.

Receipt Scanning extracts structured data from a whole receipt **in the cloud** (store info, payment totals, individual line items) and uses a **different integration pattern** from standard label capture:

- A `LabelCaptureAdaptiveRecognitionOverlay` (not the basic overlay), created in `HandlerChanged` and attached via `dataCaptureView.AddOverlay(...)`.
- An `ILabelCaptureAdaptiveRecognitionListener` whose recognized callback delivers a `ReceiptScanningResult` — store name/address/city, transaction date/time, pre-tax total, tax, total, loyalty number, and a list of `ReceiptScanningLineItem` (each with name, unit price, discount, quantity, total price).

Because this is a beta, cloud-only flow with platform-specific overlay shapes, **fetch the Advanced Configurations page before implementing it** and confirm the exact .NET listener method name and `ReceiptScanningResult` property casing against the API reference — the binding shapes are not duplicated here to avoid drift.

## Where to go next

- [Label Definitions (Android)](https://docs.scandit.com/sdks/net/android/label-capture/label-definitions/) · [Label Definitions (iOS)](https://docs.scandit.com/sdks/net/ios/label-capture/label-definitions/) — full catalogue of field types and how to tune value/anchor regexes.
- [Advanced Configurations (Android)](https://docs.scandit.com/sdks/net/android/label-capture/advanced/) · [iOS](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) — Validation Flow (see `references/validation-flow.md`), adaptive recognition, advanced overlay.
