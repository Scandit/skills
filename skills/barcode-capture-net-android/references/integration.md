# BarcodeCapture .NET for Android Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On .NET for Android you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with an `IBarcodeCaptureListener` (or the `BarcodeScanned` event), a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built UI — the camera preview and highlight rectangle are the only visuals.

Examples below use C# 12 and an Activity. The same APIs work identically in a Fragment — adapt ownership of `DataCaptureContext`, `BarcodeCapture`, and `Camera` to the project's existing structure.

> **MAUI?** Stop. If the project file has `<UseMaui>true</UseMaui>`, switch to the `barcode-capture-maui` skill. The MAUI integration uses `<scandit:DataCaptureView>` in XAML and the `UseScanditCore` / `UseScanditBarcode` builder, which are different.

## Prerequisites

- Scandit Data Capture SDK for .NET — add via NuGet. Before pinning a version, fetch the latest published version from `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/` and read the latest stable version number from the page. Then add both packages to the `.csproj`:
  ```xml
  <ItemGroup>
    <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-version>" />
    <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-version>" />
  </ItemGroup>
  ```
  Both packages are published on NuGet.org. Do **not** add `Scandit.DataCapture.Core.Maui` or `Scandit.DataCapture.Barcode.Maui` — those are MAUI-only.
- `Xamarin.AndroidX.AppCompat` — required because the `CameraPermissionActivity` helper below inherits from `AppCompatActivity`, and the AppCompat manifest theme (see the manifest setup bullet below) resolves through this package. The `dotnet new android` template already pulls it in transitively via `Xamarin.AndroidX.AppCompat.AppCompatResources`, but for manually scaffolded projects add it explicitly:
  ```xml
  <PackageReference Include="Xamarin.AndroidX.AppCompat" Version="<latest-version-with-xamarin-suffix>" />
  ```
  **When fetching the latest version, pick the highest available including any Xamarin-revision suffix — e.g. `1.7.1.3`, not bare `1.7.1`.** The `.X` suffix marks Xamarin-binding patch revisions and carries critical transitive-dep updates. The suffix-less form has a known `Xamarin.AndroidX.SavedState` constraint mismatch that fails compilation with `CS7069: Reference to type 'ISavedStateRegistryOwner' ... could not be found`. If the NuGet API response lists `1.7.1`, `1.7.1.1`, `1.7.1.2`, and `1.7.1.3`, the correct pick is `1.7.1.3`. A `jq -r '.versions | last'` filter on the flatcontainer endpoint returns the highest version correctly.
- **SDK initialization (Scandit 8.0+).** Add a `MainApplication.cs` next to `MainActivity.cs` that initializes the Scandit DI container at process start. Without this, the first `DataCaptureView.Create` / `BarcodeCapture.Create` call crashes because the container has no registrations.

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
- `AndroidManifest.xml` setup — three concerns, all required:

  1. **Camera entries** (top-level, sibling to `<application>`):
     ```xml
     <uses-feature android:name="android.hardware.camera" android:required="true" />
     <uses-permission android:name="android.permission.CAMERA" />
     ```

  2. **AppCompat theme on `<application>`** — set `android:theme="@style/Theme.AppCompat.DayNight.NoActionBar"` (or another `Theme.AppCompat` descendant) on the `<application>` element:
     ```xml
     <application
         ...
         android:theme="@style/Theme.AppCompat.DayNight.NoActionBar">
     </application>
     ```
     Required because `AppCompatActivity` throws `java.lang.IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity` at instant launch otherwise. `dotnet new android` does not set this attribute, so it must be added explicitly. `Theme.AppCompat.DayNight.NoActionBar` is the right default for a full-screen camera preview; `Theme.AppCompat.Light.NoActionBar` is also fine.

  3. **Do not add `<activity>` declarations** for `MainActivity` (or any other class decorated with `[Activity]`). The attribute is the canonical registration in .NET for Android — the build merges a correctly-named entry into the final manifest using the .NET-derived Java class name (typically `<lowercase-namespace>.MainActivity`). A manual `<activity android:name=".MainActivity">` resolves against `<ApplicationId>` and won't match the generated class, producing `ClassNotFoundException` at launch.

  Request the camera permission at runtime using `RequestPermissions` before scanning starts (Android API 23+).

### Project scaffolding (new projects only)

If a .NET Android project already exists, skip this subsection and go to the Integration flow below.

**Recommended:** scaffold a buildable shell with the official template, then add BarcodeCapture on top:

```bash
dotnet new android -o MyApp
cd MyApp
```

This produces a project with the correct `OutputType`, an `AndroidManifest.xml` with an `<application>`/`<activity>` declared, a `Resources/values/strings.xml`, and a `Resources/mipmap-*/ic_launcher.*` set. Add the Scandit and `Xamarin.AndroidX.AppCompat` packages from the bullets above and continue with Step 1.

**Manual scaffold (only if `dotnet new android` is unavailable):** the project must contain at minimum:

- `MyApp.csproj` with `<TargetFramework>net10.0-android</TargetFramework>` (or the latest installed Android TFM). Do **not** set `<OutputType>Library</OutputType>` — leave `<OutputType>` unset (the SDK defaults to `Exe` for `*-android` TFMs) or set it explicitly to `Exe`. A `Library` value silently produces an `.aar` instead of an installable `.apk`.
- `Properties/AndroidManifest.xml` with an `<application>` element and at least one `<activity>` declared, in addition to the camera entries above.
- `Resources/values/strings.xml` defining every `@string/...` the manifest references (at minimum `app_name`):
  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <resources>
    <string name="app_name">MyApp</string>
  </resources>
  ```
- `Resources/mipmap-*/ic_launcher.png` matching the `android:icon` attribute on `<application>`. If you don't have an icon yet, remove the `android:icon` attribute entirely rather than referencing a missing resource.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which Activity (or Fragment) they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `<PackageReference Include="Scandit.DataCapture.Barcode" Version="<version>" />` and `<PackageReference Include="Scandit.DataCapture.Core" Version="<version>" />` to the `.csproj` (the version was already fetched and filled in above).
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts (the example below shows a `CameraPermissionActivity` helper).
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

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

`Camera.GetDefaultCamera()` returns the back camera. The canonical pattern (matching the official .NET Android sample) is to obtain the camera, apply the recommended settings via `ApplySettingsAsync`, and attach it as the frame source. The .NET binding also has a `Camera.GetDefaultCamera(CameraSettings?)` overload that calls `ApplySettingsAsync` internally, but the explicit two-line form is preferred.

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

`DataCaptureView.Create(dataCaptureContext)` creates the camera preview as an Android `View`. Place it inside a `FrameLayout` container in the activity layout with `MatchParent` for both dimensions.

`BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView)` adds the highlight overlay to the view in one step.

```csharp
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Barcode.UI.Overlay;

// In OnCreate, after SetContentView(Resource.Layout.activity_main):
this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);

var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
container?.AddView(
    this.dataCaptureView,
    new FrameLayout.LayoutParams(
        ViewGroup.LayoutParams.MatchParent,
        ViewGroup.LayoutParams.MatchParent));
```

The activity layout should contain a `FrameLayout` (or `CoordinatorLayout`) with an id, e.g. `activity_main.axml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
             android:id="@+id/data_capture_view_container"
             android:layout_width="match_parent"
             android:layout_height="match_parent" />
```

### BarcodeCaptureOverlay members

| Member | Description |
|--------|-------------|
| `BarcodeCaptureOverlay.Create(mode, view)` | Factory — creates the overlay and adds it to the view. |
| `BarcodeCaptureOverlay.Create(mode)` | Factory — creates the overlay without attaching to a view. Attach later via `dataCaptureView.AddOverlay(overlay)`. |
| `Brush` | `Brush` (get/set) — fill / stroke for recognized-barcode highlights. |
| `BarcodeCaptureOverlay.DefaultBrush` | static `Brush` (get) — the default Scandit-blue stroke brush. |
| `Viewfinder` | `IViewfinder?` (get/set) — optional viewfinder drawn on the preview. |
| `ShouldShowScanAreaGuides` | `bool` (get/set) — development-only aid, defaults to `false`. |
| `SetProperty(string, object)` | Unstable/experimental flags. |

## Step 6 — Implement IBarcodeCaptureListener (or subscribe to the event)

The .NET binding exposes both patterns. Pick **one**:

### Listener interface (parity with the Kotlin / iOS native APIs)

```csharp
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Core.Data;

public class BarcodeScanActivity : AppCompatActivity, IBarcodeCaptureListener
{
    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        // Prevent duplicate / racing scans while we handle this one.
        // Re-enabled inside ShowResults below when the user dismisses the dialog.
        barcodeCapture.Enabled = false;

        // OnBarcodeScanned is called on a background thread — dispatch UI work.
        RunOnUiThread(() => this.ShowResults($"Scanned: {barcode.Data}"));
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        // Called every frame; keep this fast.
    }

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}

// In OnCreate or InitializeAndStartBarcodeScanning:
this.barcodeCapture.AddListener(this);
```

### Event handler (idiomatic C#)

```csharp
this.barcodeCapture.BarcodeScanned += (sender, args) =>
{
    var barcode = args.Session.NewlyRecognizedBarcode;
    if (barcode == null) return;

    args.BarcodeCapture.Enabled = false;
    RunOnUiThread(() => this.ShowResults($"Scanned: {barcode.Data}"));
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
| `FrameData` | `IFrameData` | The frame that produced the event. |

### BarcodeCaptureSession

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `NewlyRecognizedBarcode` | `Barcode?` | The barcode just scanned in the most recent frame. |
| `NewlyLocalizedBarcodes` | `IList<LocalizedOnlyBarcode>` | Codes that were located but not decoded. |
| `FrameSequenceId` | `long` | Identifier of the current frame sequence (stable until camera interruption). |
| `Reset()` | method | Clears the session's duplicate-filter history. **Only call inside the listener callbacks.** |

### Showing the result and re-enabling scanning

`barcodeCapture.Enabled = false` stops new detections until you set it back to `true`. The handler must own that re-enable — otherwise the scanner stays dead after the first scan. The canonical Scandit sample uses an `AlertDialog` so the user dismisses the result with an OK button, which is also the natural point to re-enable:

```csharp
using Android.Content; // for DialogClickEventArgs

private AlertDialog? dialog;

private void ShowResults(string result)
{
    this.dialog = new AlertDialog.Builder(this)
        .SetCancelable(false)!
        .SetTitle(result)!
        .SetPositiveButton(Android.Resource.String.Ok, (sender, args) =>
        {
            this.barcodeCapture.Enabled = true;
        })!
        .Create();
    this.dialog?.Show();
}

private void DismissScannedCodesDialog()
{
    if (this.dialog != null)
    {
        this.dialog.Dismiss();
        this.dialog = null;
    }
}
```

Hook `DismissScannedCodesDialog` into `ResumeFrameSource` so a dialog left over from a previous foreground session is cleared when the activity comes back:

```csharp
private void ResumeFrameSource()
{
    this.DismissScannedCodesDialog();
    this.barcodeCapture.Enabled = true;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}
```

This matches Scandit's official `BarcodeCaptureSimpleSample` flow on Android.

If you only need a brief non-blocking notification, use a `Toast` and schedule the re-enable explicitly instead — `Toast.MakeText().Show()` is fire-and-forget, so the re-enable has to be on a timer:

```csharp
RunOnUiThread(async () =>
{
    Toast.MakeText(this, $"Scanned: {barcode.Data}", ToastLength.Short)?.Show();
    await Task.Delay(TimeSpan.FromSeconds(2)); // ToastLength.Short ≈ 2s on Android
    this.barcodeCapture.Enabled = true;
});
```

The rule either way: every `Enabled = false` needs a matching `Enabled = true` on the path that returns control to the user.

## Step 7 — Lifecycle management

Drive the camera from `OnResume` and `OnPause`. The camera must not be active while the activity is in the background.

```csharp
protected override void OnResume()
{
    base.OnResume();

    // Request runtime permission on Android M+ if needed (see CameraPermissionActivity below).
    this.barcodeCapture.Enabled = true;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
}

protected override void OnPause()
{
    base.OnPause();
    this.barcodeCapture.Enabled = false;
    this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
}
```

## Camera permission helper

The official .NET Android sample factors the runtime permission flow into a base activity. Reuse it verbatim:

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

Then derive the scanning activity from `CameraPermissionActivity` and call `RequestCameraPermission()` from `OnResume` (after `base.OnResume()`).

## Complete minimal example

```csharp
using Android.Content;
using Android.OS;
using Android.Widget;

using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Core.UI.Viewfinder;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class BarcodeScanActivity : CameraPermissionActivity, IBarcodeCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeCapture barcodeCapture = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;
    private BarcodeCaptureOverlay overlay = null!;
    private AlertDialog? dialog;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.InitializeAndStartBarcodeScanning();
    }

    protected override void OnResume()
    {
        base.OnResume();
        if (Build.VERSION.SdkInt >= BuildVersionCodes.M)
        {
            this.RequestCameraPermission();
        }
        else
        {
            this.ResumeFrameSource();
        }
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeCapture.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    protected override void OnDestroy()
    {
        this.barcodeCapture.RemoveListener(this);
        base.OnDestroy();
    }

    protected override void OnCameraPermissionGranted() => this.ResumeFrameSource();

    private void ResumeFrameSource()
    {
        this.DismissScannedCodesDialog();
        this.barcodeCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    private void DismissScannedCodesDialog()
    {
        if (this.dialog != null)
        {
            this.dialog.Dismiss();
            this.dialog = null;
        }
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

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);
        this.overlay.Viewfinder = new RectangularViewfinder(
            RectangularViewfinderStyle.Square,
            RectangularViewfinderLineStyle.Light);

        var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        // Stop scanning while we display the result. Re-enabled when the user dismisses the dialog.
        barcodeCapture.Enabled = false;

        var description = new SymbologyDescription(barcode.Symbology);
        var result = $"Scanned: {barcode.Data} ({description.ReadableName})";
        RunOnUiThread(() => this.ShowResults(result));
    }

    private void ShowResults(string result)
    {
        this.dialog = new AlertDialog.Builder(this)
            .SetCancelable(false)!
            .SetTitle(result)!
            .SetPositiveButton(Android.Resource.String.Ok, (sender, args) =>
            {
                this.barcodeCapture.Enabled = true;
            })!
            .Create();
        this.dialog?.Show();
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData) { }

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}
```

## Optional configuration

### Async work after a scan (Task-based)

When the scan result requires a network or database call, disable scanning immediately on the scanner thread, then offload the work and re-enable in a `finally` block so scanning always resumes even if the lookup fails.

```csharp
public async void OnBarcodeScanned(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    IFrameData frameData)
{
    var data = session.NewlyRecognizedBarcode?.Data;
    if (data == null) return;

    barcodeCapture.Enabled = false;
    try
    {
        var result = await LookupAsync(data); // your async network call
        RunOnUiThread(() => UpdateUi(result));
    }
    finally
    {
        barcodeCapture.Enabled = true;
    }
}
```

> Using `async void` is acceptable here because the callback signature is `void`. Wrap the body in `try`/`finally` so an exception cannot leave the capture mode permanently disabled.

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

To restrict scanning to a sub-area of the preview, set `BarcodeCaptureSettings.LocationSelection` to an `ILocationSelection` instance (e.g. `RectangularLocationSelection`). Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/net/android/barcode-capture/advanced/) page for the exact constructor arguments — do not guess.

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
3. **Listener thread** — `OnBarcodeScanned` runs on a background thread; always dispatch UI work via `RunOnUiThread(() => …)`.
4. **Disable inside the callback** — set `barcodeCapture.Enabled = false` before doing any non-trivial work to avoid duplicate scans.
5. **Camera lifecycle** — turn the camera off in `OnPause()`, back on in `OnResume()`. Call `barcodeCapture.RemoveListener(this)` in `OnDestroy()`.
6. **Overlay is explicit** — `BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView)` adds the overlay to the view in one step. There is no implicit overlay.
7. **Runtime permission** — add `CAMERA` to `AndroidManifest.xml` and request it at runtime before the first scan.
8. **Symbologies** — enable only what's needed. Variable-length 1D symbologies (Code39, Code128, ITF) may need `ActiveSymbolCounts` adjusted (use `ICollection<short>`).
9. **Settings before construction** — configure `BarcodeCaptureSettings` before passing to `Create`. To change at runtime, use `barcodeCapture.ApplySettingsAsync(newSettings)`.
10. **`TimeSpan`, not `TimeInterval`** — `CodeDuplicateFilter` is `TimeSpan`. Use `CodeDuplicate.DefaultDuplicateFilter` / `CodeDuplicate.ReportDataAndSymbologyOnlyOnce` / `TimeSpan.FromMilliseconds(...)` / `TimeSpan.Zero`.
