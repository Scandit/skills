# Xamarin.iOS → .NET for iOS

Target: a single SDK-style `.csproj` with `<TargetFramework>net8.0-ios</TargetFramework>`. Confirm the exact `net*` version against the Scandit .NET docs and the customer's installed workloads (`dotnet workload list`). Always work on a branch/backup.

> Use the [.NET Upgrade Assistant](https://learn.microsoft.com/en-us/dotnet/core/porting/upgrade-assistant-overview) for the mechanical `.csproj` conversion where available, then apply the Scandit- and iOS-specific fixes below.

## Step 1 — Convert the project file to SDK-style

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0-ios</TargetFramework>
    <SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>
    <OutputType>Exe</OutputType>
    <ApplicationId>com.example.myapp</ApplicationId>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
```

- Delete `packages.config`; convert to `<PackageReference>`.
- Drop explicit `<Compile Include>` items (SDK-style globs automatically).
- Scandit's iOS minimum deployment target is **15.0** — set `<SupportedOSPlatformVersion>` accordingly (raise the source's `MinimumOSVersion` if it is lower).
- Legacy `<MtouchArch>`, `<CodesignKey>`, provisioning settings map to the modern iOS MSBuild properties; keep signing config in the `.csproj` or a `.pubxml`.

## Step 2 — Swap the Scandit packages

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable>" />
</ItemGroup>
```

Pin every Scandit package to one version fetched from nuget.org (see `scandit-packages.md`), then `dotnet restore`.

## Step 3 — Migrate Info.plist and entitlements

- `Info.plist` and `Entitlements.plist` carry over. Keep the build actions (implicit in SDK-style: `Info.plist` is picked up by convention).
- Ensure `NSCameraUsageDescription` (`Privacy - Camera Usage Description`) is present with a user-facing string — without it the app crashes on first camera access.

## Step 4 — Bootstrap and SDK 8 initialization

For **SDK 8.0+**, initialize in `AppDelegate.FinishedLaunching` before any Scandit API is touched (before creating the window / root view controller):

```csharp
[Register("AppDelegate")]
public class AppDelegate : UIApplicationDelegate
{
    public override UIWindow? Window { get; set; }

    public override bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
    {
        ScanditCaptureCore.Initialize();      // always
        ScanditBarcodeCapture.Initialize();   // per product — see the impl skill
        // ... existing window/root VC setup ...
        return true;
    }
}
```

Not required on 6.x/7.x. The per-product `Scandit*.Initialize()` calls live in the implementation skill.

## Step 5 — Verify

- `dotnet build -f net8.0-ios`.
- On the simulator, smoke-check that the SDK initializes and a scan is reported (see the `ios-simulator-camera-feed` workflow, or the impl skill's checklist). Note: iOS camera capture requires a real device or a simulator feed.

## Hand off

The Scandit call sites (`DataCaptureView.Create(context, frame)`, `frameData.Dispose()`, view-controller lifecycle, overlays) are verified by **`<product>-net-ios`** — e.g. `barcode-capture-net-ios`. See `scandit-packages.md` for the product→skill mapping.
