# ID Capture Advanced — iOS (Swift/UIKit)

This builds on `references/integration.md`. Covers: USDL verification, anonymization, voided detection, EU driving-license back decoding, BarcodeCapture co-existence, overlay customization, and custom feedback.

## US driver's license verification

Two independent flags — use either or both:

- `rejectForgedAamvaBarcodes` — detects forged AAMVA barcodes.
- `rejectInconsistentData` — cross-checks data between zones: VIZ vs MRZ when both present, or VIZ vs PDF417 barcode. For US DLs (no MRZ) this compares front VIZ against back PDF417.

```swift
settings.acceptedDocuments = [DriverLicense(region: .us)]
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
settings.setIncludeImage(true, for: .croppedDocument)  // required for frontReviewImage
settings.rejectForgedAamvaBarcodes = true
settings.rejectInconsistentData = true
settings.rejectExpiredIds = true
```

Handle verification rejections and read the front review image:

```swift
func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
    idCapture.isEnabled = false
    switch reason {
    case .inconsistentData:
        let reviewImage = capturedId?.verificationResult.dataConsistency?.frontReviewImage
        presentResult(rejectionReason: reason, reviewImage: reviewImage)
    case .forgedAamvaBarcode:
        presentResult(rejectionReason: reason, reviewImage: nil)
    case .documentExpired:
        presentResult(rejectionReason: reason, reviewImage: nil)
    case .timeout:
        showAlert(message: "Capture timed out. Please try again.")
    default:
        showAlert(message: "Document not supported.")
    }
}
```

**`VerificationResult` members:**
- `capturedId.verificationResult.dataConsistency` — `DataConsistencyResult?`
  - `.allChecksPassed` — `Bool`
  - `.frontReviewImage` — `UIImage?` — **nil unless `setIncludeImage(true, for: .croppedDocument)` was set**
- `capturedId.verificationResult.aamvaBarcodeVerification` — `AamvaBarcodeVerificationResult?`
  - `.status` — `.authentic` / `.likelyForged` / `.forged`

## Anonymization

Two independent dimensions:

**Which fields** — the SDK's built-in default list (meets regional legal requirements, e.g. document number on German IDs) is active by default. Override with:

```swift
settings.anonymizeDefaultFields = false  // disable SDK defaults
settings.addAnonymizedField(.dateOfBirth, forDocument: IdCard(region: .euAndSchengen))
settings.removeAnonymizedField(.dateOfBirth, forDocument: IdCard(region: .euAndSchengen))
```

**How** — controlled by `anonymizationMode` (an `IdAnonymizationMode`):
- `.fieldsOnly` — **default** — field values redacted in `CapturedId` (returned as `nil`)
- `.imagesOnly` — fields obscured in document images only
- `.fieldsAndImages` — both
- `.none` — no anonymization

```swift
settings.anonymizationMode = .fieldsAndImages
```

Check `capturedId.anonymizedFields` to see which fields were anonymized on a given result.

## Voided document detection

Set `rejectVoidedIds = true` to reject documents that have been physically voided (e.g. a hole-punched or "VOID"-stamped US Driver's License). The SDK then calls `didReject` with `RejectionReason.documentVoided`. Primarily tuned for US Driver's Licenses; results on other document types may be less accurate.

```swift
settings.rejectVoidedIds = true
```

```swift
func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
    idCapture.isEnabled = false
    switch reason {
    case .documentVoided:
        showAlert(message: "This document is voided. Please scan a valid document.")
    default:
        showAlert(message: "Document not supported.")
    }
}
```

This feature requires the `ScanditIdVoidedDetection` module in your project. See the [module overview](https://docs.scandit.com/sdks/ios/id-capture/get-started/#module-overview) for details.

## Decode the back of European Driving Licenses

By default ID Capture does not extract the vehicle-category table on the back of European Driving Licenses. Enable it with `decodeBackOfEuropeanDrivingLicense`:

```swift
settings.decodeBackOfEuropeanDrivingLicense = true
```

The categories then appear on the VIZ result under `drivingLicenseDetails.drivingLicenseCategories`. Each `DrivingLicenseCategory` exposes `.code` (the category code, e.g. "B", "C1"), plus `.dateOfIssue` and `.dateOfExpiry` (`DateResult?`):

```swift
func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
    idCapture.isEnabled = false
    if let categories = capturedId.vizResult?.drivingLicenseDetails?.drivingLicenseCategories {
        for category in categories {
            print("Category: \(category.code)")
            print("Issued: \(String(describing: category.dateOfIssue))")
            print("Expires: \(String(describing: category.dateOfExpiry))")
        }
    }
}
```

The category code is `category.code` — there is no `categoryCode` property. This feature requires the `ScanditIdEuropeDrivingLicense` module in your project. See the [module overview](https://docs.scandit.com/sdks/ios/id-capture/get-started/#module-overview) for details.

## Co-existence with Barcode Capture

`IdCapture` and `BarcodeCapture` can run **together on one `DataCaptureContext`** — one context, one `DataCaptureView`, one camera. A common case is an airport screen that reads a boarding-pass PDF417 barcode **and** a passport/ID on the same screen.

On iOS each mode is attached to the context by passing the context to its constructor (`IdCapture(context:settings:)` / `BarcodeCapture(context:settings:)` — the iOS equivalent of `context.addMode`). Both modes stay attached at once; the native layer runs them together. Give each mode its own listener, and toggle each independently with `mode.isEnabled`. Do **not** remove or replace one mode to add the other — that is not required for co-existence.

```swift
// ID Capture mode (passport / ID)
let idCaptureSettings = IdCaptureSettings()
idCaptureSettings.acceptedDocuments = [Passport(region: .any)]
idCaptureSettings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
idCapture = IdCapture(context: context, settings: idCaptureSettings) // attaches to context
idCapture.addListener(self)

// Barcode Capture mode (IATA boarding pass = PDF417), same context
let barcodeSettings = BarcodeCaptureSettings()
barcodeSettings.set(symbology: .pdf417, enabled: true)
barcodeCapture = BarcodeCapture(context: context, settings: barcodeSettings) // attaches to same context
barcodeCapture.addListener(self)

// Both can be enabled at once — they run together.
idCapture.isEnabled = true
barcodeCapture.isEnabled = true
```

In `barcodeCapture(_:didScanIn:frameData:)` read `session.newlyRecognizedBarcode`; in `idCapture(_:didCapture:capturedId:)` read the `CapturedId`. Use `isEnabled` (not mode removal) when you want to pause one of them.

## Overlay customization

```swift
overlay.idLayoutStyle = .square         // .rounded (default) or .square
overlay.idLayoutLineStyle = .bold       // .bold or .light
overlay.showTextHints = true
overlay.setFrontSideTextHint("Place the front of your ID here")
overlay.setBackSideTextHint("Now flip to the back")
overlay.capturedBrush = Brush(fill: .clear, stroke: .green, strokeWidth: 2)
overlay.rejectedBrush = Brush(fill: .clear, stroke: .red, strokeWidth: 2)
```

## Custom feedback

```swift
let feedback = IdCaptureFeedback()
feedback.idCaptured = Feedback(vibration: nil, sound: nil)
feedback.idRejected = Feedback(vibration: nil, sound: nil)
idCapture.feedback = feedback
```

Use when you want your own UX cues (animations, toasts) instead of the SDK defaults.

## NFC chip reading

iOS supports NFC chip reading via `NfcScanner` after an initial MRZ scan — refer to the [official iOS ID Capture documentation](https://docs.scandit.com/sdks/ios/id-capture/get-started/).

## Mobile documents (mDL / ISO 18013-5)

Reads **mobile driver's licenses** (mDL) — both the offline ISO 18013-5 mdoc exchange and the OCR of the on-screen rendering. This is GA, but thin in the guide docs; the API surface lives entirely in the base `ScanditIdCapture` framework (no add-on pod).

Mobile documents are read by a `MobileDocumentScanner`, passed to `IdCaptureScanner` via the `mobileDocument:` argument. The physical-document scanner is independent — supply only `mobileDocument:` for mDL-only, or both to read physical and mobile documents in the same session:

```swift
// Mobile documents only:
settings.scanner = IdCaptureScanner(
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false))

// Physical + mobile documents in the same session:
settings.scanner = IdCaptureScanner(
    physicalDocument: FullDocumentScanner(),
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false))
```

`MobileDocumentScanner(enablingIso180135: true, ocr: false)` enables the ISO 18013-5 mdoc path and disables OCR; `MobileDocumentScanner(enablingIso180135: false, ocr: true)` reads only the OCR of the on-screen document. An optional `elementsToRetain:` set of `MobileDocumentDataElement` declares which fields the app intends to retain, setting the `IntentToRetain` flag in the ISO 18013-5 request.

**Read the result** — mobile-document data arrives on `CapturedId` in source-specific getters:

```swift
func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
    if let mobile = capturedId.mobileDocumentResult {  // MobileDocumentResult? (ISO 18013-5 mdoc)
        print(mobile.fullName as Any, mobile.dateOfBirth as Any)
    }
    // The harmonized top-level fields (capturedId.fullName, capturedId.dateOfBirth, …)
    // are still populated for mobile documents — reach into mobileDocumentResult only
    // when you need mobile-specific data.
}
```

> Document type is read via `capturedId.document?.documentType` — there is no `IdDocumentType` bitmask, and no `AamvaBarcodeVerifier` is involved here.
