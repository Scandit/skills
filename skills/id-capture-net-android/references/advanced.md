# ID Capture Advanced — .NET for Android

This builds on `references/integration.md` — the `DataCaptureContext`, `IdCapture` mode, camera, `DataCaptureView`, and overlay are set up the same way. This file covers: choosing a scanner, rejection rules, data-consistency / AAMVA verification, anonymization, reading the rich result model (MRZ / VIZ / barcode / mobile document / images), and overlay customization.

Everything here is configured on `IdCaptureSettings` (property sets) and read off `CapturedId`. There is **no builder** and **no verifier class** — see the relevant sections.

## Scanner selection

`IdCaptureSettings.Scanner` is an `IdCaptureScanner` wrapping a physical and/or mobile scanner:

```csharp
settings.Scanner = new IdCaptureScanner(
    physicalDocument: <IPhysicalDocumentScanner?>,
    mobileDocument: <MobileDocumentScanner?>);
```

### FullDocumentScanner (default choice)

Reads front and back of a physical document automatically — both the VIZ (printed text) and any MRZ / PDF417 barcode. Use it for most ID / driver's-license / passport flows.

```csharp
Scanner = new IdCaptureScanner(physicalDocument: new FullDocumentScanner(), mobileDocument: null)
```

### SingleSideScanner (read only the zone(s) you need)

`new SingleSideScanner(bool barcode, bool machineReadableZone, bool visualInspectionZone)` reads a single side, enabling only the zones you turn on. Faster when you know exactly what you need.

```csharp
// Only the PDF417 barcode on the back of a US driver's license:
Scanner = new IdCaptureScanner(
    physicalDocument: new SingleSideScanner(barcode: true, machineReadableZone: false, visualInspectionZone: false),
    mobileDocument: null)

// Only the MRZ of a passport:
Scanner = new IdCaptureScanner(
    physicalDocument: new SingleSideScanner(barcode: false, machineReadableZone: true, visualInspectionZone: false),
    mobileDocument: null)
```

Properties (get-only): `Barcode`, `MachineReadableZone`, `VisualInspectionZone`.

### MobileDocumentScanner (mobile driver's licenses / mDL)

`new MobileDocumentScanner(bool iso180135, bool ocr)`. Combine it with a physical scanner or use it alone.

```csharp
Scanner = new IdCaptureScanner(
    physicalDocument: new FullDocumentScanner(),
    mobileDocument: new MobileDocumentScanner(iso180135: true, ocr: true))
```

> The ISO flag's getter is bound as `GetIso180135` (a binding quirk) — you rarely read it back; you pass the flags into the constructor.

## Accepted vs. rejected documents

- `AcceptedDocuments` (`IList<IIdCaptureDocument>`) — only these document types/regions are captured.
- `RejectedDocuments` (`IList<IIdCaptureDocument>`) — explicitly reject these even if otherwise accepted.

```csharp
var settings = new IdCaptureSettings
{
    AcceptedDocuments = [ new DriverLicense(IdCaptureRegion.Us), new IdCard(IdCaptureRegion.Us) ],
    RejectedDocuments = [ new IdCard(IdCaptureRegion.Any) ], // example
    Scanner = new IdCaptureScanner(new FullDocumentScanner(), null),
};
```

Document constructors (all `IIdCaptureDocument`, exposing `Region` + `DocumentType`):
`new IdCard(region)`, `new DriverLicense(region)`, `new Passport(region)`, `new VisaIcao(region)`, `new ResidencePermit(region)`, `new HealthInsuranceCard(region)`, and `new RegionSpecific(RegionSpecificSubtype.X)` (also exposes `Subtype`). `region` is an `IdCaptureRegion` (PascalCase: `Any`, `Us`, `Uk`, `Uae`, `EuAndSchengen`, `Germany`, … ~250 values).

## Rejection rules

Set these flags on `IdCaptureSettings`; when a scan trips a rule, the SDK calls `OnIdRejected(mode, capturedId, reason)` with the matching `RejectionReason` instead of `OnIdCaptured`.

| Setting | Type | Rejection reason raised |
|---|---|---|
| `RejectExpiredIds` | `bool` | `RejectionReason.DocumentExpired` |
| `RejectIdsExpiringIn` | `Duration?` | `RejectionReason.DocumentExpiresSoon` |
| `RejectVoidedIds` | `bool` | `RejectionReason.DocumentVoided` (punched / cancelled) |
| `RejectHolderBelowAge` | `int?` | `RejectionReason.HolderUnderage` |
| `RejectNotRealIdCompliant` | `bool` | `RejectionReason.NotRealIdCompliant` |
| `RejectForgedAamvaBarcodes` | `bool` | `RejectionReason.ForgedAamvaBarcode` |
| `RejectInconsistentData` | `bool` | `RejectionReason.InconsistentData` |

```csharp
var settings = new IdCaptureSettings
{
    AcceptedDocuments = [ new DriverLicense(IdCaptureRegion.Any), new Passport(IdCaptureRegion.Any) ],
    Scanner = new IdCaptureScanner(new FullDocumentScanner(), null),
    RejectExpiredIds = true,
    RejectIdsExpiringIn = new Duration(days: 0, months: 3, years: 0), // reject if expiring within 3 months
    RejectHolderBelowAge = 18,
};
```

`Duration` is `new Duration(int days, int months, int years)`.

The full `RejectionReason` enum: `NotAcceptedDocumentType`, `InvalidFormat`, `DocumentVoided`, `Timeout`, `SingleImageNotRecognized`, `DocumentExpired`, `DocumentExpiresSoon`, `NotRealIdCompliant`, `HolderUnderage`, `ForgedAamvaBarcode`, `InconsistentData`, `BluetoothCommunicationError`, `BluetoothUnavailable`. Always surface a user-facing message in `OnIdRejected`.

## Verification (settings-driven — there is NO verifier class)

On .NET there is **no `AamvaBarcodeVerifier` and no `DataConsistencyVerifier`** (those exist on native/web only). Instead:

1. Enable the check via a settings flag (`RejectForgedAamvaBarcodes`, `RejectInconsistentData`, `RejectNotRealIdCompliant`).
2. Read the outcome from `capturedId.VerificationResult` on a successful capture, and/or handle the rejection reason if the check fails hard.

```csharp
var settings = new IdCaptureSettings
{
    AcceptedDocuments = [ new DriverLicense(IdCaptureRegion.Us) ],
    Scanner = new IdCaptureScanner(new FullDocumentScanner(), null),
    RejectForgedAamvaBarcodes = true,
    RejectInconsistentData = true,
};
```

Then, in `OnIdCaptured`:

```csharp
using Scandit.DataCapture.ID.Verification;
using Scandit.DataCapture.ID.Verification.AamvaBarcode;

public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
{
    VerificationResult verification = capturedId.VerificationResult;

    // AAMVA barcode authenticity (US driver's licenses):
    AamvaBarcodeVerificationResult? aamva = verification.AamvaBarcodeVerification;
    if (aamva is not null)
    {
        bool authentic = aamva.Status == AamvaBarcodeVerificationStatus.Authentic;
        // Status is Authentic / LikelyForged / Forged.
    }

    // Cross-zone data consistency (front VIZ vs back barcode/MRZ):
    DataConsistencyResult? consistency = verification.DataConsistency;
    if (consistency is not null)
    {
        bool ok = consistency.AllChecksPassed;
        DataConsistencyCheck failed = consistency.FailedChecks; // [Flags] enum
        // consistency.FrontReviewImage is an Android.Graphics.Bitmap? for manual review.
    }

    mode.Enabled = false;
    this.RunOnUiThread(() => { /* present result */ });
}
```

- `VerificationResult` — `DataConsistency` (`DataConsistencyResult?`), `AamvaBarcodeVerification` (`AamvaBarcodeVerificationResult?`).
- `DataConsistencyResult` — `AllChecksPassed` (`bool`), `FailedChecks` / `PassedChecks` / `SkippedChecks` (`DataConsistencyCheck` `[Flags]`: `IssuingCountryComparison`, `IssuingJurisdictionComparison`, `FullNameComparison`, `DocumentNumberComparison`, `DateOfBirthComparison`, `DateOfExpiryComparison`, `DateOfIssueComparison`), `FrontReviewImage` (`Android.Graphics.Bitmap?`).
- `AamvaBarcodeVerificationResult` — `AllChecksPassed` (deprecated; prefer `Status`), `Status` (`AamvaBarcodeVerificationStatus`: `Authentic` / `LikelyForged` / `Forged`).

> If you set `RejectForgedAamvaBarcodes = true`, a confirmed forgery raises `OnIdRejected` with `RejectionReason.ForgedAamvaBarcode`; the `VerificationResult` on captured IDs lets you inspect borderline (`LikelyForged`) cases.

## Anonymization (keep regulated data out of the result)

`IdCaptureSettings.AnonymizationMode` controls what the SDK redacts before handing you the result. Recommend the minimum the use case needs.

```csharp
using Scandit.DataCapture.ID.Data;

var settings = new IdCaptureSettings
{
    AcceptedDocuments = [ new Passport(IdCaptureRegion.Any) ],
    Scanner = new IdCaptureScanner(new FullDocumentScanner(), null),
    AnonymizationMode = IdAnonymizationMode.FieldsAndImages,
};
```

`IdAnonymizationMode`: `None`, `FieldsOnly`, `ImagesOnly`, `FieldsAndImages`.

Per-field anonymization for a specific document:

```csharp
var passport = new Passport(IdCaptureRegion.Any);
var settings = new IdCaptureSettings
{
    AcceptedDocuments = [ passport ],
    Scanner = new IdCaptureScanner(new FullDocumentScanner(), null),
};
settings.AddAnonymizedField(passport, IdFieldType.DocumentNumber);
```

Check on the result with `capturedId.IsAnonymized(IdFieldType.DocumentNumber)`; `capturedId.AnonymizedFields` lists them. Control which images are returned at all with `settings.SetShouldPassImageTypeToResult(IdImageType.Face, false)` (`IdImageType`: `Face`, `CroppedDocument`, `Frame`).

## Reading the rich result model

`CapturedId` surfaces common holder fields at the top level (see `references/integration.md`). For zone-specific or document-specific data, use the sub-results. **The properties are `Mrz`, `Viz`, `Barcode`, `MobileDocument`, `MobileDocumentOcr`** — not `MrzResult` / `VizResult` / `BarcodeResult`. Each is null when that zone wasn't read.

```csharp
// MRZ (passports, many ID cards):
MrzResult? mrz = capturedId.Mrz;
string? capturedMrz = mrz?.CapturedMrz;          // raw 2/3-line MRZ string
string? personalIdNumber = mrz?.PersonalIdNumber;
string documentCode = mrz?.DocumentCode ?? "";

// VIZ (printed front of cards/licenses) — issuing info, place of birth, etc.:
VizResult? viz = capturedId.Viz;
string? issuingAuthority = viz?.IssuingAuthority;
string? placeOfBirth = viz?.PlaceOfBirth;
// NOTE: name / DOB / nationality / documentNumber are NOT on VizResult in .NET —
// read them from the top-level capturedId instead.

// PDF417 barcode (back of US/CA driver's licenses) — AAMVA fields:
BarcodeResult? barcode = capturedId.Barcode;
int? aamvaVersion = barcode?.AamvaVersion;
string? eyeColor = barcode?.EyeColor;
bool? realId = barcode?.RealId;
IDictionary<string, string>? elements = barcode?.BarcodeDataElements;

// Mobile driver's license (mDL):
MobileDocumentResult? mdl = capturedId.MobileDocument;
```

Other useful pieces on `CapturedId`:
- `capturedId.Images` (`IdImages`) — `Face`, `Frame`, `GetCroppedDocument(IdSide.Front/Back)`, `GetFrame(IdSide.Front/Back)` (each an `Android.Graphics.Bitmap?`).
- `capturedId.Document?.DocumentType` (`IdCaptureDocumentType`) and `capturedId.IsRegionSpecific(RegionSpecificSubtype.X)` to inspect which document was scanned (there are no `IsPassport()` / `IsDriverLicense()` helpers on .NET).
- `capturedId.UsRealIdStatus` (`NotAvailable` / `NotRealIdCompliant` / `RealIdCompliant`).

`DrivingLicenseDetails` / `DrivingLicenseCategory` (vehicle categories, restrictions, endorsements), `ProfessionalDrivingPermit`, and `VehicleRestriction` are also available — the barcode/mobile-document results expose category lists. The full per-field catalogue (the `BarcodeResult` AAMVA surface is large) is in the API reference; fetch it rather than guessing field names.

## Overlay customization

```csharp
using Scandit.DataCapture.ID.UI.Overlay;

this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
this.overlay.IdLayoutStyle = IdLayoutStyle.Square;        // Rounded (default) / Square
this.overlay.IdLayoutLineStyle = IdLayoutLineStyle.Bold;  // Bold / Light
this.overlay.ShowTextHints = true;
this.overlay.TextHintPosition = TextHintPosition.AboveViewfinder; // / BelowViewfinder
this.overlay.SetFrontSideTextHint("Show the front of your document");
this.overlay.SetBackSideTextHint("Now flip to the back");

// Custom highlight brushes:
this.overlay.CapturedBrush = IdCaptureOverlay.DefaultCapturedBrush;
this.overlay.RejectedBrush = IdCaptureOverlay.DefaultRejectedBrush;
```

## Key rules

1. **Scanner is required** — `FullDocumentScanner()` for full front+back, `SingleSideScanner(barcode, mrz, viz)` for a single zone, `MobileDocumentScanner(iso180135, ocr)` for mDL.
2. **Rejection rules are settings flags** that raise `OnIdRejected` with a matching `RejectionReason` — handle them.
3. **Verification has no verifier class** — set `RejectForgedAamvaBarcodes` / `RejectInconsistentData` and read `capturedId.VerificationResult` (`AamvaBarcodeVerification` / `DataConsistency`).
4. **Anonymize** with `AnonymizationMode` / `AddAnonymizedField` when you don't need every field.
5. **Sub-results are `capturedId.Mrz` / `.Viz` / `.Barcode` / `.MobileDocument`**; read name/DOB/nationality/documentNumber from the **top-level** `CapturedId`, not from `Viz`.
6. **No NFC / no deserializer / no `VisaDetails` / `PassportType` / `MobileDocumentDataElement`** on .NET Android.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/android/id-capture/advanced/) — full verification, anonymization, and scanner reference.
- [ID Capture API (.NET Android)](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api.html) — exhaustive field lists for `MrzResult` / `VizResult` / `BarcodeResult`.
