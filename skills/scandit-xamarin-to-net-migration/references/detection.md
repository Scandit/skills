# Detection — confirm the precondition, then classify the Scandit remnants

Run this **first**, and again at the start of every resumed session. It is the precondition gate, the target-platform classifier, and the idempotency check: any Scandit step whose target state is already present is skipped rather than redone.

## Precondition — is the app already on .NET/MAUI?

This skill only runs on a project that has **already** been migrated to the .NET stack. Decide with the `.csproj`:

| The project is… | Signals | Action |
|---|---|---|
| **Already .NET / MAUI** (proceed) | `<Project Sdk="Microsoft.NET.Sdk">`; `<TargetFramework>net*-android</TargetFramework>` / `net*-ios`; or `<UseMaui>true</UseMaui>` with `<TargetFrameworks>net*-android;net*-ios</TargetFrameworks>`; `<PackageReference>` deps (no `packages.config`). | Continue below. |
| **Still Xamarin** (stop) | `<TargetFrameworkVersion>` like `v13.0`; `<TargetFrameworkIdentifier>MonoAndroid</TargetFrameworkIdentifier>`; imports `Xamarin.Android.CSharp.targets` / `Xamarin.iOS.CSharp.targets` / `Xamarin.Forms.targets`; a `<PackageReference Include="Xamarin.Forms">`; a `packages.config`; verbose legacy `.csproj` with explicit `<Compile Include>` items. | **Stop.** The general app migration is out of scope. Tell the user to run Microsoft's .NET app-modernization tooling first — the [GitHub Copilot app‑modernization / upgrade agent](https://learn.microsoft.com/en-us/dotnet/core/porting/github-copilot-upgrade/overview) (the recommended successor to the now‑deprecated [.NET Upgrade Assistant](https://learn.microsoft.com/en-us/dotnet/core/porting/upgrade-assistant-overview)) — and offer to do the Scandit part once the app is on .NET/MAUI. Do **not** convert the project yourself. |

Do not proceed past this gate on a still-Xamarin project — that is a deliberate scope boundary, not a limitation to work around.

## Step 1 — Classify the target platform

For an already-.NET project, the platform is the TFM, and it maps 1:1 to the migration reference and the implementation-skill suffix:

| Target | Signals | Reference | Handoff suffix |
|---|---|---|---|
| **.NET for Android** | single `<TargetFramework>net*-android</TargetFramework>`, no `<UseMaui>` | `net-android.md` | `-net-android` |
| **.NET for iOS** | single `<TargetFramework>net*-ios</TargetFramework>`, no `<UseMaui>` | `net-ios.md` | `-net-ios` |
| **.NET MAUI** | `<UseMaui>true</UseMaui>`, `<TargetFrameworks>` with both `net*-android` and `net*-ios` | `net-maui.md` | `-net-maui` |

A project that came from **Xamarin.Forms** lands on **MAUI** — this is the path where the Scandit `.Unified` namespace rename and the `BarcodeCaptureOverlay` relocation apply.

## Step 2 — Find the Scandit remnants left by the general migration

Microsoft's app-modernization tooling does not know about Scandit, so it typically leaves the old Scandit references in place (or produces build errors around them). Grep for what still needs fixing:

**a) Packages** — search `.csproj` / `Directory.Packages.props` (and any leftover `packages.config`) and record the **exact version**. Match on the `Scandit.DataCapture.<Product>` stem and treat a trailing `.Xamarin` *or* `.Xamarin.Forms` as the same thing — a Forms-origin project uses the `.Xamarin.Forms` IDs, so a grep for `.Xamarin"` alone will miss it.

| Package still referenced | Meaning |
|---|---|
| `Scandit.DataCapture.Core.Xamarin` | Core — always present in a Data Capture SDK integration. |
| `Scandit.DataCapture.Core.Xamarin.Forms` | Core, **Forms-origin** — the project is on MAUI and the `.Unified` namespaces are in use (see the `Unified` → plain rename in `net-maui.md`). |
| `Scandit.DataCapture.Barcode.Xamarin(.Forms)` | Barcode Capture / MatrixScan / SparkScan API. |
| `Scandit.DataCapture.Parser.Xamarin` | Parser API. |
| `Scandit.DataCapture.Id.Xamarin` / `...Label.Xamarin` | ID Capture / Smart Label Capture (confirm the exact ID on nuget.org). |
| `Scandit.BarcodePicker.Xamarin` | **Legacy v5 Barcode Picker** — no direct modern equivalent; a reintegration, route to a Barcode Capture / SparkScan skill. |

**b) Namespaces** — grep `.cs` for `Scandit.DataCapture.*.Unified` (C# usings) and `.xaml` for `xmlns:...="clr-namespace:Scandit...Unified;assembly=Scandit*Unified"`. Their presence confirms a Forms-origin (MAUI) project that still needs the Scandit namespace rename.

**c) Initialization** — grep for `ScanditCaptureCore.Initialize` and `.UseScanditCore(`. Absence on Android/iOS means SDK-8 init still needs adding; absence in `MauiProgram` means the `.UseScandit*()` chain is missing.

**d) Product entry points** — grep for `DataCaptureContext`, `BarcodeCapture`, `SparkScan`, `BarcodeCount`, `BarcodeBatch`/`BarcodeTracking`, `BarcodeAr`, `LabelCapture`, `IdCapture`, `ScanditBarcodePicker` (legacy). This tells you which implementation skill to hand off to.

## Step 3 — Record the Scandit surface as a parity baseline

Save the Scandit XAML elements and symbols now, so Phase 5 can prove none were lost:

```bash
git grep -IohE 'scandit[A-Za-z]*:[A-Za-z]+|UseScandit[A-Za-z]*|BarcodeCaptureOverlay|DataCaptureView|IBarcodeCaptureListener' -- . ':(exclude)**/obj/**' ':(exclude)**/bin/**' | sort -u
```

Note in particular every `<scanditCore:…>` / `<scanditBarcode:…>` element in the XAML and every `IBarcodeCaptureListener` implementation — these are the constructs most often lost during a MAUI rewrite.

## Out of scope — do not migrate these

If detection also surfaces general-migration leftovers — custom renderers (`ExportRenderer`, `: ViewRenderer<…>`), `DependencyService`, platform effects, `MessagingCenter`, third-party packages without a .NET equivalent — they are **not** this skill's job. They belong to Microsoft's app-modernization tooling and the customer's team. Do not migrate them and do not delete them to force a build; if one is actively blocking the Scandit build, note it to the user as a general-migration item and continue with the Scandit slice.

The one exception this skill *does* own is a `Scandit.BarcodePicker.Xamarin` reference — that is a Scandit reintegration (Step 2a), routed to a Barcode Capture / SparkScan skill.

## Detection output

Summarize as a compact block, e.g.:

```
Precondition:   PASS — project is .NET MAUI (net8.0-android;net8.0-ios, UseMaui true)
Target:         .NET MAUI  → net-maui.md, handoff *-net-maui
Scandit pkgs:   Scandit.DataCapture.Core.Xamarin.Forms 6.28, Scandit.DataCapture.Barcode.Xamarin.Forms 6.28  (need swap + .Maui companions)
Scandit ns:     .Unified usings in ScannerPage.xaml.cs + scandit:...Unified xmlns in ScanPage.xaml  (need rename)
Init:           no .UseScanditCore( in MauiProgram  (need builder chain)
Product:        BarcodeCapture (IBarcodeCaptureListener in ScannerPage.xaml.cs)  → barcode-capture-net-maui
```

This block drives Phases 3–5 and, later, the migration report.
