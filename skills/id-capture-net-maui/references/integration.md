# ID Capture — .NET MAUI Integration Guide

ID Capture extracts data from identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — by reading the MRZ (machine-readable zone), VIZ (visual inspection zone / printed text), and/or the PDF417 barcode on the back. You declare which documents you accept and which scanner to use, and the SDK returns a `CapturedId` with the holder's data.

On .NET MAUI you combine the cross-platform `Scandit.DataCapture.Core` / `Scandit.DataCapture.IdCapture` APIs (a `DataCaptureContext`, a `Camera`, an `IdCapture` mode, the listener / `IdCaptured` event) with two MAUI-specific pieces: the generic **`<scandit:DataCaptureView>`** XAML control from `Scandit.DataCapture.Core.UI.Maui`, and an **`IdCaptureOverlay` created after the view's platform handler has attached** (`HandlerChanged`).

Two things about the .NET binding trip people up most: **`IdCaptureSettings` is configured by setting properties (object-initializer style), not a builder or a `supportedDocuments` bitmask**, and **verification has no `AamvaBarcodeVerifier` class — it's driven by settings flags**. And one MAUI-specific surprise: **`ScanditIdCapture.Initialize()` is called from the platform entry points, not `MauiProgram.cs`** (unlike Label Capture MAUI).

The examples below follow the structure of the official Scandit MAUI `IdCaptureSimpleSample`: a `MainPage` (`ContentPage`) wired to a `MainPageViewModel` via `BindingContext`, with a small singleton `DataCaptureManager` owning the SDK objects (`DataCaptureContext`, `Camera`, `IdCapture`). You can collapse this into a single `ContentPage.xaml.cs` for very small apps — the underlying SDK calls are the same.

> **Not a MAUI project?** If `<UseMaui>true</UseMaui>` is missing from the `.csproj`, switch to `id-capture-net-android` (for `net*-android`) or `id-capture-net-ios` (for `net*-ios`). Those skills host the preview through a native `Activity` / `UIViewController`, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.IdCapture/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for all three packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `NU1103` / `Unable to find package … with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.idcapture/index.json` (last entry without a pre-release suffix) before proceeding.

ID Capture's modern document/scanner API (`AcceptedDocuments`, `IdCaptureScanner`, `FullDocumentScanner`) requires **8.0+**, and the verification result model requires **8.0** — any current stable release supports it in MAUI. If the project already pins an older Scandit major (6.x / 7.x), tell the user they should move to 8.x.

### Other prerequisites

- Add **three** NuGet packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.IdCapture" Version="<step-0-version>" />
  </ItemGroup>
  ```
  - `Core.Maui` provides the `<scandit:DataCaptureView>` XAML control and the `UseScanditCore` builder extension (plus the optional `AddDataCaptureContext` / `AddCamera` DI helpers).
  - `IdCapture` is the mode plus the bundled PDF417/AAMVA barcode reader used for the back of driver's licenses — **there is no separate `Scandit.DataCapture.Barcode` package** for ID Capture.
  - **There is NO `Scandit.DataCapture.IdCapture.Maui` package** — ID Capture has no MAUI-specific assembly. Do not add one.
- A `<UseMaui>true</UseMaui>` project targeting at least one of `net10.0-android` / `net10.0-ios` (adjust the TFM to the project's .NET version).
- **`SupportedOSPlatformVersion`** — iOS must be ≥ `15.0` (the Scandit iOS framework minimum) and **Android must be ≥ `24`**. The MAUI template defaults Android to `21`, which is below Scandit's Android AAR minimum and fails the build with `uses-sdk:minSdkVersion 21 cannot be smaller than version 24 declared in library`. Set both:
  ```xml
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'ios'">15.0</SupportedOSPlatformVersion>
  <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">24.0</SupportedOSPlatformVersion>
  ```
- **Camera permission / platform config:**
  - **iOS**: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist` (and a matching `MinimumOSVersion` of `15.0`). Without it the app crashes the moment the camera starts.
    ```xml
    <key>NSCameraUsageDescription</key>
    <string>Used to scan documents</string>
    <key>MinimumOSVersion</key>
    <string>15.0</string>
    ```
  - **Android**: `Permissions.Camera` (requested at runtime, Step 6) makes MAUI add `android.permission.CAMERA`; you can also add it explicitly to `Platforms/Android/AndroidManifest.xml`.
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.

## Step 1 — Initialize the SDK (platform entry points + MauiProgram)

This is the **most MAUI-specific step and the one most often gotten wrong** — and it differs from Label Capture MAUI. ID Capture's `Initialize()` lives in a per-TFM platform assembly, so you call it from the **platform entry points**, while core init and the `DataCaptureView` handler are registered in `MauiProgram.cs`.

**`Platforms/Android/MainApplication.cs`** — call `ScanditIdCapture.Initialize()` in `OnCreate()` **before** `base.OnCreate()`:

```csharp
using Android.App;
using Android.Runtime;
using Scandit.DataCapture.ID;

namespace MyApp;

[Application]
public class MainApplication(IntPtr handle, JniHandleOwnership ownership) : MauiApplication(handle, ownership)
{
    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();

    public override void OnCreate()
    {
        ScanditIdCapture.Initialize();
        base.OnCreate();
    }
}
```

**`Platforms/iOS/AppDelegate.cs`** — call `ScanditIdCapture.Initialize()` in `FinishedLaunching` **before** `base.FinishedLaunching(...)`:

```csharp
using Foundation;
using Scandit.DataCapture.ID;
using UIKit;

namespace MyApp;

[Register("AppDelegate")]
public class AppDelegate : MauiUIApplicationDelegate
{
    public override bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
    {
        ScanditIdCapture.Initialize();
        return base.FinishedLaunching(application, launchOptions);
    }

    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
```

**`MauiProgram.cs`** — chain `.UseScanditCore(configure => configure.AddDataCaptureView())` (this calls `ScanditCaptureCore.Initialize()` and registers the `DataCaptureView` MAUI handler):

```csharp
using Scandit.DataCapture.Core; // UseScanditCore

namespace MyApp;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>()
               .ConfigureFonts(fonts => fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular"))
               // Registers the DataCaptureView handler AND calls ScanditCaptureCore.Initialize().
               .UseScanditCore(configure => configure.AddDataCaptureView());

        return builder.Build();
    }
}
```

> **Key init rules:**
> - **`ScanditIdCapture.Initialize()` goes in the platform entry points** (`MainApplication.OnCreate` on Android, `AppDelegate.FinishedLaunching` on iOS), **before** the `base.` call. **Do NOT** call it in `MauiProgram.cs` — that's the Label Capture pattern, and there is **no `UseScanditIdCapture()`** extension.
> - **`.UseScanditCore(c => c.AddDataCaptureView())` in `MauiProgram.cs` handles core init + the view handler.** Don't also call `ScanditCaptureCore.Initialize()` manually.
> - The MAUI `MainApplication` / `AppDelegate` derive from `MauiApplication` / `MauiUIApplicationDelegate` and forward to `MauiProgram.CreateMauiApp()` — keep that, just add the `Initialize()` line.

## Interactive Document Configuration

Before writing any code, walk the user through what they're scanning. Ask one question at a time.

**Question A — Which documents do you need to accept?** Present this list and ask which apply:
- `Passport` — passport booklets (MRZ)
- `DriverLicense` — driver's licenses (front VIZ + back PDF417 barcode)
- `IdCard` — national / regional ID cards
- `ResidencePermit` — residence permits
- `HealthInsuranceCard` — health-insurance cards
- `VisaIcao` — ICAO visas
- `RegionSpecific` — special document subtypes (e.g. a US Global Entry card) selected via `RegionSpecificSubtype`

Each takes an `IdCaptureRegion` (e.g. `IdCaptureRegion.Any`, `IdCaptureRegion.Us`, `IdCaptureRegion.EuAndSchengen`). Recommend the narrowest region the use case allows — it's faster and more accurate than `Any`.

**Question B — Which scanner?**
- **`FullDocumentScanner()`** — reads front and back automatically. The right default for most ID/DL use cases.
- **`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)`** — reads a single side from only the zones you enable. (See `references/advanced.md`.)
- **`MobileDocumentScanner(iso180135, ocr)`** — mobile driver's licenses (mDL). (See `references/advanced.md`.)

**Question C — Which fields do you need to read?** (full name, date of birth, expiry, document number, nationality, …) This drives what you pull off `CapturedId`, and informs whether anonymization can hide the rest (see `references/advanced.md`).

**Question D — Which page/files should the integration go in?** Then write the code directly into those files. Do not just show it in chat.

## Step 2 — Own the SDK objects (DataCaptureManager singleton)

A clean MAUI shape is a small singleton that builds the `DataCaptureContext`, the `Camera`, the `IdCaptureSettings`, and the `IdCapture` mode once. (This mirrors the official sample; for a DI alternative see the note at the end of this step.)

```csharp
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

namespace MyApp.Models;

public class DataCaptureManager
{
    // Your Scandit License key is available via your Scandit SDK web account.
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private static readonly Lazy<DataCaptureManager> instance =
        new(() => new DataCaptureManager(), LazyThreadSafetyMode.PublicationOnly);

    public static DataCaptureManager Instance => instance.Value;

    public DataCaptureContext DataCaptureContext { get; }
    public Camera? CurrentCamera { get; } = Camera.GetCamera(CameraPosition.WorldFacing);
    public IdCapture IdCapture { get; }

    private DataCaptureManager()
    {
        // Apply the recommended ID-capture settings to the camera (it is off by default).
        this.CurrentCamera?.ApplySettingsAsync(IdCapture.RecommendedCameraSettings);

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);
        this.DataCaptureContext.SetFrameSourceAsync(this.CurrentCamera);

        var settings = new IdCaptureSettings
        {
            AcceptedDocuments =
            [
                new Passport(IdCaptureRegion.Any),
                new DriverLicense(IdCaptureRegion.Any),
                new IdCard(IdCaptureRegion.Any),
            ],
            Scanner = new IdCaptureScanner(
                physicalDocument: new FullDocumentScanner(),
                mobileDocument: null),
        };

        // IdCapture.Create attaches the mode to the passed DataCaptureContext.
        this.IdCapture = IdCapture.Create(this.DataCaptureContext, settings);
    }
}
```

### Notes when generating the settings

- `AcceptedDocuments` is an `IList<IIdCaptureDocument>` — use a collection expression `[ … ]` or `new List<IIdCaptureDocument> { … }`. Add **only** the documents the user selected.
- Documents are `new`'d with an `IdCaptureRegion`: `new Passport(IdCaptureRegion.Any)`, `new DriverLicense(IdCaptureRegion.Us)`, etc. `IdCaptureRegion` values are PascalCase (`Any`, `Us`, `Uk`, `EuAndSchengen`, `Germany`, …). Do **not** use the Swift/Kotlin style.
- `Scanner` is **always** required: `new IdCaptureScanner(physicalDocument: …, mobileDocument: …)`. For a typical document scan use `physicalDocument: new FullDocumentScanner()` and `mobileDocument: null`.
- `IdCapture.Create(context, settings)` is a **static factory** — the constructor is private and there is no `forDataCaptureContext`.
- `RecommendedCameraSettings` is a **static property** on `IdCapture`; apply it to the camera with `camera.ApplySettingsAsync(...)`.
- Optional rejection rules, verification flags, and anonymization are also set as properties on `IdCaptureSettings` — see `references/advanced.md`.

> **DI alternative.** Instead of the singleton you can register the context/camera through DI in `MauiProgram.cs` (from `Core.Maui`): `builder.Services.AddDataCaptureContext(SCANDIT_LICENSE_KEY);` and `builder.Services.AddCamera(c => { c.Position = CameraPosition.WorldFacing; c.Settings = IdCapture.RecommendedCameraSettings; });`, then inject `DataCaptureContext` / `Camera` into a service or view model. Either approach works; the singleton matches the official ID Capture sample.

## Step 3 — Expose the context (and mode) on a view model

The page's `BindingContext` must expose a `DataCaptureContext` property so the XAML binding can wire the preview. Implement `IIdCaptureListener` on the view model (a **plain C# class** — no `NSObject` / `Java.Lang.Object` base in MAUI).

```csharp
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using MyApp.Models;

namespace MyApp.ViewModels;

public class MainPageViewModel : IIdCaptureListener
{
    private readonly DataCaptureManager model = DataCaptureManager.Instance;

    public DataCaptureContext DataCaptureContext => this.model.DataCaptureContext;
    public IdCapture IdCapture => this.model.IdCapture;

    public MainPageViewModel()
    {
        // Start listening for ID Capture events.
        this.IdCapture.AddListener(this);
        this.IdCapture.Enabled = true;
    }

    // OnIdCaptured / OnIdRejected + lifecycle below (Steps 5 & 6).
}
```

## Step 4 — Add the DataCaptureView in XAML and the overlay in `HandlerChanged`

ID Capture uses the generic `<scandit:DataCaptureView>` (not a dedicated ID view). Add the XAML namespace and place it on the page; bind its `DataCaptureContext` to the view-model property.

```xml
<?xml version="1.0" encoding="utf-8" ?>
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage">
    <ContentPage.BindingContext>
        <vm:MainPageViewModel x:Name="viewModel" />
    </ContentPage.BindingContext>
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

> ⚠️ **`DataCaptureContext="{Binding DataCaptureContext}"` is mandatory.** Without this binding the frame source is never attached to the preview and the camera renders as a **black/blank screen** even though the code-behind compiles and the camera is started. Setting only `x:Name` does **not** wire the context.

The overlay must be created **after** the MAUI handler attaches a native view. Subscribe to `dataCaptureView.HandlerChanged` in the page constructor and add the overlay there with the **single-arg** factory:

```csharp
using Scandit.DataCapture.ID.UI.Overlay;
using MyApp.ViewModels;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private IdCaptureOverlay? overlay;

    public MainPage()
    {
        this.InitializeComponent();

        // Build the overlay only once the native view exists.
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = IdCaptureOverlay.Create(this.viewModel.IdCapture);
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

> Use the **single-arg** `IdCaptureOverlay.Create(idCapture)` in MAUI and attach via `dataCaptureView.AddOverlay(overlay)`. The two-arg `Create(idCapture, dataCaptureView)` overload expects a **native** iOS/Android view, not the MAUI XAML control. Optionally set `overlay.IdLayoutStyle = IdLayoutStyle.Square` (default is `Rounded`).

## Step 5 — Handle captured and rejected IDs

Implement `IIdCaptureListener` (or subscribe to the `IdCaptured` / `IdRejected` events). **Both callbacks run on a background/arbitrary thread** — set `idCapture.Enabled = false` while a result is displayed (so the same document isn't captured repeatedly), and dispatch UI work to the main thread.

```csharp
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
{
    // Read the fields you need (see "Reading field values" below).
    string? fullName = capturedId.FullName;
    DateResult? dateOfBirth = capturedId.DateOfBirth;
    string? documentNumber = capturedId.DocumentNumber;
    DateResult? dateOfExpiry = capturedId.DateOfExpiry;

    // Stop capturing while we show the result.
    mode.Enabled = false;

    MainThread.BeginInvokeOnMainThread(async () =>
    {
        await Application.Current!.Windows[0].Page!.DisplayAlert(
            "Document",
            $"{fullName}\nDOB: {dateOfBirth?.LocalDate:d}\nDoc #: {documentNumber}",
            "OK");

        // Re-enable scanning once the user dismisses the result.
        mode.Enabled = true;
    });
}

public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
{
    string message = reason switch
    {
        RejectionReason.NotAcceptedDocumentType => "Document not supported. Try another document.",
        RejectionReason.Timeout => "Couldn't read the document. Please try again.",
        _ => $"Document capture was rejected. Reason={reason}.",
    };

    mode.Enabled = false;
    MainThread.BeginInvokeOnMainThread(async () =>
    {
        await Application.Current!.Windows[0].Page!.DisplayAlert("Scandit", message, "OK");
        mode.Enabled = true;
    });
}
```

If you prefer events instead of the interface:

```csharp
this.IdCapture.IdCaptured += (sender, args) => { CapturedId id = args.CapturedId; /* ... */ };
this.IdCapture.IdRejected += (sender, args) => { RejectionReason reason = args.Reason; /* ... */ };
```

> Use **either** `AddListener` **or** the events for a given concern — both deliver the same callback; subscribing to both double-processes. The dispatch helper can be `MainThread.BeginInvokeOnMainThread(...)`, `MainThread.InvokeOnMainThreadAsync(...)`, or `Application.Current.Dispatcher.DispatchAsync(...)` — **not** Android's `RunOnUiThread` or iOS's `DispatchQueue.MainQueue`.

### Reading field values

`CapturedId` exposes the common holder fields at the top level, regardless of which zone they came from:

| Accessor | Type | Notes |
|----------|------|-------|
| `capturedId.FullName` / `FirstName` / `LastName` | `string?` | |
| `capturedId.DateOfBirth` / `DateOfExpiry` / `DateOfIssue` | `DateResult?` | `.Day` / `.Month` / `.Year` (`int`), `.UtcDate` / `.LocalDate` (`DateTime`) |
| `capturedId.DocumentNumber` / `DocumentAdditionalNumber` | `string?` | |
| `capturedId.Nationality` / `NationalityISO` | `string?` | |
| `capturedId.Sex` / `SexType` | `string?` / `Sex` enum | |
| `capturedId.Age` / `Expired` | `int?` / `bool?` | |
| `capturedId.Address` | `string?` | |
| `capturedId.Document?.DocumentType` | `IdCaptureDocumentType` | which document was recognized (`Passport`, `DriverLicense`, …) |

For the richer zone-specific results (`capturedId.Mrz`, `capturedId.Viz`, `capturedId.Barcode`, `capturedId.MobileDocument`), the document images (`capturedId.Images` — platform-typed, see `references/advanced.md`), and the verification outcome (`capturedId.VerificationResult`), see `references/advanced.md`.

> Always guard for nulls — a field that wasn't present on the scanned document is `null`. When formatting a date, use `DateResult.LocalDate` / `.UtcDate` (a `DateTime`), not the raw object.

## Step 6 — Camera lifecycle and permission

Drive the camera from the page's MAUI lifecycle (`OnAppearing` / `OnDisappearing`), usually delegated to the view model's `ResumeAsync` / `SleepAsync`. Request `Permissions.Camera` in the resume path before turning the camera on.

```csharp
using Scandit.DataCapture.Core.Source;

public async Task ResumeAsync()
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

    if (this.model.CurrentCamera is not null)
    {
        await this.model.CurrentCamera.SwitchToDesiredStateAsync(FrameSourceState.On);
    }
}

public async Task SleepAsync()
{
    if (this.model.CurrentCamera is not null)
    {
        await this.model.CurrentCamera.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }
}
```

> On iOS the OS shows the camera permission prompt automatically (driven by `NSCameraUsageDescription`); `Permissions.RequestAsync` ties into that. On Android `Permissions.Camera` triggers the runtime prompt and ensures the manifest permission is present. The camera is the lifecycle handle — switch it `On` in the resume path and `Off` on disappear.

## Step 7 — Provide feedback (optional)

ID Capture emits sound/vibration automatically on a capture, configurable via `idCapture.Feedback`.

```csharp
using Scandit.DataCapture.ID.Feedback;

// Default (sound + vibration):
this.IdCapture.Feedback = IdCaptureFeedback.DefaultFeedback;
```

> `IdCaptureFeedback.DefaultFeedback` is a **static property**. The feedback object exposes `IdCaptured` and `IdRejected` slots (`Scandit.DataCapture.Core.Common.Feedback`). Audio plays only if the device is not muted.

## Setup checklist

After writing the integration code, show this checklist:

1. **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.IdCapture/` and read the latest **stable** version (skip `-beta`/`-preview`/`-rc`). Do not skip — versions from training data are stale and fail `dotnet restore` with `NU1103`.
2. Add the three `<PackageReference>` entries (`Scandit.DataCapture.Core`, `Scandit.DataCapture.Core.Maui`, `Scandit.DataCapture.IdCapture`), all pinned to that version. **No `IdCapture.Maui`, no separate Barcode package.**
3. Set Android `SupportedOSPlatformVersion` to `24.0` (MAUI defaults to `21`, which fails the build) and iOS to `15.0`.
4. Add `ScanditIdCapture.Initialize()` to `Platforms/Android/MainApplication.OnCreate()` (before `base.OnCreate()`) **and** `Platforms/iOS/AppDelegate.FinishedLaunching` (before `base.FinishedLaunching(...)`).
5. In `MauiProgram.cs`, chain `.UseScanditCore(c => c.AddDataCaptureView())`. **No `UseScanditIdCapture()`, no `ScanditIdCapture.Initialize()` here.**
6. Add the `<scandit:DataCaptureView>` element (with `DataCaptureContext="{Binding DataCaptureContext}"`) and the `xmlns:scandit` namespace to the page; create `IdCaptureOverlay.Create(idCapture)` in `HandlerChanged` and attach with `AddOverlay`.
7. iOS: add `NSCameraUsageDescription` to `Platforms/iOS/Info.plist`. Android: rely on `Permissions.Camera` or add `<uses-permission android:name="android.permission.CAMERA" />` to `Platforms/Android/AndroidManifest.xml`.
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Troubleshooting

### Black / blank camera preview

**Cause:** The `<scandit:DataCaptureView>` does not have its `DataCaptureContext` bindable property set. **Fix:** Add `DataCaptureContext="{Binding DataCaptureContext}"` and make sure the page's `BindingContext` exposes a `DataCaptureContext` property. `x:Name` alone is not enough.

### Overlay / viewfinder never appears

**Cause:** The overlay was created before `dataCaptureView.HandlerChanged` fired (no native view yet), or the two-arg `Create(idCapture, dataCaptureView)` overload was used with the MAUI control. **Fix:** Create `IdCaptureOverlay.Create(idCapture)` (single-arg) inside the `HandlerChanged` handler and attach with `AddOverlay`.

### First `IdCapture.Create(...)` crashes / "not initialized"

**Cause:** `ScanditIdCapture.Initialize()` was not called in the platform entry points. **Fix:** Add it to `MainApplication.OnCreate()` (Android) and `AppDelegate.FinishedLaunching` (iOS), before the `base.` call. Don't put it in `MauiProgram.cs`.

### `dotnet restore` fails with `NU1103`

**Cause:** A guessed/stale version, or an attempt to reference a non-existent `Scandit.DataCapture.IdCapture.Maui` / `Scandit.DataCapture.Barcode`. **Fix:** Use the version from the live NuGet page for the three real packages.

### Build fails with `minSdkVersion 21 cannot be smaller than version 24`

**Cause:** The MAUI template's default Android `SupportedOSPlatformVersion` (21) is below Scandit's AAR minimum. **Fix:** Set it to `24.0`.

## Key rules

1. **Three NuGet packages** — `Core`, `Core.Maui`, `IdCapture`. **No `IdCapture.Maui`, no Barcode package.** Fetch the version from NuGet; don't guess.
2. **Init = `ScanditIdCapture.Initialize()` in the platform entry points** (`MainApplication.OnCreate` / `AppDelegate.FinishedLaunching`) **+ `.UseScanditCore(c => c.AddDataCaptureView())`** in `MauiProgram.cs`. No `UseScanditIdCapture()`, no `Initialize()` in `MauiProgram` (that's the Label Capture pattern).
3. **No settings builder, no bitmask** — `new IdCaptureSettings { AcceptedDocuments = [ … ], Scanner = new IdCaptureScanner(physicalDocument: …, mobileDocument: …) }`.
4. **Documents are `new`'d with an `IdCaptureRegion`** (`new Passport(IdCaptureRegion.Any)`); regions are PascalCase.
5. **`IdCapture.Create(...)`** — factory; the constructor is private.
6. **You manage the camera** — `Camera.GetCamera(...)` / `GetDefaultCamera()`, `camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Off)`. `RecommendedCameraSettings` is a static property.
7. **`<scandit:DataCaptureView>` + `DataCaptureContext="{Binding DataCaptureContext}"`** — the binding is mandatory or the preview is black.
8. **Overlay after `HandlerChanged`** — single-arg `IdCaptureOverlay.Create(idCapture)` then `dataCaptureView.AddOverlay(overlay)`.
9. **Handle both `OnIdCaptured` and `OnIdRejected`**; both run on a background thread — set `idCapture.Enabled = false` while a result is shown and dispatch UI via `MainThread.BeginInvokeOnMainThread(...)`.
10. **Listeners are plain C# classes** — no `NSObject` / `Java.Lang.Object` base.
11. **Read values from `CapturedId`** — top-level `FullName` / `DateOfBirth` (a `DateResult`) / `DocumentNumber` / etc.
12. **Android `SupportedOSPlatformVersion` ≥ 24, iOS ≥ 15**; `NSCameraUsageDescription` in `Info.plist`.

## Where to go next

- [Advanced Configurations (Android)](https://docs.scandit.com/sdks/net/android/id-capture/advanced/) · [iOS](https://docs.scandit.com/sdks/net/ios/id-capture/advanced/) — scanner selection, rejection rules, verification, anonymization, the rich result model (see `references/advanced.md`).
