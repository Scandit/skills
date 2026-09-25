# ID Capture .NET for Android Migration Guide

This guide covers upgrading an existing **ID Capture** integration on the non-MAUI `.NET for Android` workload across major Scandit SDK versions. ID Capture first shipped on `dotnet.android` in **6.16**, so a project may legitimately be on a 6.x, 7.x, or 8.x line.

Two changes dominate the upgrade path:

- **6 → 7** completely redesigned ID Capture: the v6 `SupportedDocuments` (`IdDocumentType` bitmask) + `SupportedSides` model was removed and replaced by an explicit `AcceptedDocuments` list plus a `Scanner` (`IdCaptureScanner`). This is **compile-breaking** — old code will not build against 7.x.
- **7 → 8** is mostly the .NET architecture redesign: the SDK now requires **explicit initialization at process start**, or the app crashes on the first Scandit call. ID Capture itself gains the settings-driven verification result model.

Do not guess at the old or new signatures. Follow the concrete before/after below, and verify anything not covered against the [ID Capture API reference (.NET Android)](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api.html).

---

## Step 1: Detect the installed SDK version

Before making any changes, find out which version the project has. Check `.csproj` (and `Directory.Packages.props` if Central Package Management is in use) for:

```xml
<PackageReference Include="Scandit.DataCapture.Core" Version="..." />
<PackageReference Include="Scandit.DataCapture.IdCapture" Version="..." />
```

Both packages should be pinned to the **same** version. If they drift, treat the lowest as the installed one. Then pick the migration path:

| Installed version | Target | Action |
|---|---|---|
| 6.16–6.x (`dotnet.android >= 6.16`) | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6 → 7 first, then 7 → 8) |

If you cannot find the version, ask the user which version they are migrating from. ID Capture does not exist on `dotnet.android` below 6.16 — confirm with the user before assuming an older version.

A quick way to tell which API era the **code** is in:

- Uses `settings.SupportedDocuments` (an `IdDocumentType` bitmask) and/or `settings.SupportedSides` → **v6 code**; apply 6 → 7 (then 7 → 8 if targeting 8.x).
- Uses `settings.AcceptedDocuments` + `settings.Scanner` but no `MainApplication` `Initialize()` calls → **v7 code**; apply 7 → 8.
- Already uses `AcceptedDocuments` + `Scanner` **and** calls `ScanditCaptureCore.Initialize()` / `ScanditIdCapture.Initialize()` → already on 8.x; only the optional adoptions apply.

---

## Step 2: Update the dependency version

Before touching source files, **WebFetch** `https://www.nuget.org/packages/Scandit.DataCapture.IdCapture/` and read the latest stable version. Then set that exact version on **both** `<PackageReference>` entries:

- `Scandit.DataCapture.Core`
- `Scandit.DataCapture.IdCapture`

Do **not** guess — the latest stable changes regularly and only the live NuGet page is authoritative. If `WebFetch` fails, fall back to `https://api.nuget.org/v3-flatcontainer/scandit.datacapture.idcapture/index.json` (last entry without a pre-release suffix). There is **no** separate Barcode package — the PDF417/AAMVA reader is bundled in `Scandit.DataCapture.IdCapture`.

Restore packages (`dotnet restore` or rebuild in the IDE) before continuing.

---

## Step 3: Find the ID Capture code

Search the project for the symbols that change. Old (v6): `SupportedDocuments`, `IdDocumentType`, `SupportedSides`. Current: `IdCaptureSettings`, `AcceptedDocuments`, `RejectedDocuments`, `Scanner`, `IdCaptureScanner`, `FullDocumentScanner`, `SingleSideScanner`, `MobileDocumentScanner`, `IdCapture.Create`, `IIdCaptureListener`, `OnIdCaptured`, `OnIdRejected`, `IdCaptureOverlay`, `CapturedId`, `VerificationResult`. Apply the relevant changes from the sections below directly to those files.

---

## Migration: 6 → 7

Version 7.0 introduced a completely redesigned ID Capture API. Work through each section that matches the project.

### 1. Document & zone selection: `SupportedDocuments` + `SupportedSides` → `AcceptedDocuments` + `Scanner`

In v6 you set a bitmask of `IdDocumentType` values (whose suffix encoded the zone — `_VIZ`, `_MRZ`, `_BARCODE`) and a `SupportedSides`. In v7 you declare **what** to accept as a list of document objects, and **how** to scan as a `Scanner`.

> On `.NET for Android` the settings property is **`Scanner`** (an `IdCaptureScanner`). The generic Scandit docs sometimes call it `scannerType` — that is the cross-platform name; the .NET binding is `Scanner`.

**Before (v6):**

```csharp
var settings = new IdCaptureSettings();
settings.SupportedDocuments =
    IdDocumentType.DlViz | IdDocumentType.IdCardViz | IdDocumentType.PassportMrz;
settings.SupportedSides = SupportedSides.FrontAndBack;
var idCapture = IdCapture.Create(dataCaptureContext, settings);
```

**After (v7+):**

```csharp
var settings = new IdCaptureSettings
{
    AcceptedDocuments =
    [
        new DriverLicense(IdCaptureRegion.Any),
        new IdCard(IdCaptureRegion.Any),
        new Passport(IdCaptureRegion.Any),
    ],
    // Sides are now expressed by the scanner. FullDocumentScanner = front + back.
    Scanner = new IdCaptureScanner(
        physicalDocument: new FullDocumentScanner(),
        mobileDocument: null),
};
var idCapture = IdCapture.Create(dataCaptureContext, settings);
```

**Sides mapping** (was `SupportedSides`):

| v6 | v7 |
|---|---|
| `FRONT_ONLY` | `new SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` |
| `FRONT_AND_BACK` | `new FullDocumentScanner()` |

**Zone mapping** (the v6 `IdDocumentType` suffix becomes a scanner zone toggle). `SingleSideScanner` takes three positional booleans `(bool barcode, bool machineReadableZone, bool visualInspectionZone)`:

| v6 suffix | v7 |
|---|---|
| `*_VIZ` | `new SingleSideScanner(false, false, true)` or `new FullDocumentScanner()` |
| `*_MRZ` | `new SingleSideScanner(false, true, false)` |
| `*_BARCODE` | `new SingleSideScanner(true, false, false)` |
| multiple zones | `new FullDocumentScanner()` (recommended), or a `SingleSideScanner` with several flags enabled |

> Tip: if some documents need full scanning and others only one zone, use `FullDocumentScanner` for all of them — it is simpler and reads every available zone.

**Document type mapping** (the v6 `IdDocumentType` value → the v7 document object you add to `AcceptedDocuments`). The right column is a document class taking an `IdCaptureRegion`:

| v6 `IdDocumentType` | v7 document |
|---|---|
| `DL_VIZ` | `new DriverLicense(IdCaptureRegion.Any)` |
| `AAMVA_BARCODE` | `new DriverLicense(...)` **and** `new IdCard(...)` |
| `VISA_MRZ` | `new VisaIcao(IdCaptureRegion.Any)` |
| `PASSPORT_MRZ` / `PASSPORT_VIZ` | `new Passport(IdCaptureRegion.Any)` |
| `ID_CARD_MRZ` / `ID_CARD_VIZ` | `new IdCard(...)` and/or `new ResidencePermit(...)` and/or certain `new RegionSpecific(...)` |
| `SWISS_DL_MRZ` | `new DriverLicense(IdCaptureRegion.Switzerland)` |
| `HEALTH_INSURANCE_CARD_VIZ` | `new HealthInsuranceCard(IdCaptureRegion.Any)` |
| `COLOMBIA_DL_BARCODE` | `new DriverLicense(IdCaptureRegion.Colombia)` |
| `COLOMBIA_ID_BARCODE` | `new IdCard(IdCaptureRegion.Colombia)` |
| `ARGENTINA_ID_BARCODE` | `new IdCard(IdCaptureRegion.Argentina)` |
| `SOUTH_AFRICA_DL_BARCODE` | `new DriverLicense(IdCaptureRegion.SouthAfrica)` |
| `SOUTH_AFRICA_ID_BARCODE` | `new IdCard(IdCaptureRegion.SouthAfrica)` |
| `US_US_ID_BARCODE` | `new RegionSpecific(RegionSpecificSubtype.UsUniformedServicesId)` |
| `COMMON_ACCESS_CARD_BARCODE` | `new RegionSpecific(RegionSpecificSubtype.UsCommonAccessCard)` |
| `CHINA_*_MRZ` permits | `new RegionSpecific(...)` with the matching China subtype |
| `APEC_BUSINESS_TRAVEL_CARD_MRZ` | `new RegionSpecific(RegionSpecificSubtype.ApecBusinessTravelCard)` |

> The .NET enum members are PascalCase (`IdDocumentType.DlViz`, `IdCaptureRegion.Colombia`, `RegionSpecificSubtype.UsCommonAccessCard`, …). Read the **actual** v6 symbols out of the project and map each one; do not invent values. If a v6 type isn't in this table, find its modern equivalent in the [Supported Documents](https://docs.scandit.com/sdks/net/android/id-capture/supported-documents/) list.

### 2. Accepting / rejecting documents

Delete any hand-written "is this document allowed?" logic that ran after capture. In v7, `AcceptedDocuments` automatically rejects anything not listed (delivered via `OnIdRejected` with `RejectionReason.NotAcceptedDocumentType`), and `RejectedDocuments` lets you exclude a subset even if it matches an accepted category.

### 3. Document images: `IdImageType`

If the project requested document images, remap the enum — there is no longer a front/back distinction:

| v6 | v7 |
|---|---|
| `IdImageType.Face` | `IdImageType.Face` |
| `IdImageType.IdFront` | `IdImageType.CroppedDocument` |
| `IdImageType.IdBack` | `IdImageType.CroppedDocument` |

With `SingleSideScanner` you get the front; with `FullDocumentScanner` you get front and back. For the full camera frame use `settings.SetShouldPassImageTypeToResult(IdImageType.Frame, true)`.

### 4. Callbacks

There are now exactly two: `OnIdCaptured(IdCapture, CapturedId)` and `OnIdRejected(IdCapture, CapturedId?, RejectionReason)`. If the old code handled a timeout callback (`onIdCapturedTimedOut`), that case now arrives in `OnIdRejected` with `RejectionReason.Timeout`. For `FullDocumentScanner`, `OnIdCaptured` fires only once **all** sides are captured — the overlay guides the user through flipping the document.

### 5. Result structure (`CapturedId`)

Update field reads that changed shape:

- `CapturedId.IssuingCountry` is now a region type rather than a raw `string` (use `IssuingCountryIso` for the ISO string).
- The `Viz.CapturedSides` type is now `CapturedSides` (renamed from `SupportedSides`).
- `CapturedId.DocumentType` → `CapturedId.Document` (`IIdCaptureDocument?`, read `Document?.DocumentType`).
- Zone-specific substructures (e.g. the old `aamvaBarcode`) are replaced by the unified `CapturedId.Barcode` / `CapturedId.Mrz` / `CapturedId.Viz`. Aggregate fields (name, dates, document number) are available directly on the top-level `CapturedId`.

### 6. Optional rejection flags (7.6+)

The declarative rejection flags (`RejectExpiredIds`, `RejectIdsExpiringIn`, `RejectNotRealIdCompliant`, `RejectForgedAamvaBarcodes`, `RejectInconsistentData`, `RejectHolderBelowAge`) landed on `dotnet.android` at **7.6**. If you are migrating to 7.0–7.5 they are not available yet; on 7.6+ prefer them over manual post-capture checks. See `references/advanced.md`.

---

## Migration: 7 → 8

### 1. Explicit SDK initialization is now required (the critical change)

The 8.0 .NET redesign removed the implicit bootstrap that 6.x/7.x performed automatically. The app must call `ScanditCaptureCore.Initialize()` and `ScanditIdCapture.Initialize()` before any Scandit type is constructed, or it **crashes on the first `DataCaptureContext.ForLicenseKey(...)` / `IdCapture.Create(...)` / `DataCaptureView.Create(...)` call**.

Check whether the project has an `Application` subclass (a class with `[Application]` deriving from `Android.App.Application`, usually `MainApplication.cs`).

**If `MainApplication.cs` exists** — add both calls at the top of `OnCreate()` (after `base.OnCreate()`):

```csharp
public override void OnCreate()
{
    base.OnCreate();
    ScanditCaptureCore.Initialize();
    ScanditIdCapture.Initialize();
    // ... existing init stays below
}
```

with the using directives:

```csharp
using Scandit.DataCapture.Core;
using Scandit.DataCapture.ID;
```

**If `MainApplication.cs` does not exist** — create it next to `MainActivity.cs`. Android refuses to load two `[Application]`-decorated classes, so do not add a second one.

```csharp
using Android.Runtime;
using Scandit.DataCapture.Core;
using Scandit.DataCapture.ID;

namespace MyApp;

[Application]
public class MainApplication(IntPtr handle, JniHandleOwnership ownership)
    : Application(handle, ownership)
{
    public override void OnCreate()
    {
        base.OnCreate();
        ScanditCaptureCore.Initialize();
        ScanditIdCapture.Initialize();
    }
}
```

> Note the initializer name: the NuGet package is `Scandit.DataCapture.IdCapture`, but the initializer and namespace are **`ScanditIdCapture.Initialize()`** / `using Scandit.DataCapture.ID;`. The generic .NET migration example shows `ScanditBarcodeCapture.Initialize()` — for an ID Capture app you want `ScanditIdCapture.Initialize()` instead (alongside `ScanditCaptureCore`).

### 2. `IdCapture.Create(...)` is unchanged on .NET — do NOT switch to a constructor

The 7→8 guide deprecates `forContext(...)` in favor of constructor initialization, **but that change applies only to the cross-platform frameworks (Capacitor, Cordova, React Native, Flutter).** The .NET binding has always used the static factory `IdCapture.Create(dataCaptureContext, settings)`, and it remains correct in 8.x. There is no `new IdCapture(...)` / `IdCapture.ForDataCaptureContext(...)` on .NET — leave existing `Create(...)` calls as they are.

### 3. Verification result model (settings-driven)

If the app does AAMVA forgery or front/back consistency verification, the result model arrives on `dotnet.android` at **8.0**: enable `settings.RejectForgedAamvaBarcodes` / `settings.RejectInconsistentData`, then read `capturedId.VerificationResult.AamvaBarcodeVerification` (`.Status`: `Authentic` / `LikelyForged` / `Forged`) and `capturedId.VerificationResult.DataConsistency` (`.AllChecksPassed`, `.FailedChecks`).

There is **no standalone `AamvaBarcodeVerifier` on .NET** — it was a Web/Xamarin-only class and was removed entirely in 8.0. If you are porting from a Xamarin.Android project that used `AamvaBarcodeVerifier.Create(...)` / `VerifyCapturedIdAsync(...)`, delete that verifier and switch to the settings flag above. On `.NET for Android`, prefer `AamvaBarcodeVerificationResult.Status` over the deprecated `AllChecksPassed`. See `references/advanced.md`.

### 4. Other 8.0 ID Capture changes (apply only if used)

- `DateResult.ToDate` was removed — use `DateResult.LocalDate` or `DateResult.UtcDate` (both `DateTime`).
- Mobile-document OCR (previously surfaced inside `VizResult` via `decodeMobileDriverLicenseViz`) is now a separate `capturedId.MobileDocumentOcr`.
- `CapturedId.CitizenPassport` (`IsCitizenPassport`) was added.
- Full-frame anonymization and `AnonymizeDefaultFields` (8.2) were added; `AddAnonymizedField(document, IdFieldType)` lets you anonymize specific fields.
- `VideoResolution.Auto` is deprecated SDK-wide — prefer `IdCapture.RecommendedCameraSettings` (which the integration already uses).

> Do not introduce `MobileDocumentScanner.ElementsToRetain`, NFC types (`NfcScanner` / `capturedId.Nfc`), or the deserializer API while migrating — they are not part of the `dotnet.android` surface.

---

## After applying changes

1. Restore NuGet packages (`dotnet restore`) and rebuild. Fix any remaining compile errors using the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api.html) — do not guess at signatures.
2. Point the user at the official guides for the complete (cross-product) change list:
   - 6 → 7: https://docs.scandit.com/sdks/net/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/net/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made — which files were edited, which APIs were replaced (e.g. `SupportedDocuments` → `AcceptedDocuments` + `Scanner`), and the required `MainApplication` initialization. Do not list APIs that were already correct or unchanged.
4. Verify: the project compiles with no references to `SupportedDocuments`, `IdDocumentType`, or `SupportedSides`; `AcceptedDocuments` and `Scanner` are both set explicitly; on 8.x both `Initialize()` calls run at startup; a test scan delivers a `CapturedId` in `OnIdCaptured` and an out-of-scope document triggers `OnIdRejected`.
