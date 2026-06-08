# ID Capture Advanced — iOS (Swift/UIKit)

This builds on `references/integration.md`. Covers: USDL verification, anonymization, BarcodeCapture co-existence, overlay customization, and custom feedback.

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

**How** — controlled by `anonymizationMode`:
- `.none` — no anonymization
- `.fieldsOnly` — field values redacted in `CapturedId` (returned as `nil`)
- `.imagesOnly` — fields obscured in document images only
- `.fieldsAndImages` — both

```swift
settings.anonymizationMode = .fieldsAndImages
```

Check `capturedId.anonymizedFields` to see which fields were anonymized on a given result.

## Co-existing with BarcodeCapture

In most apps that switch between modes, call `context.removeCurrentMode()` before adding the new mode — otherwise the SDK may surface a visible error on the `DataCaptureView`:

```swift
// When showing the ID scanning screen:
context.removeCurrentMode()
idCapture = IdCapture(context: context, settings: idCaptureSettings)

// When returning to the barcode scanning screen:
context.removeCurrentMode()
barcodeCapture = BarcodeCapture(context: context, settings: barcodeCaptureSettings)
```

**Exception:** apps that intentionally scan both simultaneously (e.g. scanning a boarding-pass barcode and an ID at the same time) keep both modes active. This is an advanced use case with restrictions — consult the documentation.

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
