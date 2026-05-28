# SparkScan .NET for Android Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for the `<PackageReference Include="Scandit.DataCapture.Barcode" Version="..." />` (or `Scandit.DataCapture.Core`) line. Both packages should be pinned to the **same** version. If they drift, treat the lowest version as the installed one.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x (`dotnet.android >= 6.22`) | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version, ask the user which version they are migrating from.

> Note: SparkScan on dotnet.android was first published in 6.22. Anything older does not have a SparkScan API on this platform — confirm with the user before assuming a version below 6.22.

---

## Step 2: Update the dependency version

Update the SDK version in every `<PackageReference>`:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.Barcode`

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Apply source-code changes

Search for files that use SparkScan (search for `SparkScan`, `SparkScanSettings`, `SparkScanView`, `SparkScanViewSettings`, `SparkScanEventArgs`, `ISparkScanListener`, `ISparkScanFeedbackDelegate`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for .NET Android SparkScan is primarily about renamed / removed `SparkScanView` properties and the scan-intention default change. Go through every section below and apply each change that matches the project.

### Where these properties live in v6

- **On `SparkScanView`** — all button-visibility, color, and text properties listed below.
- **On `SparkScanViewSettings`** — `DefaultHandMode` only (removed in v7).

When searching the project, look for usages on both the view instance and the settings object.

### SparkScanView renames

Apply these renames everywhere they appear. Always replace the old name with the new one, preserving the existing value, regardless of what that value is:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `TorchButtonVisible` | `TorchControlVisible` |
| `CameraButtonBackgroundColor` | `TriggerButtonCollapsedColor`, `TriggerButtonExpandedColor`, `TriggerButtonAnimationColor` (see note) |
| `CaptureButtonTintColor` | `TriggerButtonTintColor` |
| `FastFindButtonVisible` | `BarcodeFindButtonVisible` |

> **Note on `CameraButtonBackgroundColor`:** v7 splits this into three separate color properties for the collapsed state, expanded state, and animation. If the user set a single color, apply it to all three unless they indicate otherwise.

### SparkScanView removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause compile errors:

- `CaptureButtonActiveBackgroundColor`
- `StopCapturingText`, `StartCapturingText`, `ResumeCapturingText`, `ScanningCapturingText` — the trigger button no longer displays text
- `HandModeButtonVisible`
- `SoundModeButtonVisible`
- `HapticModeButtonVisible`
- `ShouldShowScanAreaGuides`

### SparkScanViewSettings removed APIs

- `DefaultHandMode` — removed in v7. Hand-mode is no longer configurable.

### `TriggerButtonCollapseTimeout` default change

The default value changed from "never collapse" to **5 seconds**.

- If the project **already sets** `TriggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, inform the user that the button will now collapse after 5 seconds by default and they can set it to `TimeSpan.FromSeconds(-1)` to restore the old behavior.

### New v7 APIs (optional)

These are available in v7 — mention them only if the user asks:

- `SparkScanViewState` (enum `Initial`, `Idle`, `Inactive`, `Active`, `Error`) + the `SparkScanView.ViewStateChanged` event of type `EventHandler<SparkScanViewStateEventArgs>`.
- `SparkScanViewSettings.DefaultMiniPreviewSize` (`SparkScanMiniPreviewSize.Regular` / `Expanded`).
- `SparkScanView.PreviewCloseControlVisible`, `TriggerButtonVisible` (defaults to `true`), `TorchControlVisible`.
- `SparkScanView.TriggerButtonImage` (`Core.Image?`) — set a custom trigger icon.
- `SparkScanView.TriggerButtonCollapsedColor` / `TriggerButtonExpandedColor` / `TriggerButtonAnimationColor` / `TriggerButtonTintColor` — replacements for v6's color properties.

### `BarcodeTracking` → `BarcodeBatch` rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch`. The API is otherwise unchanged.

### Scan intention default change

The default `ScanIntention` is now `Smart` from v7.

- If the project already explicitly sets `ScanIntention.Manual` (or any other value) on `SparkScanSettings`, leave it.
- If the project uses a single-image frame source, Smart is incompatible — set `settings.ScanIntention = ScanIntention.Manual`.
- Otherwise the code still compiles — no change needed. Inform the user that Smart Scan is now the default.

---

## Migration: 7 → 8

The 7→8 step for .NET Android SparkScan is mostly mechanical. Most of the API surface is unchanged. The one **required** action is adding explicit SDK initialization at process start — without it, the app crashes on the first Scandit API call.

### Explicit SDK initialization is now required

Scandit 8.0 removed the implicit container bootstrap that 6.x/7.x performed automatically. The app must now call `ScanditCaptureCore.Initialize()` and `ScanditBarcodeCapture.Initialize()` before any Scandit type is constructed.

Check whether the project already has an `Application` subclass (look for `[Application]` on a class deriving from `Android.App.Application`, typically in `MainApplication.cs`).

**If `MainApplication.cs` exists** — add the two `Initialize()` calls at the top of its `OnCreate()` (after `base.OnCreate()`):

```csharp
public override void OnCreate()
{
    base.OnCreate();
    ScanditCaptureCore.Initialize();
    ScanditBarcodeCapture.Initialize();
    // ... existing init code stays below
}
```

Make sure these `using` directives are present:

```csharp
using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;
```

**If `MainApplication.cs` does not exist** — create it next to `MainActivity.cs`. Android will refuse to load two `[Application]`-decorated classes, so do not add a second one.

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

Symptom if this step is skipped: instant launch crash at the first `new SparkScan(...)` / `SparkScanView.Create(...)` call, because the DI container has no registrations.

### `LabelCaptureButtonVisible` / `LabelCaptureButtonTapped` introduced in 8.3

If the user wants a Label Capture toolbar button, these are available in 8.3+:

```csharp
this.sparkScanView.LabelCaptureButtonVisible = true;
this.sparkScanView.LabelCaptureButtonTapped += (s, e) => { /* navigate to Label Capture screen */ };
```

If the project does not use Label Capture, no action is needed.

### `TargetModeButtonVisible` deprecation in 8.5

The target mode button now toggles `SparkScanSettings.SelectionMode` between `SelectionMode.On` and `SelectionMode.Off`. The property name `TargetModeButtonVisible` will be renamed in 9.0. Existing code keeps compiling — no required change.

### SparkScan text scanning (8.x, opt-in)

v8 adds the ability to scan text alongside barcodes in SparkScan. This is purely additive — existing code is unaffected. Mention it only if the user asks about new features.

### No other breaking SparkScan changes

`new SparkScan(settings)`, `ISparkScanListener`, the `BarcodeScanned` / `SessionUpdated` events, `SparkScanSession`, `SparkScanView.Create(...)`, and the feedback delegate are all unchanged in v8 for .NET for Android.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g., how `CameraButtonBackgroundColor` was split into three properties). Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the SparkScan API reference (`https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html`) to find the correct API before guessing.
