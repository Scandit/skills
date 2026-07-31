# Xamarin.Forms → .NET MAUI

This is the largest of the three paths: a Forms solution (a shared `.Forms` project + `.Android`/`.iOS` heads) collapses into **one** multi-target MAUI project. Always work on a branch/backup.

> **Before you write any Scandit MAUI code, load the product's `*-net-maui` implementation skill** (e.g. `barcode-capture-net-maui`). It holds the exact XAML `xmlns`, assembly names, and builder-chain signatures. Guessing these is the #1 cause of a bogus "the Scandit MAUI API doesn't exist" conclusion — followed by someone deleting the scanner to get a green build. Do not do that; see the no-gutting invariant in `SKILL.md`.

## Step 0 — Resolve the TFM from the installed toolchain

Do not hardcode a TFM. Run:

```bash
dotnet --version
dotnet workload list      # need: maui / maui-android / maui-ios
```

Target the newest `net*` for which the customer actually has workload manifests. A `net8.0-android` target on a machine with only the .NET 10 SDK fails to restore, and `net10.0-android` carries the kotlinx caveat below. Use the TFM you resolve here consistently in the `.csproj` **and** in every `dotnet build -f …` command you run and report. The examples below write `net8.0-*`; substitute your resolved TFM throughout.

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

**The three `using` directives below are mandatory** — the `UseScandit*` methods are extension methods, so without them the calls do not resolve and you get `CS1061: 'MauiAppBuilder' has no method 'UseScanditCore'`. That error means **a missing `using`, not a missing API**; add the `using` and never resolve it by commenting out the chain (see the no-gutting invariant in `SKILL.md`).

```csharp
using Scandit.DataCapture.Core;          // UseScanditCore
using Scandit.DataCapture.Core.UI.Maui;  // AddDataCaptureView
using Scandit.DataCapture.Barcode;       // UseScanditBarcode  (per product — see impl skill)

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .UseScanditCore(configure => configure.AddDataCaptureView())
            .UseScanditBarcode();          // takes NO inner configure
        return builder.Build();
    }
}
```

Note the namespaces are counter-intuitive: `UseScanditCore` is in the bare `Scandit.DataCapture.Core` namespace (not `...Core.UI.Maui`, and not a `.Hosting` namespace), while `AddDataCaptureView` is in `Scandit.DataCapture.Core.UI.Maui`. Do not guess these — they are documented in `barcode-capture-net-maui/references/integration.md`. `UseScanditBarcode()` takes no inner configure lambda; `UseScanditBarcode(c => c.AddBarcodeCaptureView())` does not exist.

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

Note the source IDs in a Forms project are `Scandit.DataCapture.Core.Xamarin.Forms` / `Scandit.DataCapture.Barcode.Xamarin.Forms` — strip the **whole** `.Xamarin.Forms` suffix, not just `.Xamarin`.

### Android kotlinx-serialization override (required on `net10.0-android`)

Scandit's Android AAR chain declares a transitive `Org.Jetbrains.Kotlinx.KotlinxSerializationJson` that only targets `net8.0-android`/`net9.0-android`. On `net10.0-android` the JAR is fetched but never injected into the app's library chain, so the project **builds clean and crashes at the first scan** with `Java.Lang.NoClassDefFoundError: Failed resolution of: Lkotlinx/serialization/json/JsonKt;`. If your resolved TFM is `net10.0-android`, add:

```xml
<ItemGroup Condition="$([MSBuild]::GetTargetPlatformIdentifier('$(TargetFramework)')) == 'android'">
  <PackageReference Include="Org.Jetbrains.Kotlinx.KotlinxSerializationJson"    Version="1.7.3" ExcludeAssets="all" />
  <PackageReference Include="Org.Jetbrains.Kotlinx.KotlinxSerializationJsonJvm" Version="1.7.3" ExcludeAssets="all" />
  <PackageReference Include="Xamarin.KotlinX.Serialization.Json" Version="1.11.0" />
</ItemGroup>
```

Both `ExcludeAssets="all"` lines are required — leaving the `Jvm` one active produces `XA4215` "Java type generated by more than one managed type". A green build does **not** indicate this is handled; only a real scan does.

## Step 3b — Scandit namespace rename (`Unified` → `Maui`)

**This is the highest-volume mechanical edit in a Forms migration and it is easy to miss** — the Forms binding ships `.Unified` namespaces and `Scandit*Unified` assemblies; the MAUI binding does not. Two distinct transforms:

**C# `using` directives — drop the `.Unified` segment:**

| Xamarin.Forms binding | .NET MAUI binding |
|---|---|
| `Scandit.DataCapture.Core.Capture.Unified` | `Scandit.DataCapture.Core.Capture` |
| `Scandit.DataCapture.Core.Source.Unified` | `Scandit.DataCapture.Core.Source` |
| `Scandit.DataCapture.Core.Common.Feedback.Unified` | `Scandit.DataCapture.Core.Common.Feedback` |
| `Scandit.DataCapture.Core.Data.Unified` | `Scandit.DataCapture.Core.Data` |
| `Scandit.DataCapture.Core.UI.Viewfinder.Unified` | `Scandit.DataCapture.Core.UI.Viewfinder` |
| `Scandit.DataCapture.Barcode.Capture.Unified` | `Scandit.DataCapture.Barcode.Capture` |
| `Scandit.DataCapture.Barcode.Data.Unified` | `Scandit.DataCapture.Barcode.Data` |

A blanket `Scandit.DataCapture.(.*)\.Unified` → `Scandit.DataCapture.$1` regex over `.cs` files handles these.

**XAML `xmlns` — do not assume a symmetric `Unified` → `Maui` swap per product.** Only *some* Scandit UI types are MAUI XAML elements. The one that reliably is:

| Xamarin.Forms XAML | .NET MAUI XAML |
|---|---|
| `clr-namespace:Scandit.DataCapture.Core.UI.Unified;assembly=ScanditCaptureCoreUnified` | `clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui` |

`<scandit:DataCaptureView>` keeps its `DataCaptureContext="{Binding DataCaptureContext}"` binding — it is **mandatory**, and without it the preview renders black at runtime even though everything compiles.

### `BarcodeCaptureOverlay` is NOT a MAUI XAML element — it moves to code-behind

There is **no** `Scandit.DataCapture.Barcode.UI.Maui` namespace. `ScanditBarcodeCaptureMaui` only ships MAUI views for products that have a pre-built view — `Barcode.Spark.UI.Maui`, `Barcode.Count.UI.Maui`, `Barcode.Find.UI.Maui`, `Barcode.Pick.UI.Maui`, `Barcode.Ar.UI.Maui`. Plain Barcode Capture has none. `BarcodeCaptureOverlay` lives in `Scandit.DataCapture.Barcode.UI.Overlay` in the **plain** `Scandit.DataCapture.Barcode` package and is a runtime object, not a control.

So a Forms page like this:

```xml
<scanditCore:DataCaptureView DataCaptureContext="{Binding DataCaptureContext}">
    <scanditBarcode:BarcodeCaptureOverlay BarcodeCapture="{Binding BarcodeCapture}"
                                          Viewfinder="{Binding Viewfinder}" />
</scanditCore:DataCaptureView>
```

becomes a **self-closing** `DataCaptureView` in XAML (give it an `x:Name`, drop the `scanditBarcode` xmlns entirely) plus this in the code-behind — the overlay must be created **after** the platform handler attaches, or it silently fails to appear:

```csharp
using Scandit.DataCapture.Barcode.UI.Overlay;

this.dataCaptureView.HandlerChanged += (s, e) =>
{
    var overlay = BarcodeCaptureOverlay.Create(this.viewModel.BarcodeCapture);
    overlay.Viewfinder = this.viewModel.Viewfinder;   // was a XAML binding in Forms
    this.dataCaptureView.AddOverlay(overlay);
};
```

**This relocation is expected and is not a violation of the no-gutting invariant** — the overlay still exists, it moved from markup to code. What *is* a violation is deleting the overlay without recreating it. The Phase 5 parity check should show `BarcodeCaptureOverlay` still present in the source, just in a `.cs` file rather than a `.xaml` one.

Before writing any Scandit MAUI markup, confirm which types are XAML elements against the product's `*-net-maui` skill — it is authoritative. If an `xmlns` fails to resolve, either the string is wrong **or the type is not a XAML element at all**; check which before changing anything, and never resolve it by deleting the construct. To verify directly:

```bash
strings ~/.nuget/packages/scandit.datacapture.barcode.maui/<version>/lib/<tfm>/ScanditBarcodeCaptureMaui.dll | grep 'UI.Maui'
```

## Step 4 — Migrate the manual-only Forms constructs

These do **not** convert mechanically — flag each and migrate deliberately:

| Xamarin.Forms construct | .NET MAUI equivalent |
|---|---|
| Custom renderer (`ExportRenderer`, `ViewRenderer<TView,TNative>`) | **Handler** (`Microsoft.Maui.Handlers`) or a mapper on an existing handler |
| `DependencyService.Get<T>()` + `[assembly: Dependency]` | **DI**: register in `MauiProgram` (`builder.Services.AddSingleton<T>()`), inject via constructor |
| Platform effect (`PlatformEffect`, `[assembly: ExportEffect]`) | Handler mapper or platform-specific code |
| `Application.Properties` persistence | `Preferences` / `SecureStorage` |
| `Xamarin.Essentials` permissions (`Permissions.Camera`) | `Microsoft.Maui.ApplicationModel.Permissions` — same `CheckStatusAsync<Permissions.Camera>()` / `RequestAsync<…>()` shape, new namespace |
| `MessagingCenter.Send/Subscribe` | Obsolete in MAUI — use `WeakReferenceMessenger` (CommunityToolkit.Mvvm) or wire the `App` lifecycle events directly |
| `App.MainPage = new MainPage()` | Set `MainPage` via `new Window(new MainPage())` from `CreateWindow` — the `MainPage` setter is deprecated in MAUI 9+ |
| `Page.DisplayAlert(...)` | `await DisplayAlertAsync(...)` — the non-async overload is obsolete in MAUI 9+ (`CS0618`) |

## Step 5 — Verify

1. **Integration parity first.** Confirm you did not lose any Scandit code (see the Phase 5 check in `SKILL.md`):
   ```bash
   git diff <start-sha> -- '*.xaml' '*.cs' | grep -E '^-.*(scandit|Scandit|UseScandit)'
   ```
   Every removed Scandit line must correspond to a rename in Step 3b. A removed `<scandit:DataCaptureView>`, a commented-out `.UseScandit*()`, or a scanning page replaced by a placeholder is a **failed migration**, not a partial one.
2. `dotnet build -f <your-android-tfm>` and `dotnet build -f <your-ios-tfm>`.
3. Smoke-check on an emulator/simulator that the Scandit SDK initializes **and scans**, per the impl skill's checklist. Required on `net10.0-android`, where a clean build hides the kotlinx crash.

## Hand off

The Scandit MAUI call sites (`<scandit:DataCaptureView>`, `BarcodeCaptureOverlay` created after the handler attaches, the `.UseScandit*()` chain) are verified by the product's **MAUI** skill — e.g. `barcode-capture-net-maui`, `sparkscan-net-maui`, `id-capture-net-maui`, `label-capture-net-maui`, `matrixscan-count-net-maui`. See `scandit-packages.md` for the product→skill mapping; use the `data-capture-sdk` router if the product is unclear.
