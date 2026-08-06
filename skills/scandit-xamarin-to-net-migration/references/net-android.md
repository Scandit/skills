# Scandit on .NET for Android

**Precondition:** the app is already a .NET-for-Android project (`<Project Sdk="Microsoft.NET.Sdk">`, `<TargetFramework>net*-android</TargetFramework>`). If it is still `MonoAndroid`/legacy, stop and route to Microsoft's app-modernization tooling (see `detection.md` → Precondition). This reference covers **only** the Scandit integration on that already-migrated project.

> **Use the TFM the project already targets.** Run `dotnet --version` / `dotnet workload list` and build against the project's existing `net*-android` TFM; do not retarget it here (that is a general-migration decision). Use the same TFM in every `dotnet build -f …` you run and report. On `net10.0-android`, also add the kotlinx-serialization override documented in `net-maui.md` — without it the build is clean and the first scan crashes. Always work on a branch/backup.

## Step 1 — Swap the Scandit packages

Drop the `.Xamarin` suffix and pin all Scandit packages to one version fetched from nuget.org (see `scandit-packages.md`):

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable>" />
</ItemGroup>
```

Remove the old `Scandit.DataCapture.*.Xamarin` references (and any stale `<Reference>`/`<HintPath>` the general migration left behind). `dotnet restore` after the swap.

## Step 2 — Verify the Scandit runtime prerequisites

Microsoft's app-modernization tooling does not know Scandit's requirements. Confirm (and fix if wrong):

- **`<SupportedOSPlatformVersion>` must be at least 24** — Scandit's Android AAR requires API 24+; a lower value fails with `uses-sdk:minSdkVersion … cannot be smaller than version 24 declared in library`. Raise it to 24 if the migrated project left it lower.
- **Camera permission** — `AndroidManifest.xml` must keep `<uses-permission android:name="android.permission.CAMERA" />`. Without it the app crashes at first camera access. (Runtime permission prompting is handled in the implementation skill's call sites.)

## Step 3 — Add SDK 8 initialization

For **SDK 8.0+**, add explicit initialization in an `Android.App.Application` subclass — Xamarin 6.x/7.x self-initialized, so a project coming from there will not have this and will crash at the first Scandit call without it:

```csharp
[Application]
public class MainApplication : Application
{
    public MainApplication(IntPtr handle, JniHandleOwnership ownership) : base(handle, ownership) { }

    public override void OnCreate()
    {
        base.OnCreate();
        ScanditCaptureCore.Initialize();      // always
        ScanditBarcodeCapture.Initialize();   // per product — see the impl skill
    }
}
```

The exact `Scandit*.Initialize()` calls per product live in the implementation skill you hand off to.

## Step 4 — Verify

- Parity check first (see `SKILL.md` Phase 5): confirm no Scandit view/listener/overlay was lost in the swap.
- `dotnet build -f <the project's net*-android TFM>`.
- If a device/emulator is available, deploy and smoke-check that the Scandit SDK initializes and a scan is reported (see the `android-emulator-camera-feed` workflow, or the impl skill's checklist).

## Hand off

The Scandit call sites (`DataCaptureView.Create`, listener wiring, camera lifecycle, overlays) are verified by **`<product>-net-android`** — e.g. `barcode-capture-net-android`. See `scandit-packages.md` for the product→skill mapping.
