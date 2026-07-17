# Xamarin.Forms → .NET MAUI

This is the largest of the three paths: a Forms solution (a shared `.Forms` project + `.Android`/`.iOS` heads) collapses into **one** multi-target MAUI project. Confirm the exact `net*` version against the Scandit MAUI docs and installed workloads (`dotnet workload install maui`). Always work on a branch/backup.

> Follow Microsoft's [Forms → MAUI upgrade guidance](https://learn.microsoft.com/en-us/dotnet/maui/migration/forms-projects) and use the [.NET Upgrade Assistant](https://learn.microsoft.com/en-us/dotnet/core/porting/upgrade-assistant-overview) (`upgrade-assistant upgrade`) for the scaffolding, then apply the Scandit and MAUI-specific fixes below.

## Step 1 — Create the multi-target SDK-style project

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net8.0-android;net8.0-ios</TargetFrameworks>
    <UseMaui>true</UseMaui>
    <SingleProject>true</SingleProject>
    <OutputType>Exe</OutputType>
    <ApplicationId>com.example.myapp</ApplicationId>
    <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">24</SupportedOSPlatformVersion>
    <SupportedOSPlatformVersion Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'ios'">15.0</SupportedOSPlatformVersion>
  </PropertyGroup>
</Project>
```

Platform head projects are removed; their code moves under `Platforms/Android/` and `Platforms/iOS/` in the single project.

## Step 2 — Namespace and host-builder changes

- **Namespaces:** `Xamarin.Forms` → `Microsoft.Maui` / `Microsoft.Maui.Controls`; `Xamarin.Essentials` → `Microsoft.Maui.*` / `Microsoft.Maui.ApplicationModel` etc. Update `using` directives and XAML `xmlns` (`http://xamarin.com/schemas/2014/forms` → `http://schemas.microsoft.com/dotnet/2021/maui`).
- **App entry:** the Forms `App.xaml`/`App.xaml.cs` becomes a MAUI `App` (`: Application`), and startup moves into `MauiProgram.CreateMauiApp()`:

```csharp
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .UseScanditCore(configure => configure.AddDataCaptureView())  // Scandit MAUI builder ext
            .UseScanditBarcode();                                          // per product — see impl skill
        return builder.Build();
    }
}
```

- The Android `MainActivity`/`MainApplication` and iOS `AppDelegate` become thin MAUI shims under `Platforms/` (`: MauiAppCompatActivity`, `: MauiUIApplicationDelegate`). Scandit MAUI initializes through the `.UseScandit*()` builder extensions — you do **not** hand-call `ScanditCaptureCore.Initialize()` in a MAUI app (that is the non-MAUI path).

## Step 3 — Swap the Scandit packages (MAUI needs the `*.Maui` companions)

Unlike the non-MAUI paths, MAUI needs **both** the plain and `*.Maui` packages, all pinned to one version from nuget.org:

```xml
<ItemGroup>
  <PackageReference Include="Scandit.DataCapture.Core" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Core.Maui" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode" Version="<latest-stable>" />
  <PackageReference Include="Scandit.DataCapture.Barcode.Maui" Version="<latest-stable>" />
</ItemGroup>
```

The `*.Maui` packages provide the builder extensions, handlers, and `<scandit:...>` XAML controls; the plain packages provide the bindings they delegate to. See `scandit-packages.md`.

## Step 4 — Migrate the manual-only Forms constructs

These do **not** convert mechanically — flag each and migrate deliberately:

| Xamarin.Forms construct | .NET MAUI equivalent |
|---|---|
| Custom renderer (`ExportRenderer`, `ViewRenderer<TView,TNative>`) | **Handler** (`Microsoft.Maui.Handlers`) or a mapper on an existing handler |
| `DependencyService.Get<T>()` + `[assembly: Dependency]` | **DI**: register in `MauiProgram` (`builder.Services.AddSingleton<T>()`), inject via constructor |
| Platform effect (`PlatformEffect`, `[assembly: ExportEffect]`) | Handler mapper or platform-specific code |
| `Application.Properties` persistence | `Preferences` / `SecureStorage` |

## Step 5 — Verify

- `dotnet build -f net8.0-android` and `dotnet build -f net8.0-ios`.
- Smoke-check on an emulator/simulator that the Scandit SDK initializes and scans, per the impl skill's checklist.

## Hand off

The Scandit MAUI call sites (`<scandit:DataCaptureView>`, `BarcodeCaptureOverlay` created after the handler attaches, the `.UseScandit*()` chain) are verified by the product's **MAUI** skill — e.g. `barcode-capture-maui`, `sparkscan-maui`, `id-capture-net-maui`, `label-capture-net-maui`, `matrixscan-count-maui`. See `scandit-packages.md` for the product→skill mapping; use the `data-capture-sdk` router if the product is unclear.
