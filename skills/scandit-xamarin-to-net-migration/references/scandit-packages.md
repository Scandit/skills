# Scandit packages, APIs, and implementation-skill handoff

## Golden rule: fetch the version, never invent it

Before pinning any Scandit package, **WebFetch** its nuget.org page and read the latest **stable** version (skip `-beta.*` / `-preview.*` / `-rc.*`). Pin **every** Scandit package in the project to that same version. Inventing a version (e.g. `8.13.0` when only `8.4.0` is published) fails `dotnet restore` with `NU1103` / `Unable to find package …`.

- Barcode: `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/`
- Barcode MAUI: `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/`
- Profile (all Scandit packages): `https://www.nuget.org/profiles/Scandit`

If WebFetch fails, fall back to the flat-container index, e.g. `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last non-prerelease entry). The ID is lower-cased in that URL.

**To confirm an ID exists at all** — do this whenever you are about to write a package ID that is not literally in the table below, rather than trusting the naming pattern:

```bash
# 200 = the package exists, 404 = you invented it
curl -s -o /dev/null -w '%{http_code}\n' \
  https://api.nuget.org/v3-flatcontainer/<lowercased.package.id>/index.json
```

The full published set is small (27 IDs), so you can also list everything Scandit ships and check against it directly:

```bash
curl -s 'https://azuresearch-usnc.nuget.org/query?q=Scandit&take=100&prerelease=false' \
  | python3 -c 'import sys,json; [print(x["id"], x["version"]) for x in sorted(json.load(sys.stdin)["data"], key=lambda d: d["id"])]'
```

## Package name mapping (Xamarin → .NET)

The transform is: **strip the `.Xamarin` *or* `.Xamarin.Forms` suffix entirely.** On MAUI you *additionally* need the `.Maui` companions — but **only Core and Barcode have one** (see the warning below the table).

> **`.Xamarin` vs `.Xamarin.Forms`.** Xamarin.Forms projects reference the **`.Xamarin.Forms`**-suffixed IDs (`Scandit.DataCapture.Core.Xamarin.Forms`), not the plain `.Xamarin` ones — those are for native Xamarin.Android/iOS heads. Strip the *whole* suffix: `Scandit.DataCapture.Core.Xamarin.Forms` → `Scandit.DataCapture.Core`. Do **not** merely drop `.Xamarin`, which would leave `Scandit.DataCapture.Core.Forms` — that package does not exist and restore fails with `NU1101`.
>
> One exception to that rule: **Smart Label Capture never shipped a `.Xamarin.Forms` ID.** A Forms-origin Label project carries the plain `Scandit.DataCapture.Label.Xamarin`, so "no `.Xamarin.Forms` reference" does **not** prove the project is a native head — classify the target from the `.csproj` TFM (see `detection.md`), not from the Scandit suffix.
>
> The reason is that **Label has no Forms binding at all** — no `ScanditLabelCaptureUnified.dll`, and no `Unified` namespaces anywhere in `ScanditLabelCapture.dll` 7.6.14. Forms apps consumed it via the platform heads. Consequence for the migration: Label needs the package swap and initialization but **no namespace work whatsoever** — its `Scandit.DataCapture.Label.*` namespaces are already identical to the .NET binding's. See "Which products actually need this step" in `net-maui.md`.

| Xamarin package (last shipped 7.6.14) | .NET (net*-android / net*-ios) | .NET MAUI |
|---|---|---|
| `Scandit.DataCapture.Core.Xamarin` | `Scandit.DataCapture.Core` | `Scandit.DataCapture.Core` **+** `Scandit.DataCapture.Core.Maui` |
| `Scandit.DataCapture.Core.Xamarin.Forms` *(Forms projects)* | `Scandit.DataCapture.Core` | `Scandit.DataCapture.Core` **+** `Scandit.DataCapture.Core.Maui` |
| `Scandit.DataCapture.Barcode.Xamarin` | `Scandit.DataCapture.Barcode` | `Scandit.DataCapture.Barcode` **+** `Scandit.DataCapture.Barcode.Maui` |
| `Scandit.DataCapture.Barcode.Xamarin.Forms` *(Forms projects)* | `Scandit.DataCapture.Barcode` | `Scandit.DataCapture.Barcode` **+** `Scandit.DataCapture.Barcode.Maui` |
| `Scandit.DataCapture.IdCapture.Xamarin` | `Scandit.DataCapture.IdCapture` | `Scandit.DataCapture.IdCapture` — **no `.Maui` companion exists** |
| `Scandit.DataCapture.IdCapture.Xamarin.Forms` *(Forms projects)* | `Scandit.DataCapture.IdCapture` | `Scandit.DataCapture.IdCapture` — **no `.Maui` companion exists** |
| `Scandit.DataCapture.IdCapture.AamvaBarcodeVerification.Xamarin` | `Scandit.DataCapture.IdCapture.AamvaBarcodeVerification` | same — no `.Maui` companion |
| `Scandit.DataCapture.IdCapture.IdEuropeDrivingLicense.Xamarin` | `Scandit.DataCapture.IdCapture.IdEuropeDrivingLicense` | same — no `.Maui` companion |
| `Scandit.DataCapture.Label.Xamarin` *(no `.Xamarin.Forms` ID exists)* | `Scandit.DataCapture.Label` | `Scandit.DataCapture.Label` — **no `.Maui` companion exists** |
| `Scandit.DataCapture.Parser.Xamarin` | `Scandit.DataCapture.Parser` | `Scandit.DataCapture.Parser` — **no `.Maui` companion exists** |
| `Scandit.DataCapture.Parser.Xamarin.Forms` *(Forms projects)* | `Scandit.DataCapture.Parser` | `Scandit.DataCapture.Parser` — **no `.Maui` companion exists** |
| `Scandit.DataCapture.TextCapture.Xamarin(.Forms)` **(frozen at 6.28)** | **no 8.x equivalent** — see below | **no 8.x equivalent** — see below |
| `Scandit.BarcodePicker.Xamarin` / `.Unified` **(legacy v5 Barcode Picker)** | **no equivalent** | **no equivalent** |

> **`Scandit.DataCapture.Core.Maui` and `Scandit.DataCapture.Barcode.Maui` are the only `.Maui` packages Scandit publishes.** There is no `IdCapture.Maui`, `Label.Maui`, or `Parser.Maui` — adding one fails restore with `NU1101`. Products without a `.Maui` companion reuse the generic `<scandit:DataCaptureView>` from `Core.Maui`.

**The MAUI reference set is per-product, not a formula.** Take it from the product's `*-net-maui` skill rather than extrapolating; the three shipped shapes differ in both packages *and* initialization:

| Product | MAUI packages | MAUI initialization |
|---|---|---|
| Barcode Capture / SparkScan / MatrixScan | `Core`, `Core.Maui`, `Barcode`, `Barcode.Maui` | `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()` |
| ID Capture | `Core`, `Core.Maui`, `IdCapture` — **three, no Barcode** | `.UseScanditCore(c => c.AddDataCaptureView())` in `MauiProgram`, **plus** `ScanditIdCapture.Initialize()` in `Platforms/Android/MainApplication.OnCreate` *and* `Platforms/iOS/AppDelegate.FinishedLaunching` |
| Smart Label Capture | `Core`, `Core.Maui`, `Barcode`, `Label` — **no `Barcode.Maui`** | `ScanditLabelCapture.Initialize()` called directly in `MauiProgram`, plus `.UseScanditCore(c => c.AddDataCaptureView())` |

> **There is no `UseScanditIdCapture()` and no `UseScanditLabel()` builder extension.** `UseScanditCore` and `UseScanditBarcode` are the only two that exist. ID Capture and Smart Label Capture initialize through `Scandit*.Initialize()` calls instead — and in *different places* from each other, so do not copy one product's pattern to the other. Verify against `id-capture-net-maui` / `label-capture-net-maui` before writing the chain.
>
> Also note ID Capture's package ID and C# namespace disagree: the package is `Scandit.DataCapture.IdCapture`, the namespace is `using Scandit.DataCapture.ID;` (upper-case `ID`), and the initializer is `ScanditIdCapture.Initialize()`.

> **The product stem is `IdCapture`, not `Id`.** `Scandit.DataCapture.Id` does not exist. The IDs are `Scandit.DataCapture.IdCapture[.Xamarin|.Xamarin.Forms]`, plus the two optional add-on packages listed above for AAMVA barcode verification and European driving licences.

### Text Capture has no modern equivalent

`Scandit.DataCapture.TextCapture` / `.Xamarin` / `.Xamarin.Forms` all stop at **6.28.11**; there is no 7.x or 8.x release. Do **not** strip the suffix and pin "latest stable" — that lands a 6.28 package next to Core 8.5.2 and cannot work. Treat it like the legacy Barcode Picker: flag it to the user as a blocker with no package swap, and route them to a Scandit contact to discuss the replacement (usually Smart Label Capture or a Barcode Capture + Parser combination) before the migration continues.

### Legacy Barcode Picker (`Scandit.BarcodePicker.*`, v5)

This is the **v5** Barcode Picker API (`ScanditBarcodePicker`, `BarcodePicker`, `ScanSettings`), not the modern Data Capture SDK. There is no package swap — it is a **reintegration** onto Barcode Capture or SparkScan. Flag it as manual-only and hand off to `barcode-capture-net-*` / `barcode-capture-net-maui` / `sparkscan-*` for a fresh integration.

The whole v5 family is frozen at **5.19.3.10**, and it has more than one ID — grepping only for `Scandit.BarcodePicker.Xamarin` misses the Forms flavour:

| v5 package | Where it came from |
|---|---|
| `Scandit.BarcodePicker.Xamarin` | native Xamarin.Android / Xamarin.iOS head |
| `Scandit.BarcodePicker.Unified` | **Xamarin.Forms** — so this is the one most likely heading for MAUI |
| `Scandit.BarcodePicker` | pre-Xamarin / .NET Framework |
| `Scandit.Recognition` | low-level v5 recognition engine |

Note the naming collision: `.Unified` here marks the **Forms** flavour of the *v5 picker*, whereas in the Data Capture SDK `.Unified` marks a *namespace* inside the Forms binding (see the rename in `net-maui.md`). They are unrelated; do not treat a `Scandit.BarcodePicker.Unified` reference as something the namespace rename applies to.

## Call-site API changes

For a project already on the **Data Capture SDK Xamarin** binding (6.x/7.x), the C# API is largely identical to the .NET binding — the same PascalCase factories, listener interfaces, and symbology names. The changes are:

1. **SDK 8.0+ explicit initialization** (non-MAUI): add `ScanditCaptureCore.Initialize()` + the per-product `Scandit*.Initialize()` at startup (see `net-android.md` / `net-ios.md`). MAUI initializes via the `.UseScandit*()` builder chain instead.
2. **Any 6→7 / 7→8 SDK-version deltas** for the specific product (camera-settings, scan-intention, composite-codes defaults, etc.). These are **not** Xamarin→.NET changes — they are Scandit major-version changes and are documented per product in the implementation skill's `migration.md`. Apply them there, not here.

Do not attempt to rewrite Scandit call sites from memory. Hand off.

## Product → implementation skill

Identify the product from the Scandit entry points found during detection, then hand off to the matching skill for the target platform:

| Scandit entry point (detected) | Product | .NET package it lives in | net*-android | net*-ios | MAUI |
|---|---|---|---|---|---|
| `BarcodeCapture` | Barcode Capture | `Scandit.DataCapture.Barcode` | `barcode-capture-net-android` | `barcode-capture-net-ios` | `barcode-capture-net-maui` |
| `SparkScanView` / `SparkScan` | SparkScan | `Scandit.DataCapture.Barcode` | `sparkscan-net-android` | `sparkscan-net-ios` | `sparkscan-net-maui` |
| `BarcodeCount` | MatrixScan Count | `Scandit.DataCapture.Barcode` | `matrixscan-count-net-android` | `matrixscan-count-net-ios` | `matrixscan-count-net-maui` |
| `BarcodeBatch` / `BarcodeTracking` | MatrixScan Batch | `Scandit.DataCapture.Barcode` | `matrixscan-batch-net-android` | `matrixscan-batch-net-ios` | `matrixscan-batch-net-maui` |
| `BarcodeAr` | MatrixScan AR | `Scandit.DataCapture.Barcode` | `matrixscan-ar-net-android` | `matrixscan-ar-net-ios` | `matrixscan-ar-net-maui` |
| `LabelCapture` | Smart Label Capture | `Scandit.DataCapture.Label` | `label-capture-net-android` | `label-capture-net-ios` | `label-capture-net-maui` |
| `IdCapture` | ID Capture | `Scandit.DataCapture.IdCapture` | `id-capture-net-android` | `id-capture-net-ios` | `id-capture-net-maui` |
| `TextCapture` | Text Capture | **none — frozen at 6.28**, no 8.x | — | — | — |
| `ScanditBarcodePicker` / `BarcodePicker` | legacy v5 picker | **none** — reintegration | route to Barcode Capture / SparkScan | ditto | ditto |

All five Barcode-family products share the single `Scandit.DataCapture.Barcode` package (plus `Scandit.DataCapture.Barcode.Maui` on MAUI) — so the package set does not tell you which product the app uses. Identify that from the entry-point types, and remember the per-product `Scandit*.Initialize()` call and the handoff skill both depend on getting it right.

If the product is unclear, hand off to the **`data-capture-sdk`** router skill, which identifies the product and names the correct implementation skill. If a specific product×platform skill does not exist, the router falls back to the matching sample app.
