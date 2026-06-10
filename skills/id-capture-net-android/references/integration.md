# ID Capture — .NET for Android Integration Guide

ID Capture extracts data from identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — by reading the MRZ (machine-readable zone), VIZ (visual inspection zone / printed text), and/or the PDF417 barcode on the back. You declare which documents you accept and which scanner to use, and the SDK returns a `CapturedId` with the holder's data.

The .NET binding differs from the native Android (Kotlin), iOS, and Flutter SDKs in several ways. The two that trip people up most: **`IdCaptureSettings` is configured by setting properties (object-initializer style), not a builder or a `supportedDocuments` bitmask**, and **verification has no `AamvaBarcodeVerifier` class — it's driven by settings flags**.

Examples below use C# and an `AppCompatActivity`. The same APIs work in a Fragment — adapt ownership of `DataCaptureContext`, `Camera`, `IdCapture`, `DataCaptureView`, and the overlay to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, do not use this skill — the MAUI integration hosts the `DataCaptureView` as a XAML element and wires it through handlers, which is different.

## Prerequisites

### Step 0 — Fetch the latest SDK version from NuGet (mandatory, do this before any edits)

Before editing the `.csproj`, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.IdCapture/` and read the latest **stable** version number off the page (skip `-beta.*` / `-preview.*` / `-rc.*` suffixes). Use that exact version for both packages.

Do **not** guess, do **not** reuse a version from training data, and do **not** invent a number — `dotnet restore` will fail with `Unable to find package Scandit.DataCapture.IdCapture with version (>= …)`. The latest stable version changes regularly; only the live NuGet page is authoritative. If WebFetch fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.idcapture/index.json` (last entry without a pre-release suffix) before proceeding.

ID Capture's modern document/scanner API (`AcceptedDocuments`, `IdCaptureScanner`, `FullDocumentScanner`) requires **8.0+**, and the verification result model requires **8.0** — any current stable release supports it. If the project already pins an older Scandit major (6.x / 7.x), tell the user they should move to 8.x.

### Other prerequisites

- Scandit Data Capture SDK for .NET — add **two** packages to the `.csproj`, pinned to the version fetched in Step 0:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<step-0-version>" />
    <PackageReference Include="Scandit.DataCapture.IdCapture" Version="<step-0-version>" />
  </ItemGroup>
  ```
  There is **no separate Barcode package** — the PDF417/AAMVA barcode reader used for the back of driver's licenses is bundled in `Scandit.DataCapture.IdCapture`. Do **not** add any `*.Maui` package — those are MAUI-only.
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
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. **Two** initializers are required — missing `ScanditIdCapture.Initialize()` crashes the first `IdCapture.Create(...)` call.

  ```csharp
  using Android.Runtime;
  using Scandit.DataCapture.Core;
  using Scandit.DataCapture.ID;

  namespace MyApp;

  [Application]
  public class MainApplication(IntPtr handle, JniHandleOwnership ownership)
      : Application(handle, ownership)
  {
      public override void OnCreate()
      {
          base.OnCreate();
          ScanditCaptureCore.Initialize();
          ScanditIdCapture.Initialize();
      }
  }
  ```

  If the project already has an `Application` subclass, add the two `Initialize()` calls to its existing `OnCreate()` rather than creating a second one (Android refuses to load two `[Application]`-decorated classes).
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

If a .NET Android project already exists, skip this and go to the Interactive Document Configuration below.

**Recommended:** scaffold a buildable shell with the official template, then add ID Capture on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

Add the two Scandit packages and `Xamarin.AndroidX.AppCompat` from the bullets above, set `<SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>`, and continue.

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

**Question D — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```csharp
using Scandit.DataCapture.Core.Capture;

this.dataCaptureContext =
    DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");
```

> **ID Capture runs as the only mode.** Using `IdCapture` at the same time as another capture mode (e.g. `BarcodeCapture`, `SparkScan`, `BarcodeTracking`) on the same `DataCaptureContext` is **not supported**. Add `IdCapture` as the single mode on the context. If you also need to scan plain barcodes, do it in a separate, non-concurrent scanning surface — the PDF417 / AAMVA barcode on an ID is already read by `IdCapture` itself via the scanner zones, so you do not add a barcode mode for that.

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
- Documents are `new`'d with an `IdCaptureRegion`: `new Passport(IdCaptureRegion.Any)`, `new DriverLicense(IdCaptureRegion.Us)`, etc. `IdCaptureRegion` values are PascalCase (`Any`, `Us`, `Uk`, `EuAndSchengen`, `Germany`, …). Do **not** use the Kotlin underscore form.
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
| `event EventHandler<IdCapturedEventArgs> IdCaptured` | Idiomatic C# alternative to the listener's `OnIdCaptured`. |
| `event EventHandler<IdRejectedEventArgs> IdRejected` | Idiomatic C# alternative to the listener's `OnIdRejected`. |
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

The camera is off by default. You turn it on in `OnResume` / after permission is granted, and off in `OnPause` (Step 7).

> **Do not make `OnCreate` `async` and do not `await` `SetFrameSourceAsync` inside it.** With `async void OnCreate`, the activity returns control to Android at the first `await`, and Android proceeds to call `OnStart` / `OnResume` before the rest of `OnCreate` has run. `OnResume` then touches `idCapture` (or the camera) before it has been assigned, throwing `NullReferenceException` at startup. Keep `OnCreate` synchronous and discard the Task with `_ =`.

## Step 5 — Visualize with DataCaptureView + IdCaptureOverlay

ID Capture uses the generic `DataCaptureView`. Create it from the context, add it to your layout, then add an `IdCaptureOverlay` so the document frame/viewfinder is drawn.

```csharp
using Android.Views;
using Android.Widget;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.UI.Overlay;

this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);

// Add it to a container from your XML layout...
ViewGroup container = this.FindViewById<ViewGroup>(Resource.Id.data_capture_view_container)!;
container.AddView(
    this.dataCaptureView,
    new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));

// ...or host it full-screen in a FrameLayout created in code:
// var container = new FrameLayout(this);
// this.SetContentView(container);
// container.AddView(this.dataCaptureView);

this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
this.overlay.IdLayoutStyle = IdLayoutStyle.Square;   // optional; Rounded is the default
```

> `IdCaptureOverlay.Create(idCapture, dataCaptureView)` takes the mode **and** the view (the view-passing overload auto-attaches the overlay, so you do not also call `AddOverlay`). There is also a `Create(idCapture)` single-arg overload if you prefer to add it yourself.

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

Implement `IIdCaptureListener` (or subscribe to the `IdCaptured` / `IdRejected` events). **Both callbacks run on a background/arbitrary thread** — dispatch UI work to the main thread, and disable the mode while a result is displayed so the same document isn't captured repeatedly.

The listener form (mirrors the official sample):

```csharp
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

public class IdCaptureActivity : CameraPermissionActivity, IIdCaptureListener
{
    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        // Read the fields you need (see "Reading field values" below).
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;

        // Stop capturing while we show the result.
        mode.Enabled = false;

        // Callback is on a background thread — post to the UI thread.
        this.RunOnUiThread(() =>
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
        this.RunOnUiThread(() =>
        {
            // Show message; re-enable scanning afterwards.
        });
    }
}
```

Register / unregister it across the lifecycle (Step 7): `this.idCapture.AddListener(this);` / `RemoveListener(this)`.

If you prefer events instead of the interface:

```csharp
this.idCapture.IdCaptured += (sender, args) => { CapturedId id = args.CapturedId; /* ... */ };
this.idCapture.IdRejected += (sender, args) => { RejectionReason reason = args.Reason; /* ... */ };
```

> Use **either** `AddListener` **or** the events for a given concern — both deliver the same callback; subscribing to both double-processes.

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

For the richer zone-specific results (`capturedId.Mrz`, `capturedId.Viz`, `capturedId.Barcode`, `capturedId.MobileDocument`), the document images (`capturedId.Images`), and the verification outcome (`capturedId.VerificationResult`), see `references/advanced.md`.

> Always guard for nulls — a field that wasn't present on the scanned document is `null`. When formatting a date, use `DateResult.UtcDate` (a `DateTime`).

## Step 7 — Camera permission and lifecycle

Toggle the camera and the listener across the activity lifecycle. The camera — not the view — is the lifecycle handle.

```csharp
using Scandit.DataCapture.Core.Source;

protected override void OnResume()
{
    base.OnResume();

    this.idCapture.AddListener(this);
    this.idCapture.Enabled = true;

    // Request camera permission; the camera is turned on once granted.
    this.RequestCameraPermission();
}

protected override void OnPause()
{
    base.OnPause();
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    this.idCapture.RemoveListener(this);
}

protected override void OnCameraPermissionGranted()
{
    // Permission granted (or already held) — turn the camera on.
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

protected override void OnDestroy()
{
    base.OnDestroy();
    this.overlay.Dispose();
    this.idCapture.Dispose();
}
```

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
2. Ensure `<SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>` is set in the `.csproj`.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` to `AndroidManifest.xml`.
4. Request the `CAMERA` permission at runtime before scanning starts (the `CameraPermissionActivity` helper below).
5. Create `MainApplication.cs` with `ScanditCaptureCore.Initialize()` **and `ScanditIdCapture.Initialize()`** (SDK 8.0+).
6. Ensure the activity uses a `Theme.AppCompat` descendant (manifest `<application android:theme=...>` or the `[Activity]` `Theme=` attribute).
7. Provide a layout with a container (e.g. a `FrameLayout`) for the `DataCaptureView`, or host it full-screen in a `FrameLayout` created in code.
8. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.

## Complete minimal example

```csharp
using Android.OS;
using Android.Views;
using Android.Widget;

using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using Scandit.DataCapture.ID.UI.Overlay;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class IdCaptureActivity : CameraPermissionActivity, IIdCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private IdCapture idCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private IdCaptureOverlay overlay = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

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
        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        container.AddView(
            this.dataCaptureView,
            new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));
        this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
        this.overlay.IdLayoutStyle = IdLayoutStyle.Square;
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.idCapture.AddListener(this);
        this.idCapture.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.idCapture.RemoveListener(this);
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.overlay.Dispose();
        this.idCapture.Dispose();
    }

    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;
        DateResult? dateOfExpiry = capturedId.DateOfExpiry;

        mode.Enabled = false;
        this.RunOnUiThread(() =>
        {
            // Present fullName / dateOfBirth?.UtcDate / documentNumber / dateOfExpiry?.UtcDate.
            // Re-enable scanning when the user dismisses the result: mode.Enabled = true;
        });
    }

    public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
    {
        mode.Enabled = false;
        this.RunOnUiThread(() =>
        {
            // Show a message based on `reason`; re-enable scanning afterwards.
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
2. **No settings builder, no bitmask** — `new IdCaptureSettings { AcceptedDocuments = [ … ], Scanner = new IdCaptureScanner(physicalDocument: …, mobileDocument: …) }`.
3. **Documents are `new`'d with an `IdCaptureRegion`** (`new Passport(IdCaptureRegion.Any)`); regions are PascalCase.
4. **`IdCapture.Create(...)`** — factory; the constructor is private.
5. **Two NuGet packages** — `Core`, `IdCapture`. No Barcode package.
6. **Two initializers** — `ScanditCaptureCore.Initialize()`, `ScanditIdCapture.Initialize()` in `MainApplication.OnCreate()` (SDK 8.0+).
7. **You manage the camera** — `Camera.GetDefaultCamera()`, `camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings)`, `SetFrameSourceAsync`, `SwitchToDesiredStateAsync(On/Off)`. `RecommendedCameraSettings` is a static property.
8. **`DataCaptureView.Create(context)` + `IdCaptureOverlay.Create(idCapture, dataCaptureView)`** — the view is generic; the two-arg overlay factory auto-attaches.
9. **Handle both `OnIdCaptured` and `OnIdRejected`**; both run on a background thread — `RunOnUiThread` for UI and set `idCapture.Enabled = false` while a result is shown.
10. **Read values from `CapturedId`** — top-level `FullName` / `DateOfBirth` (a `DateResult`) / `DocumentNumber` / etc.
11. **No `<activity>` in the manifest** — `[Activity(MainLauncher = true, ...)]` is the canonical registration.
12. **`Theme.AppCompat` descendant** + **`SupportedOSPlatformVersion` ≥ 24** are required for the build/launch to succeed.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/android/id-capture/advanced/) — scanner selection, rejection rules, verification, anonymization, the rich result model (see `references/advanced.md`).
