# ID Capture — .NET for iOS Integration Guide

ID Capture extracts data from identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — by reading the MRZ (machine-readable zone), VIZ (visual inspection zone / printed text), and/or the PDF417 barcode on the back. You declare which documents you accept and which scanner to use, and the SDK returns a `CapturedId` with the holder's data.

The .NET binding differs from the native iOS (Swift), Android (Kotlin), and Flutter SDKs in several ways. The two that trip people up most: **`IdCaptureSettings` is configured by setting properties (object-initializer style), not a builder or a `supportedDocuments` bitmask**, and **verification has no `AamvaBarcodeVerifier` class — it's driven by settings flags**.

Examples below use C# and a `UIViewController`. The same APIs work in storyboards, XIBs, or programmatically-instantiated controllers — adapt ownership of `DataCaptureContext`, `Camera`, `IdCapture`, `DataCaptureView`, and the overlay to the project's existing structure.

> **Scene-based vs storyboard instantiation — match the constructor to the instantiation path.** The `dotnet new ios` template that ships with modern .NET-iOS is **scene-based**: no `Main.storyboard`, `AppDelegate` returns a `UISceneConfiguration`, and a `SceneDelegate.WillConnect` builds the window and sets `Window.RootViewController` programmatically. In that case the `UIViewController` must expose a **parameterless** constructor (`public ViewController() : base() { }`) and `SceneDelegate.WillConnect` calls `new ViewController()`. Do **not** call `new ViewController(IntPtr.Zero)`. If the project *is* storyboard-based (older Scandit samples follow this pattern — `UIMainStoryboardFile` in `Info.plist`, `customClass="ViewController"` in `Main.storyboard`), keep the `public ViewController(IntPtr handle) : base(handle) { }` constructor instead, since storyboard inflation invokes that ctor with a real native handle. **Symptom of the wrong choice: the app launches but shows a blank screen, no camera preview.**

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts the `DataCaptureView` as a XAML element and wires it through handlers, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.IdCapture/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.IdCapture with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.idcapture/index.json` (last entry without a pre-release suffix) before proceeding.

ID Capture's modern document/scanner API (`AcceptedDocuments`, `IdCaptureScanner`, `FullDocumentScanner`) requires **7.0+**, and the verification result model requires **8.0** — any current stable release supports it. If the project already pins an older Scandit major (6.x / 7.x), tell the user they should move to 8.x.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add **two** packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.IdCapture" Version="<step-0-version>" />
  </ItemGroup>
  ```
  There is **no separate Barcode package** — the PDF417/AAMVA barcode reader used for the back of driver's licenses is bundled in `Scandit.DataCapture.IdCapture`. Do **not** add any `*.Maui` package — those are MAUI-only.
- **`SupportedOSPlatformVersion` must be at least `15.0`** in the `.csproj` (matches the .NET iOS / MAUI template default and the Scandit iOS framework's minimum deployment target):
  ```xml
  <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
  ```
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- **Camera usage description in `Info.plist`:**
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan identity documents.</string>
  ```
  Without this key the app crashes on first camera access. iOS prompts the user for permission automatically the first time the camera is opened; there is no separate runtime-request API to call (unlike Android, there is no `CameraPermissionActivity`).
- **SDK initialization (Scandit 8.0+).** Initialize the Scandit DI container in `AppDelegate.FinishedLaunching` before any Scandit type is constructed. **Two** initializers are required — missing `ScanditIdCapture.Initialize()` crashes the first `IdCapture.Create(...)` call.

  ```csharp
  using Foundation;
  using Scandit.DataCapture.Core;
  using Scandit.DataCapture.ID;
  using UIKit;

  namespace MyApp;

  [Register("AppDelegate")]
  public class AppDelegate : UIResponder, IUIApplicationDelegate
  {
      [Export("window")]
      public UIWindow Window { get; set; } = null!;

      [Export("application:didFinishLaunchingWithOptions:")]
      public bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
      {
          ScanditCaptureCore.Initialize();
          ScanditIdCapture.Initialize();
          return true;
      }
  }
  ```

  If the project already has an `AppDelegate`, add the two `Initialize()` calls at the top of `FinishedLaunching` rather than creating a second delegate. **This step is only required on Scandit SDK 8.0+ — earlier majors (6.x, 7.x) self-initialized, so for those versions skip this entirely.** Note the initializer name: the NuGet package is `Scandit.DataCapture.IdCapture`, but the initializer/namespace are `ScanditIdCapture.Initialize()` / `using Scandit.DataCapture.ID;`.

### Project scaffolding (new projects only)

If a .NET iOS project already exists, skip this and go to the Interactive Document Configuration below.

**Recommended:** scaffold a buildable shell with the official template, then add ID Capture on top:

```bash
dotnet new ios -o MyApp
cd MyApp
```

Add the two Scandit packages from the bullets above, set `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>`, add `NSCameraUsageDescription` to `Info.plist`, and continue.

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
- **`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)`** — reads a single side from only the zones you enable. Use when you only need, say, the back PDF417 barcode of a US license, or only the passport MRZ. (See `references/advanced.md`.)
- **`MobileDocumentScanner(iso180135, ocr)`** — mobile driver's licenses (mDL). (See `references/advanced.md`.)

**Question C — Which fields do you need to read?** (full name, date of birth, expiry, document number, nationality, …) This drives what you pull off `CapturedId`, and informs whether anonymization can hide the rest (see `references/advanced.md`).

**Question D — Which `UIViewController` should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

this.dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

## Step 2 — Build the settings (accepted documents + scanner)

`IdCaptureSettings` is configured by **setting properties** — there is no builder and no `supportedDocuments` bitmask. Set `AcceptedDocuments` to the documents you accept and `Scanner` to an `IdCaptureScanner` wrapping a physical and/or mobile scanner.

```csharp
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

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
```

### Notes when generating the settings

- `AcceptedDocuments` is an `IList<IIdCaptureDocument>` — use a collection expression `[ … ]` or `new List<IIdCaptureDocument> { … }`. Add **only** the documents the user selected.
- Documents are `new`'d with an `IdCaptureRegion`: `new Passport(IdCaptureRegion.Any)`, `new DriverLicense(IdCaptureRegion.Us)`, etc. `IdCaptureRegion` values are PascalCase (`Any`, `Us`, `Uk`, `EuAndSchengen`, `Germany`, …). Do **not** use the Swift/Kotlin form.
- `Scanner` is **always** required: `new IdCaptureScanner(physicalDocument: …, mobileDocument: …)`. For a typical document scan use `physicalDocument: new FullDocumentScanner()` and `mobileDocument: null`.
- Optional rejection rules, verification flags, and anonymization are also set as properties here — see `references/advanced.md`.

## Step 3 — Create the IdCapture mode

`IdCapture` is created with a **static factory** that attaches the mode to the context. There is **no** public `new IdCapture(...)` and no `forDataCaptureContext`.

```csharp
this.idCapture = IdCapture.Create(this.dataCaptureContext, settings);
```

### IdCapture members

| Member | Description |
|--------|-------------|
| `static IdCapture Create(DataCaptureContext?, IdCaptureSettings)` | Factory — creates the mode and attaches it to the context. (Also `Create(IdCaptureSettings)`.) |
| `Enabled` | `bool` (get/set) — set `false` while a result dialog is shown to stop re-capturing; re-enable to scan again. |
| `static CameraSettings RecommendedCameraSettings` | Property — recommended camera settings for ID capture. |
| `ApplySettings(IdCaptureSettings)` | Apply new settings at runtime. |
| `AddListener(IIdCaptureListener)` / `RemoveListener(...)` | Register / remove a listener. |
| `Feedback` | `IdCaptureFeedback` (get/set) — sound / vibration. |
| `Reset()` | Reset capture state (e.g. before a new multi-side scan). |
| `Context` | `DataCaptureContext?` (get). |
| `Dispose()` | Releases native resources. |

## Step 4 — Set up the camera (you manage it; the view does not)

Get the default camera, **apply the recommended ID-capture settings to it**, and set it as the context's frame source. Keep a reference so you can switch it on/off across the lifecycle.

```csharp
using Scandit.DataCapture.Core.Source;

this.camera = Camera.GetDefaultCamera();
if (this.camera is null)
{
    throw new InvalidOperationException("ID Capture requires a camera.");
}

_ = this.camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings);
_ = this.dataCaptureContext.SetFrameSourceAsync(this.camera);
```

> Note: ID Capture applies `RecommendedCameraSettings` to the camera via `camera.ApplySettingsAsync(...)`. `RecommendedCameraSettings` is a **static property** on `IdCapture`.

The camera is off by default. You turn it on in `ViewWillAppear` and off in `ViewWillDisappear` (Step 7).

> **Keep `ViewDidLoad` synchronous — do not make it `async void`.** An `async void ViewDidLoad` returns control to UIKit at the first `await`, so `ViewWillAppear` can run before the mode/camera are constructed, touching `idCapture` (or the camera) before it has been assigned. Fire-and-forget the async camera calls with `_ =` instead of awaiting them inside `ViewDidLoad`.

## Step 5 — Visualize with DataCaptureView + IdCaptureOverlay

ID Capture uses the generic `DataCaptureView`. On iOS, `DataCaptureView.Create(context, CGRect frame)` takes the view's frame; the returned object **is** a `UIView`, so you add it to your controller's view yourself and add an `IdCaptureOverlay` so the document frame/viewfinder is drawn.

```csharp
using CoreGraphics;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.UI.Overlay;
using UIKit;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);

UIView platformView = this.dataCaptureView;
platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
this.View.AddSubview(this.dataCaptureView);

this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
this.overlay.IdLayoutStyle = IdLayoutStyle.Square;   // optional; Rounded is the default
```

> `DataCaptureView.Create(context, frame)` takes a `CGRect` on iOS (`this.View!.Bounds`, or `this.View?.Frame ?? CGRect.Empty`). The two-arg `IdCaptureOverlay.Create(idCapture, dataCaptureView)` auto-attaches the overlay to the view (so you do not also call `AddOverlay`). There is also a `Create(idCapture)` single-arg overload if you prefer to add it yourself.

### Common IdCaptureOverlay members

| Member | Description |
|--------|-------------|
| `static Create(IdCapture, DataCaptureView?)` / `Create(IdCapture)` | Factory. |
| `IdLayoutStyle` | `Rounded` (default) / `Square`. |
| `IdLayoutLineStyle` | `Bold` / `Light`. |
| `ShowTextHints` / `TextHintPosition` | Toggle/position the on-screen hints. |
| `SetFrontSideTextHint(string)` / `SetBackSideTextHint(string)` | Customize the hint text. |
| `CapturedBrush` / `LocalizedBrush` / `RejectedBrush` | `Brush` (get/set); static `Default*Brush` provide defaults. |
| `Dispose()` | Releases native resources. |

## Step 6 — Handle captured and rejected IDs

Implement `IIdCaptureListener`. **Both callbacks run on a background/arbitrary thread** — dispatch UI work to the main thread, and disable the mode while a result is displayed so the same document isn't captured repeatedly. A `UIViewController` is already an `NSObject`, so it can implement `IIdCaptureListener` directly (mirrors the official sample):

```csharp
using CoreFoundation;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using UIKit;

public partial class IdCaptureViewController : UIViewController, IIdCaptureListener
{
    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        // Read the fields you need (see "Reading field values" below).
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;

        // Stop capturing while we show the result.
        mode.Enabled = false;

        // Callback is on a background thread — dispatch to the main queue.
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // Present the data; re-enable mode.Enabled = true when the user dismisses it.
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
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // Show message; re-enable scanning afterwards.
        });
    }
}
```

Register / unregister it across the lifecycle (Step 7): `this.idCapture.AddListener(this);` / `RemoveListener(this)`.

> Dispatch to the main thread with `DispatchQueue.MainQueue.DispatchAsync(...)` (or `UIApplication.SharedApplication.InvokeOnMainThread(...)`) — **not** Android's `RunOnUiThread`.

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

For the richer zone-specific results (`capturedId.Mrz`, `capturedId.Viz`, `capturedId.Barcode`, `capturedId.MobileDocument`), the document images (`capturedId.Images`, each a `UIImage?`), and the verification outcome (`capturedId.VerificationResult`), see `references/advanced.md`.

> Always guard for nulls — a field that wasn't present on the scanned document is `null`. When formatting a date, use `DateResult.UtcDate` (a `DateTime`).

## Step 7 — Camera lifecycle (and the result alert)

Toggle the camera and the listener across the `UIViewController` lifecycle. The camera — not the view — is the lifecycle handle. iOS shows the camera permission prompt automatically the first time the camera starts (provided `NSCameraUsageDescription` is in `Info.plist`).

```csharp
using Scandit.DataCapture.Core.Source;

public override void ViewWillAppear(bool animated)
{
    base.ViewWillAppear(animated);

    this.idCapture.AddListener(this);
    this.idCapture.Enabled = true;

    // Switch the camera on (the camera starts asynchronously).
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

public override void ViewWillDisappear(bool animated)
{
    base.ViewWillDisappear(animated);

    this.idCapture.RemoveListener(this);
    this.idCapture.Enabled = false;

    // Switch the camera off to stop streaming frames.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}
```

A typical result presentation re-enables scanning when the alert is dismissed:

```csharp
private void ShowResult(string message)
{
    DispatchQueue.MainQueue.DispatchAsync(() =>
    {
        var alert = UIAlertController.Create(message, message: null, preferredStyle: UIAlertControllerStyle.Alert);
        alert.AddAction(UIAlertAction.Create("OK", UIAlertActionStyle.Default, _ =>
        {
            this.idCapture.Enabled = true;   // resume scanning
        }));
        this.PresentViewController(alert, animated: true, completionHandler: null);
    });
}
```

> `FrameSourceState.Standby` is a lighter alternative to `.Off` for short in-app navigation that keeps the camera warm; use `.Off` when leaving the scanning screen entirely or backgrounding.

## Step 8 — Provide feedback (optional)

ID Capture emits sound/vibration automatically, configurable via `idCapture.Feedback`.

```csharp
using Scandit.DataCapture.ID.Feedback;

// Default (sound + vibration):
this.idCapture.Feedback = IdCaptureFeedback.DefaultFeedback;
```

> `IdCaptureFeedback.DefaultFeedback` is a **static property**. The feedback object exposes `IdCaptured` and `IdRejected` slots (`Scandit.DataCapture.Core.Common.Feedback`). Audio plays only if the device is not muted.

## Setup checklist

After writing the integration code, show this checklist:

1. Add `Scandit.DataCapture.Core` and `Scandit.DataCapture.IdCapture` to the `.csproj` (use the version pinned in **Step 0** — do not guess). No separate Barcode package is needed.
2. Ensure `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `NSCameraUsageDescription` to `Info.plist` with a short user-facing description (iOS prompts automatically — no runtime-permission code).
4. Add `ScanditCaptureCore.Initialize()` **and `ScanditIdCapture.Initialize()`** to `AppDelegate.FinishedLaunching` (SDK 8.0+).
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Complete minimal example

```csharp
using CoreFoundation;
using CoreGraphics;
using UIKit;

using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using Scandit.DataCapture.ID.UI.Overlay;

namespace MyApp;

public partial class IdCaptureViewController : UIViewController, IIdCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private IdCapture idCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private IdCaptureOverlay overlay = null!;

    // Storyboard/XIB inflation passes a real native handle here. For scene-based /
    // programmatic instantiation, add a parameterless `public IdCaptureViewController() : base() { }`
    // instead and construct it with `new IdCaptureViewController()` in SceneDelegate.
    public IdCaptureViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // Camera (you manage it — the view does not).
        this.camera = Camera.GetDefaultCamera();
        if (this.camera is not null)
        {
            _ = this.camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings);
            _ = this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        // Settings: accepted documents + scanner.
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

        this.idCapture = IdCapture.Create(this.dataCaptureContext, settings);

        // Host the preview.
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
        this.overlay.IdLayoutStyle = IdLayoutStyle.Square;
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.idCapture.AddListener(this);
        this.idCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.idCapture.RemoveListener(this);
        this.idCapture.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;
        DateResult? dateOfExpiry = capturedId.DateOfExpiry;

        mode.Enabled = false;
        this.ShowResult($"{fullName}");
        // Present fullName / dateOfBirth?.UtcDate / documentNumber / dateOfExpiry?.UtcDate.
    }

    public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
    {
        mode.Enabled = false;
        this.ShowResult($"Rejected: {reason}");
    }

    private void ShowResult(string message)
    {
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            var alert = UIAlertController.Create(message, message: null, preferredStyle: UIAlertControllerStyle.Alert);
            alert.AddAction(UIAlertAction.Create("OK", UIAlertActionStyle.Default, _ => this.idCapture.Enabled = true));
            this.PresentViewController(alert, animated: true, completionHandler: null);
        });
    }
}
```

## Co-existence with Barcode Capture

`IdCapture` and `BarcodeCapture` can run **together on one `DataCaptureContext`** — one context, one `DataCaptureView`, one camera. A common case is an airport screen that reads a boarding-pass PDF417 barcode **and** a passport/ID at the same time. This example uses a **separate `BarcodeCapture` mode**, so add the **`Scandit.DataCapture.Barcode`** NuGet package alongside `Core` + `IdCapture` (verified by build). The base ID Capture flow doesn't need it — `IdCapture` reads the ID's own barcode internally; a standalone `BarcodeCapture` mode for the boarding pass is what pulls in the Barcode package.

On .NET each mode is attached to the context by its static factory: `IdCapture.Create(context, settings)` **and** `BarcodeCapture.Create(context, settings)` (these are the .NET equivalent of `addMode` — there is no public `new IdCapture(...)` and no `setMode`). Both factories take the **same** `DataCaptureContext`, so both modes stay attached; the native layer runs them together. Give each mode its own listener and toggle each independently with `mode.Enabled` — do **not** create a second context or remove one mode to add the other.

```csharp
// ID Capture mode (passport / ID)
var idSettings = new IdCaptureSettings
{
    AcceptedDocuments = { new Passport(IdCaptureRegion.Any) },
    Scanner = new IdCaptureScanner(physicalDocument: new FullDocumentScanner(), mobileDocument: null),
};
this.idCapture = IdCapture.Create(this.dataCaptureContext, idSettings); // attaches to context
this.idCapture.IdCaptured += OnIdCaptured;
this.idCapture.IdRejected += OnIdRejected;

// Barcode Capture mode (IATA boarding pass = PDF417), same context
var bcSettings = BarcodeCaptureSettings.Create();
bcSettings.EnableSymbology(Symbology.Pdf417, true);
this.barcodeCapture = BarcodeCapture.Create(this.dataCaptureContext, bcSettings); // attaches to same context
this.barcodeCapture.BarcodeScanned += (sender, args) =>
{
    Barcode? barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode != null) { /* ... */ }
};

// Both can be enabled at once — they run together.
this.idCapture.Enabled = true;
this.barcodeCapture.Enabled = true;
```

## Key rules

1. **One context per scanning surface** — construct `DataCaptureContext.ForLicenseKey(key)` once and reuse it.
2. **No settings builder, no bitmask** — `new IdCaptureSettings { AcceptedDocuments = [ … ], Scanner = new IdCaptureScanner(physicalDocument: …, mobileDocument: …) }`.
3. **Documents are `new`'d with an `IdCaptureRegion`** (`new Passport(IdCaptureRegion.Any)`); regions are PascalCase.
4. **`IdCapture.Create(...)`** — factory; the constructor is private.
5. **Two NuGet packages** — `Core`, `IdCapture`. No Barcode package.
6. **Two initializers** — `ScanditCaptureCore.Initialize()`, `ScanditIdCapture.Initialize()` in `AppDelegate.FinishedLaunching` (SDK 8.0+).
7. **You manage the camera** — `Camera.GetDefaultCamera()`, `camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Off)`. `RecommendedCameraSettings` is a static property.
8. **`DataCaptureView.Create(context, this.View!.Bounds)` + `this.View.AddSubview(view)` + `IdCaptureOverlay.Create(idCapture, dataCaptureView)`** — the view takes a `CGRect` and you add it yourself; the two-arg overlay factory auto-attaches.
9. **Handle both `OnIdCaptured` and `OnIdRejected`**; both run on a background thread — dispatch UI work with `DispatchQueue.MainQueue.DispatchAsync` and set `idCapture.Enabled = false` while a result is shown.
10. **Read values from `CapturedId`** — top-level `FullName` / `DateOfBirth` (a `DateResult`) / `DocumentNumber` / etc.
11. **`NSCameraUsageDescription` in `Info.plist`** — required; iOS prompts automatically. No `CameraPermissionActivity`.
12. **`SupportedOSPlatformVersion` ≥ 15.0** is required for the build to succeed.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/id-capture/advanced/) — scanner selection, rejection rules, verification, anonymization, the rich result model (see `references/advanced.md`).
