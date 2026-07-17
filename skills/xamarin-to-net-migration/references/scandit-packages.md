# Scandit packages, APIs, and implementation-skill handoff

## Golden rule: fetch the version, never invent it

Before pinning any Scandit package, **WebFetch** its nuget.org page and read the latest **stable** version (skip `-beta.*` / `-preview.*` / `-rc.*`). Pin **every** Scandit package in the project to that same version. Inventing a version (e.g. `8.13.0` when only `8.4.0` is published) fails `dotnet restore` with `NU1103` / `Unable to find package …`.

- Barcode: `https://www.nuget.org/packages/Scandit.DataCapture.Barcode/`
- Barcode MAUI: `https://www.nuget.org/packages/Scandit.DataCapture.Barcode.Maui/`
- Profile (all Scandit packages): `https://www.nuget.org/profiles/Scandit`

If WebFetch fails, fall back to the flat-container index, e.g. `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.barcode/index.json` (last non-prerelease entry).

## Package name mapping (Xamarin → .NET)

The transform is: **drop the `.Xamarin` suffix**; for MAUI, **add** the `*.Maui` companion for each package.

| Xamarin package | .NET (net*-android / net*-ios) | .NET MAUI |
|---|---|---|
| `Scandit.DataCapture.Core.Xamarin` | `Scandit.DataCapture.Core` | `Scandit.DataCapture.Core` **+** `Scandit.DataCapture.Core.Maui` |
| `Scandit.DataCapture.Barcode.Xamarin` | `Scandit.DataCapture.Barcode` | `Scandit.DataCapture.Barcode` **+** `Scandit.DataCapture.Barcode.Maui` |
| `Scandit.DataCapture.Parser.Xamarin` | `Scandit.DataCapture.Parser` | `Scandit.DataCapture.Parser` (+ `.Maui` if a companion exists — verify on nuget.org) |
| `Scandit.DataCapture.Id.Xamarin` *(verify exact id)* | `Scandit.DataCapture.Id` | `Scandit.DataCapture.Id` **+** `Scandit.DataCapture.Id.Maui` |
| `Scandit.DataCapture.Label.Xamarin` *(verify exact id)* | `Scandit.DataCapture.Label` | `Scandit.DataCapture.Label` **+** `Scandit.DataCapture.Label.Maui` |
| `Scandit.BarcodePicker.Xamarin` **(legacy v5 Barcode Picker)** | **no equivalent** | **no equivalent** |

Always confirm the exact `.Id` / `.Label` / `.Parser` package IDs and the existence of a `*.Maui` companion on nuget.org — do not assume from the pattern alone.

### Legacy Barcode Picker (`Scandit.BarcodePicker.Xamarin`)

This is the **v5** Barcode Picker API (`ScanditBarcodePicker`, `BarcodePicker`, `ScanSettings`), not the modern Data Capture SDK. There is no package swap — it is a **reintegration** onto Barcode Capture or SparkScan. Flag it as manual-only and hand off to `barcode-capture-net-*` / `barcode-capture-maui` / `sparkscan-*` for a fresh integration.

## Call-site API changes

For a project already on the **Data Capture SDK Xamarin** binding (6.x/7.x), the C# API is largely identical to the .NET binding — the same PascalCase factories, listener interfaces, and symbology names. The changes are:

1. **SDK 8.0+ explicit initialization** (non-MAUI): add `ScanditCaptureCore.Initialize()` + the per-product `Scandit*.Initialize()` at startup (see `migrate-android.md` / `migrate-ios.md`). MAUI initializes via the `.UseScandit*()` builder chain instead.
2. **Any 6→7 / 7→8 SDK-version deltas** for the specific product (camera-settings, scan-intention, composite-codes defaults, etc.). These are **not** Xamarin→.NET changes — they are Scandit major-version changes and are documented per product in the implementation skill's `migration.md`. Apply them there, not here.

Do not attempt to rewrite Scandit call sites from memory. Hand off.

## Product → implementation skill

Identify the product from the Scandit entry points found during detection, then hand off to the matching skill for the target platform:

| Scandit entry point (detected) | Product | net*-android | net*-ios | MAUI |
|---|---|---|---|---|
| `BarcodeCapture` | Barcode Capture | `barcode-capture-net-android` | `barcode-capture-net-ios` | `barcode-capture-maui` |
| `SparkScanView` / `SparkScan` | SparkScan | `sparkscan-net-android` | `sparkscan-net-ios` | `sparkscan-maui` |
| `BarcodeCount` | MatrixScan Count | `matrixscan-count-net-android` | `matrixscan-count-net-ios` | `matrixscan-count-maui` |
| `BarcodeBatch` / `BarcodeTracking` | MatrixScan Batch | `matrixscan-batch-net-android` | `matrixscan-batch-net-ios` | `matrixscan-batch-maui` |
| `BarcodeAr` | MatrixScan AR | `matrixscan-ar-net-android` | `matrixscan-ar-net-ios` | `matrixscan-ar-maui` |
| `LabelCapture` | Smart Label Capture | `label-capture-net-android` | `label-capture-net-ios` | `label-capture-net-maui` |
| `IdCapture` | ID Capture | `id-capture-net-android` | `id-capture-net-ios` | `id-capture-net-maui` |

If the product is unclear, hand off to the **`data-capture-sdk`** router skill, which identifies the product and names the correct implementation skill. If a specific product×platform skill does not exist, the router falls back to the matching sample app.
