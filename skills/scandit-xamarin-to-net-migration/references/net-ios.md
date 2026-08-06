# Scandit on .NET for iOS

**Precondition:** the app is already a .NET-for-iOS project (`<Project Sdk="Microsoft.NET.Sdk">`, `<TargetFramework>net*-ios</TargetFramework>`). If it is still `Xamarin.iOS`/legacy, stop and route to the .NET Upgrade Assistant (see `detection.md` → Precondition). This reference covers **only** the Scandit integration on that already-migrated project.

> **Use the TFM the project already targets.** Run `dotnet --version` / `dotnet workload list` and build against the project's existing `net*-ios` TFM; do not retarget it here. Use the same TFM in every `dotnet build -f …` you run and report. Always work on a branch/backup.

## Step 1 — Swap the Scandit packages

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable>" />
</ItemGroup>
```

Drop the `.Xamarin` suffix, remove the old references, pin every Scandit package to one version fetched from nuget.org (see `scandit-packages.md`), then `dotnet restore`.

## Step 2 — Verify the Scandit runtime prerequisites

- **Scandit's iOS minimum deployment target is 15.0** — set `<SupportedOSPlatformVersion>15.0</SupportedOSPlatformVersion>` (raise it if the migrated project left it lower; also raise `MinimumOSVersion` in `Info.plist` if it is below 15.0).
- **Camera usage description** — `Info.plist` must keep `NSCameraUsageDescription` (`Privacy - Camera Usage Description`) with a user-facing string. Without it the app crashes on first camera access.

## Step 3 — Add SDK 8 initialization

For **SDK 8.0+**, initialize in `AppDelegate.FinishedLaunching` before any Scandit API is touched (before creating the window / root view controller) — a project coming from Xamarin 6.x/7.x will not have this:

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

The per-product `Scandit*.Initialize()` calls live in the implementation skill.

## Step 4 — Verify

- Parity check first (see `SKILL.md` Phase 5): confirm no Scandit view/listener/overlay was lost in the swap.
- `dotnet build -f <the project's net*-ios TFM>`.
- On the simulator, smoke-check that the SDK initializes and a scan is reported (see the `ios-simulator-camera-feed` workflow, or the impl skill's checklist). Note: iOS camera capture requires a real device or a simulator feed.

## Hand off

The Scandit call sites (`DataCaptureView.Create(context, frame)`, `frameData.Dispose()`, view-controller lifecycle, overlays) are verified by **`<product>-net-ios`** — e.g. `barcode-capture-net-ios`. See `scandit-packages.md` for the product→skill mapping.
