# Detection — classify the Xamarin project

Run this **first**, and again at the start of every resumed session. It is both the classifier and the idempotency check: any step whose target state is already present is skipped rather than redone.

## Step 1 — Locate the project files

Search the repository for:

- `*.csproj`, `*.sln` — the projects to migrate.
- `Info.plist`, `Entitlements.plist` — iOS.
- `AndroidManifest.xml`, `Resources/` — Android.
- `App.xaml` / `App.xaml.cs`, `*.xaml` — Forms/MAUI UI.
- `packages.config` — a strong signal of a **legacy** (non-SDK-style) project.

## Step 2 — Classify the Xamarin flavour

Inspect each `.csproj`. The signals below are ordered most → least reliable.

| Flavour | Signals |
|---|---|
| **Xamarin.Android** | `<Project ... >` imports `Xamarin.Android.CSharp.targets`; `<TargetFrameworkIdentifier>MonoAndroid</TargetFrameworkIdentifier>`; `<TargetFrameworkVersion>` like `v13.0`; references `Mono.Android`. |
| **Xamarin.iOS** | imports `Xamarin.iOS.CSharp.targets`; references `Xamarin.iOS`; has an `Info.plist` + `Entitlements.plist`; `<MtouchArch>` present. |
| **Xamarin.Forms** | any of the above **plus** a `<PackageReference Include="Xamarin.Forms" ... />` (or `packages.config` entry), usually a shared/head project referencing platform `.Android`/`.iOS` head projects, and `App.xaml`. |

A Forms solution is typically **three projects**: a shared `.Forms` project plus `.Android` and `.iOS` heads. Migrating it means collapsing to a single multi-target MAUI project (see `migrate-forms-maui.md`).

## Step 3 — Determine the project style

| Style | How to tell | Implication |
|---|---|---|
| **Legacy** | Verbose `.csproj` with explicit `<Compile Include=...>` items, a `packages.config`, `<Project ToolsVersion=...>`, no `<Project Sdk=...>` attribute. | Full conversion to SDK-style needed. |
| **SDK-style** | `<Project Sdk="Microsoft.NET.Sdk" ...>` (or `.Sdk.Razor`), `<PackageReference>` for deps, implicit globbing (no per-file `<Compile>`). | Only the TFM + packages + bootstrap change. |

## Step 4 — Identify the Scandit integration

Search `.csproj` / `packages.config` / `Directory.Packages.props` for Scandit package references and record the **exact version**:

Match on the **`Scandit.DataCapture.<Product>`** stem and treat a trailing `.Xamarin` *or* `.Xamarin.Forms` as the same thing — a Forms project uses the `.Xamarin.Forms` IDs, so a grep for `.Xamarin"` alone will miss it.

| Package referenced | Meaning |
|---|---|
| `Scandit.DataCapture.Core.Xamarin` | Core — always present in a Data Capture SDK integration. |
| `Scandit.DataCapture.Core.Xamarin.Forms` | Core, **Forms** flavour — confirms Xamarin.Forms and implies the `.Unified` namespaces are in use (see the `Unified` → `Maui` rename in `migrate-forms-maui.md`). |
| `Scandit.DataCapture.Barcode.Xamarin` | Barcode Capture / MatrixScan / SparkScan API. |
| `Scandit.DataCapture.Barcode.Xamarin.Forms` | Same, **Forms** flavour. |
| `Scandit.DataCapture.Parser.Xamarin` | Parser API. |
| `Scandit.DataCapture.Id.Xamarin` / `...Label.Xamarin` | ID Capture / Smart Label Capture (confirm the exact ID on nuget.org). |
| `Scandit.BarcodePicker.Xamarin` | **Legacy v5 Barcode Picker** — no direct modern equivalent; a reintegration, flag manual. |

Also grep the source for the Scandit entry points to know which product's implementation skill to hand off to: `DataCaptureContext`, `BarcodeCapture`, `SparkScan`, `BarcodeCount`, `BarcodeBatch`/`BarcodeTracking`, `BarcodeAr`, `LabelCapture`, `IdCapture`, `ScanditBarcodePicker` (legacy).

**Record the Scandit surface as a baseline for the Phase 5 parity check.** Save the list of Scandit XAML elements and symbols now, so Phase 5 can prove none were lost:

```bash
git grep -IohE 'scandit[A-Za-z]*:[A-Za-z]+|UseScandit[A-Za-z]*|BarcodeCaptureOverlay|DataCaptureView|IBarcodeCaptureListener' -- . ':(exclude)**/obj/**' ':(exclude)**/bin/**' | sort -u
```

Note in particular every `<scanditCore:…>` / `<scanditBarcode:…>` element in the XAML and every `IBarcodeCaptureListener` implementation — these are the constructs most often lost during a Forms→MAUI rewrite.

## Step 5 — Flag manual-only items

Record anything that will **not** migrate mechanically, so Phase 2 can surface it:

- Custom renderers (`ExportRenderer`, `: ViewRenderer<…>`) → become MAUI **handlers**.
- `DependencyService` registrations/usages → become **DI** (`builder.Services.Add…`).
- Platform effects (`: PlatformEffect`), `[assembly: ResolutionGroupName]`, `[assembly: ExportEffect]`.
- Third-party NuGet packages with no .NET/MAUI-compatible version.
- `AssemblyInfo.cs` attributes that move into the SDK-style `.csproj`.

## Detection output

Summarize as a compact block, e.g.:

```
Flavour:        Xamarin.Forms (Forms 5.0.0; .Android + .iOS heads)
Project style:  legacy (.csproj + packages.config)
Current TFMs:   MonoAndroid13.0 / Xamarin.iOS10
Scandit:        Scandit.DataCapture.Core.Xamarin 6.28, Scandit.DataCapture.Barcode.Xamarin 6.28
Scandit entry:  BarcodeCapture (IBarcodeCaptureListener in ScannerPage.xaml.cs)
Manual items:   1 custom renderer (BadgeView), DependencyService IAudioService, package Acr.UserDialogs
```

This block drives the plan and, later, the migration report.
