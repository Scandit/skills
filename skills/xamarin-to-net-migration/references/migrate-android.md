# Xamarin.Android → .NET for Android

Target: a single SDK-style `.csproj` with `<TargetFramework>net8.0-android</TargetFramework>` that builds an installable APK and keeps the Scandit integration working. Confirm the exact `net*` version against the Scandit .NET docs and the customer's installed .NET workloads (`dotnet workload list`) rather than assuming.

> Prefer the [.NET Upgrade Assistant](https://learn.microsoft.com/en-us/dotnet/core/porting/upgrade-assistant-overview) for the mechanical `.csproj` conversion where it is installed, then apply the Scandit- and Android-specific fixes below. Always work on a branch/backup.

## Step 1 — Convert the project file to SDK-style

Replace the legacy `.csproj` header/body with the SDK-style form:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0-android</TargetFramework>
    <SupportedOSPlatformVersion>24</SupportedOSPlatformVersion>
    <OutputType>Exe</OutputType>
    <ApplicationId>com.example.myapp</ApplicationId>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
```

- Delete `packages.config`; every entry becomes a `<PackageReference>`.
- Delete explicit `<Compile Include="…">` items — SDK-style globs `**/*.cs` automatically. Keep only non-default excludes/includes.
- `<SupportedOSPlatformVersion>` must be **at least 24** — Scandit's Android AAR requires API 24+; a lower value fails with `uses-sdk:minSdkVersion … cannot be smaller than version 24 declared in library`.
- Move `AssemblyInfo.cs` assembly attributes into `<PropertyGroup>` (or set `<GenerateAssemblyInfo>false</GenerateAssemblyInfo>` to keep the file).

## Step 2 — Swap the Scandit packages

Drop the `.Xamarin` suffix and pin all Scandit packages to one version fetched from nuget.org (see `scandit-packages.md`):

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable>" />
</ItemGroup>
```

`dotnet restore` after the swap.

## Step 3 — Migrate the manifest and resources

- `AndroidManifest.xml` moves to the project (SDK-style keeps it at `Properties/AndroidManifest.xml` or the path in `<AndroidManifest>`). Keep `<uses-permission android:name="android.permission.CAMERA" />` and any `<uses-feature>`.
- **Do not hand-declare `<activity>` elements for `[Activity]`-decorated classes** — the `[Activity(MainLauncher = true)]` attribute is the canonical registration in .NET for Android; a manual entry resolves against `<ApplicationId>` and won't match the generated class (`ClassNotFoundException` at launch).
- Resources under `Resources/` (drawable, layout, values) carry over unchanged; the build actions are implicit in SDK-style.

## Step 4 — Bootstrap and SDK 8 initialization

For **SDK 8.0+**, add explicit initialization in an `Android.App.Application` subclass:

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

Not required on 6.x/7.x — if the source is on 6.x/7.x, this is added as part of moving to 8. The exact `Scandit*.Initialize()` calls per product live in the implementation skill you hand off to.

## Step 5 — Verify

- `dotnet build -f net8.0-android` (or the confirmed TFM).
- If a device/emulator is available, deploy and smoke-check that the Scandit SDK initializes and a scan is reported (see the `android-emulator-camera-feed` workflow, or the impl skill's checklist).

## Hand off

The Scandit call sites (`DataCaptureView.Create`, listener wiring, camera lifecycle, overlays) are verified by **`<product>-net-android`** — e.g. `barcode-capture-net-android`. See `scandit-packages.md` for the product→skill mapping.
