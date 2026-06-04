# ID Capture Advanced — iOS (Swift/UIKit)

This builds on `references/integration.md` — the `DataCaptureContext`, `IdCapture` mode, camera, `DataCaptureView`, and overlay are set up the same way. This file covers: choosing a scanner, rejection rules, US driver's license verification, anonymization, image capture, reading the rich result model, overlay customization, custom feedback, and co-existing with BarcodeCapture.

## Scanner selection

`IdCaptureSettings.scanner` takes an `IdCaptureScanner` wrapping a physical and/or mobile scanner:

```swift
settings.scanner = IdCaptureScanner(physicalDocument: <(any PhysicalDocumentScanner)?>)
// or
settings.scanner = IdCaptureScanner(physicalDocument: ..., mobileDocument: <MobileDocumentScanner?>)
```

### FullDocumentScanner (default choice)

Reads both sides of a physical document automatically — VIZ (printed text), MRZ, and PDF417 barcode. Multiple zones can be captured in a single scan; the results are aggregated and exposed through `CapturedId` via `mrzResult` (`MrzResult?`), `vizResult` (`VizResult?`), and `barcode` (`BarcodeResult?`). Use it for most ID / driver's license / passport flows where you need complete data from both sides.

```swift
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
```

### SingleSideScanner (read only the zone(s) you need)

`SingleSideScanner(enablingBarcode:machineReadableZone:visualInspectionZone:)` reads a single side, enabling only the zones you turn on. Use when you only need a specific zone — e.g. the back PDF417 barcode of a US license, or just the MRZ of a passport.

```swift
// Only the PDF417 barcode on the back of a US driver's license:
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(
        enablingBarcode: true,
        machineReadableZone: false,
        visualInspectionZone: false
    )
)

// Only the MRZ of a passport:
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(
        enablingBarcode: false,
        machineReadableZone: true,
        visualInspectionZone: false
    )
)

// All zones, single side:
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(
        enablingBarcode: true,
        machineReadableZone: true,
        visualInspectionZone: true
    )
)
```

**Passport-specific: combined VIZ + MRZ capture**

When `acceptedDocuments` includes `Passport` and `SingleSideScanner` has both `machineReadableZone` and `visualInspectionZone` enabled, the SDK performs a combined VIZ + MRZ capture pass for passports specifically — reading the printed data zone and the machine-readable zone together in a single scan. This does **not** apply to other documents that have an MRZ (such as ID cards or residence permits); for those, only the enabled zones are read independently.

```swift
// Capture both VIZ and MRZ together from a passport:
settings.acceptedDocuments = [Passport(region: .any)]
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(
        enablingBarcode: false,
        machineReadableZone: true,
        visualInspectionZone: true
    )
)
// Result: capturedId.mrzResult and capturedId.vizResult are both populated
```

### MobileDocumentScanner (IDs displayed on a screen)

`MobileDocumentScanner(enablingIso180135:ocr:)` is for mobile-presented identity documents. Use it specifically when the document holder is presenting an ID on their phone's screen — not for physical documents.

The two modes are distinct and can be enabled independently or together:

- **`enablingIso180135`** — ISO 18013-5 protocol. Scans a QR code displayed on the holder's phone, then performs a Bluetooth handover to securely pull the document holder's data from the mobile document app on their device.
- **`ocr`** — Uses OCR to read data directly from the screen of the holder's phone when a mobile document (e.g. a digital driver's license) is displayed.

```swift
// ISO 18013-5 only (QR + Bluetooth handover):
settings.scanner = IdCaptureScanner(
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false)
)

// OCR only (read from screen):
settings.scanner = IdCaptureScanner(
    mobileDocument: MobileDocumentScanner(enablingIso180135: false, ocr: true)
)

// Both modes combined with physical document scanning:
settings.scanner = IdCaptureScanner(
    physicalDocument: FullDocumentScanner(),
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: true)
)
```

## Accepted vs. rejected documents

- `acceptedDocuments` — only these document types/regions are captured.
- `rejectedDocuments` — explicitly reject these even if they would otherwise be accepted.

```swift
// Accept all EU/Schengen ID cards, but explicitly reject French ones:
settings.acceptedDocuments = [IdCard(region: .euAndSchengen)]
settings.rejectedDocuments = [IdCard(region: .france)]
```

> **Rejected always wins.** If a document matches anything in `rejectedDocuments`, it is rejected regardless of what is in `acceptedDocuments`. Do not put a broader region in `rejectedDocuments` and a narrower one in `acceptedDocuments` expecting the narrower accepted entry to win — it won't.

Document constructors (all conforming to `IdCaptureDocument`, exposing `region` + `documentType`):
`IdCard(region:)`, `DriverLicense(region:)`, `Passport(region:)`, `VisaIcao(region:)`, `ResidencePermit(region:)`, `HealthInsuranceCard(region:)`, and `RegionSpecific(subtype: RegionSpecificSubtype)`.

`IdCaptureRegion` values: `.any`, `.euAndSchengen`, `.us`, `.uk`, `.uae`, `.germany`, … (~250 values).

> **US Visa foil number:** When `VisaIcao(region: .us)` is in `acceptedDocuments` and MRZ is enabled on the scanner, the SDK will also capture the foil number printed outside the MRZ on US visas. The foil number is returned in `capturedId.vizResult`.

## Rejection rules

Set these flags on `IdCaptureSettings`. When a scan trips a rule, the SDK calls `idCapture(_:didReject:reason:)` with the matching `RejectionReason` instead of `idCapture(_:didCapture:)`.

| Setting | Type | Rejection reason raised |
|---|---|---|
| `rejectExpiredIds` | `Bool` | `.documentExpired` |
| `rejectIdsExpiringIn` | `Duration?` | `.documentExpiresSoon` |
| `rejectVoidedIds` | `Bool` | `.documentVoided` |
| `rejectHolderBelowAge` | `Int?` | `.holderUnderage` |
| `rejectNotRealIdCompliant` | `Bool` | `.notRealIdCompliant` |
| `rejectForgedAamvaBarcodes` | `Bool` | `.forgedAamvaBarcode` |
| `rejectInconsistentData` | `Bool` | `.inconsistentData` |

```swift
settings.rejectExpiredIds = true
settings.rejectHolderBelowAge = 21
settings.rejectIdsExpiringIn = Duration(days: 0, months: 3, years: 0)
```

Always surface a user-facing message in `didReject`. Handle each reason distinctly when it matters to your UX:

```swift
func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
    idCapture.isEnabled = false
    DispatchQueue.main.async {
        let message: String
        switch reason {
        case .documentExpired:
            message = "This ID has expired. Please use a valid document."
        case .holderUnderage:
            message = "The document holder does not meet the age requirement."
        case .timeout:
            message = "Capture timed out. Ensure the document is well lit and try again."
        default:
            message = "Document not supported. Please try a different document."
        }
        // Show alert and re-enable on dismiss
    }
}
```

The full `RejectionReason` enum: `.notAcceptedDocumentType`, `.invalidFormat`, `.documentVoided`, `.timeout`, `.documentExpired`, `.documentExpiresSoon`, `.notRealIdCompliant`, `.holderUnderage`, `.forgedAamvaBarcode`, `.inconsistentData`.

## US driver's license verification

For US driver's license verification, two independent flags are available — use either or both depending on what you need to check:

- `rejectForgedAamvaBarcodes` — detects forged AAMVA barcodes on the back of the license.
- `rejectInconsistentData` — cross-checks data between zones captured from the same document. What is compared depends on which zones are enabled: VIZ is compared against MRZ when both are present, or against the PDF417 barcode when barcode is captured instead. For US driver's licenses (which have no MRZ), this compares the VIZ on the front against the PDF417 barcode on the back.

Enable whichever flags apply and read `capturedId.verificationResult` on both the captured and rejected paths:

```swift
settings.acceptedDocuments = [DriverLicense(region: .us)]
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
settings.setIncludeImage(true, for: .face)
settings.setIncludeImage(true, for: .croppedDocument)
settings.rejectForgedAamvaBarcodes = true
settings.rejectInconsistentData = true
settings.rejectExpiredIds = true
```

On rejection for verification failures, extract the front review image if available:

```swift
func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
    idCapture.isEnabled = false
    switch reason {
    case .inconsistentData, .forgedAamvaBarcode, .documentExpired:
        let frontReviewImage = reason == .inconsistentData
            ? capturedId?.verificationResult.dataConsistency?.frontReviewImage
            : nil
        presentVerificationResult(capturedId, rejectionReason: reason, reviewImage: frontReviewImage)
    case .timeout:
        showAlert(message: "Capture timed out. Please try again.")
    default:
        showAlert(message: "Document not supported.")
    }
}
```

On success, the captured ID has passed all enabled verification checks:

```swift
func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
    let frontReviewImage = capturedId.verificationResult.dataConsistency?.frontReviewImage
    presentVerificationResult(capturedId, rejectionReason: nil, reviewImage: frontReviewImage)
}
```

**Key `VerificationResult` members:**
- `capturedId.verificationResult.dataConsistency` — `DataConsistencyResult?`
  - `.allChecksPassed` — `Bool`
  - `.frontReviewImage` — `UIImage?` (annotated image highlighting inconsistencies)
- `capturedId.verificationResult.aamvaBarcodeVerification` — `AamvaBarcodeVerificationResult?`
  - `.status` — `AamvaBarcodeVerificationStatus` (`.authentic` / `.likelyForged` / `.forged`)

> There is **no `AamvaBarcodeVerifier` or `DataConsistencyVerifier` class** on native iOS. Verification is entirely settings-driven.

## Anonymization

Anonymization is controlled by two independent dimensions:

**Which fields are anonymized** — determined by the combination of:
- The SDK's built-in default anonymization list (applied per document type, e.g. to meet regional legal requirements). Active by default; disable with `settings.anonymizeDefaultFields = false`.
- Any fields explicitly added with `settings.addAnonymizedField(_:forDocument:)` or removed with `settings.removeAnonymizedField(_:forDocument:)`.

**How fields are anonymized** — controlled by `anonymizationMode`:
- `.none` — no anonymization applied
- `.fieldsOnly` — anonymized field values are redacted in `CapturedId` (returned as `nil`)
- `.imagesOnly` — anonymized fields are obscured in document images only; field values are still returned
- `.fieldsAndImages` — field values are redacted AND the field is obscured in document images

```swift
// Redact field values and images for anonymized fields:
settings.anonymizationMode = .fieldsAndImages

// Add a field to anonymize for a specific document type:
settings.addAnonymizedField(.dateOfBirth, forDocument: IdCard(region: .euAndSchengen))

// Disable the SDK's default anonymization list entirely:
settings.anonymizeDefaultFields = false
```

Anonymized fields return `nil` in `CapturedId`. Check `capturedId.anonymizedFields` for the list of fields that were anonymized on a given result.

## Image capture

Opt in to document images before creating the `IdCapture` mode:

```swift
settings.setIncludeImage(true, for: .face)            // portrait photo
settings.setIncludeImage(true, for: .croppedDocument) // cropped document (by side)
settings.setIncludeImage(true, for: .frame)            // full camera frame
```

Retrieve images from `capturedId.images`:

```swift
let faceImage: UIImage? = capturedId.images.face
let croppedFront: UIImage? = capturedId.images.croppedDocument(side: .front)
let croppedBack: UIImage? = capturedId.images.croppedDocument(side: .back)
let frameImage: UIImage? = capturedId.images.frame
```

> Image capture increases processing time. Only opt in to the images you actually need.

## Reading the rich result model

Beyond the top-level `CapturedId` fields, zone-specific sub-results contain additional data:

**MRZ result** (`capturedId.mrzResult: MrzResult?`):
- Raw MRZ string lines, check digits, document code
- Available when the document was scanned via MRZ (machine-readable zone)

**VIZ result** (`capturedId.vizResult: VizResult?`):
- `capturedSides` (`CapturedSides`: `.frontOnly` / `.frontAndBack`)
- Additional fields from the visual inspection zone

**Barcode result** (`capturedId.barcode: BarcodeResult?`):
- AAMVA barcode data (US/Canadian DLs)
- Raw barcode string

**Mobile document result** (`capturedId.mobileDocumentResult: MobileDocumentResult?`):
- Data from an ISO 18013-5 mobile driver's license

**Driving license details** are nested under the barcode result for AAMVA documents and expose fields such as vehicle class, restrictions, endorsements, and weight limits.

## Co-existing with BarcodeCapture

`IdCapture` and `BarcodeCapture` can coexist on the same `DataCaptureContext`, but with limitations on concurrent scanning. In most apps that switch between the two modes, **call `context.removeCurrentMode()` before adding the new mode**:

```swift
// When switching to IdCapture from BarcodeCapture:
context.removeCurrentMode()
let idCapture = IdCapture(context: context, settings: idCaptureSettings)

// When switching back to BarcodeCapture:
context.removeCurrentMode()
let barcodeCapture = BarcodeCapture(context: context, settings: barcodeCaptureSettings)
```

**Exception — simultaneous scanning:** In apps where both modes should run at the same time (e.g. scanning a boarding-pass barcode and an ID simultaneously), keep both modes active without removing them. This is an advanced use case with restrictions — consult the documentation.

> `context.removeAllModes()` removes every active mode at once; `context.removeCurrentMode()` removes only the one mode currently attached. Use whichever is appropriate for your architecture.

> If `BarcodeCapture` and `IdCapture` are both active and incompatible settings are detected, the SDK will surface a visible error on the `DataCaptureView`. Call `context.removeCurrentMode()` before re-adding `IdCapture` to resolve it.

## Overlay customization

```swift
overlay.idLayoutStyle = .square      // .rounded (default) or .square
overlay.idLayoutLineStyle = .bold    // .bold or .light
overlay.showTextHints = true
overlay.setFrontSideTextHint("Place the front of your ID here")
overlay.setBackSideTextHint("Now flip to the back")

// Custom brush colors:
overlay.capturedBrush = Brush(fill: .clear, stroke: .green, strokeWidth: 2)
overlay.rejectedBrush = Brush(fill: .clear, stroke: .red, strokeWidth: 2)
```

## Custom feedback

Override the default sound/vibration with an `IdCaptureFeedback`:

```swift
let feedback = IdCaptureFeedback()
feedback.idCaptured = Feedback(vibration: nil, sound: nil)  // silence on capture
feedback.idRejected = Feedback(vibration: nil, sound: nil)  // silence on rejection
idCapture.feedback = feedback
```

Use this when you want to provide your own UX cues (animations, toasts) instead of the SDK defaults.

## NFC chip reading

iOS supports NFC chip reading via `NfcScanner` after an initial MRZ scan. This is out of scope for this skill — refer the user to the [official iOS ID Capture documentation](https://docs.scandit.com/sdks/ios/id-capture/get-started/) for guidance on NFC integration.

## Key rules

1. **Choose the scanner based on what data you need.** Use `FullDocumentScanner` when you need data from both sides of a document. Use `SingleSideScanner` when you only need a specific zone (e.g. MRZ only, or back barcode only). Don't default to `FullDocumentScanner` if single-zone scanning meets the requirement.
2. **Verification is settings-driven** — no verifier class; set flags on `IdCaptureSettings` and read `capturedId.verificationResult`.
4. **Always handle every `RejectionReason` you enable** — a rule you add without a corresponding UI message will confuse users.
5. **Request only the images you need** — face, croppedDocument, and frame each add processing overhead.
6. **Call `context.removeCurrentMode()` when switching between IdCapture and BarcodeCapture** — unless simultaneous scanning is intentional.

## Where to go next

- [Advanced Configurations (iOS)](https://docs.scandit.com/sdks/ios/id-capture/advanced/)
