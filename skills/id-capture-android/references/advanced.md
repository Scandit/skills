# ID Capture Advanced — Android (Kotlin/Java)

This builds on `references/integration.md`. Covers: USDL verification, anonymization, voided detection, EU driving-license back decoding, BarcodeCapture co-existence, mobile documents (mDL), overlay customization, and custom feedback.

## US driver's license verification

Two independent flags — use either or both:

- `rejectForgedAamvaBarcodes` — detects forged AAMVA barcodes.
- `rejectInconsistentData` — cross-checks data between zones: VIZ vs MRZ when both present, or VIZ vs PDF417 barcode. For US DLs (no MRZ) this compares front VIZ against back PDF417.

```kotlin
val settings = IdCaptureSettings().apply {
    acceptedDocuments = listOf(DriverLicense(IdCaptureRegion.US))
    scanner = IdCaptureScanner(FullDocumentScanner())
    setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true) // required for frontReviewImage
    rejectForgedAamvaBarcodes = true
    rejectInconsistentData = true
    rejectExpiredIds = true
}
```

Handle verification rejections and read the front review image:

```kotlin
override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
    mode.isEnabled = false
    when (reason) {
        RejectionReason.INCONSISTENT_DATA -> {
            val reviewImage = id?.verificationResult?.dataConsistency?.frontReviewImage
            presentResult(reason, reviewImage)
        }
        RejectionReason.FORGED_AAMVA_BARCODE -> presentResult(reason, null)
        RejectionReason.DOCUMENT_EXPIRED     -> presentResult(reason, null)
        RejectionReason.TIMEOUT              -> showAlert("Capture timed out. Please try again.")
        else                                 -> showAlert("Document not supported.")
    }
}
```

**`VerificationResult` members:**
- `capturedId.verificationResult?.dataConsistency` — `DataConsistencyResult?`
  - `.allChecksPassed` — `Boolean`
  - `.frontReviewImage` — `Bitmap?` — **null unless `setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true)` was set**
- `capturedId.verificationResul?.aamvaBarcodeVerification` — `AamvaBarcodeVerificationResult?`
  - `.status` — `AamvaBarcodeVerificationStatus`: `AUTHENTIC` / `LIKELY_FORGED` / `FORGED`

Verification is settings-driven — do **not** use a standalone `AamvaBarcodeVerifier` or `DataConsistencyVerifier`.

## Anonymization

Two independent dimensions:

**Which fields** — the SDK's built-in default list (meets regional legal requirements, e.g. document number on German IDs) is active by default. Override with:

```kotlin
settings.anonymizeDefaultFields = false  // disable SDK defaults
settings.addAnonymizedField(IdCard(IdCaptureRegion.EU_AND_SCHENGEN), IdFieldType.DATE_OF_BIRTH)
```

**How** — controlled by `anonymizationMode` (an `IdAnonymizationMode`):
- `FIELDS_ONLY` — **default** — field values redacted in `CapturedId` (returned as `null`)
- `IMAGES_ONLY` — fields obscured in document images only
- `FIELDS_AND_IMAGES` — both
- `NONE` — no anonymization

```kotlin
settings.anonymizationMode = IdAnonymizationMode.FIELDS_AND_IMAGES
```

Check `capturedId.anonymizedFields` to see which fields were anonymized on a given result.

## Voided document detection

Set `rejectVoidedIds = true` to reject documents that have been physically voided (e.g. a hole-punched or "VOID"-stamped US Driver's License). The SDK then calls `onIdRejected` with `RejectionReason.DOCUMENT_VOIDED`. Primarily tuned for US Driver's Licenses; results on other document types may be less accurate.

```kotlin
settings.rejectVoidedIds = true
```

```kotlin
override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
    mode.isEnabled = false
    when (reason) {
        RejectionReason.DOCUMENT_VOIDED ->
            showAlert("This document is voided. Please scan a valid document.")
        else -> showAlert("Document not supported.")
    }
}
```

Voided detection is part of the `id` module — no separate dependency or verifier class is required.

## Decode the back of European Driving Licenses

By default ID Capture does not extract the vehicle-category table on the back of European Driving Licenses. Enable it with `decodeBackOfEuropeanDrivingLicense`:

```kotlin
settings.decodeBackOfEuropeanDrivingLicense = true
```

The categories then appear on the VIZ result under `drivingLicenseDetails.drivingLicenseCategories`. Each `DrivingLicenseCategory` exposes `.code` (the category code, e.g. "B", "C1"), plus `.dateOfIssue` and `.dateOfExpiry` (`DateResult?`):

```kotlin
override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
    mode.isEnabled = false
    id.viz?.drivingLicenseDetails?.drivingLicenseCategories?.forEach { category ->
        Log.d("IdCapture", "Category: ${category.code}")
        Log.d("IdCapture", "Issued: ${category.dateOfIssue}")
        Log.d("IdCapture", "Expires: ${category.dateOfExpiry}")
    }
}
```

The category code is `category.code` — there is no `categoryCode` property.

## Co-existence with Barcode Capture

`IdCapture` and `BarcodeCapture` can run **together on one `DataCaptureContext`** — one context, one `DataCaptureView`, one camera. A common case is an airport screen that reads a boarding-pass PDF417 barcode **and** a passport/ID on the same screen.

Each mode is attached to the context by its own `forDataCaptureContext` factory; both stay attached at once and the native layer runs them together. Give each mode its own listener, and toggle each independently with `mode.isEnabled`. Do **not** remove or replace one mode to add the other — that is not required for co-existence (it is only needed when you genuinely want to switch a surface from one mode to another).

```kotlin
// ID Capture mode (passport / ID)
val idCaptureSettings = IdCaptureSettings().apply {
    acceptedDocuments = listOf(Passport(IdCaptureRegion.ANY))
    scanner = IdCaptureScanner(FullDocumentScanner())
}
val idCapture = IdCapture.forDataCaptureContext(dataCaptureContext, idCaptureSettings)
idCapture.addListener(idListener)

// Barcode Capture mode (IATA boarding pass = PDF417), same context
val barcodeSettings = BarcodeCaptureSettings().apply {
    enableSymbology(Symbology.PDF417, true)
}
val barcodeCapture = BarcodeCapture.forDataCaptureContext(dataCaptureContext, barcodeSettings)
barcodeCapture.addListener(barcodeListener)

// Both can be enabled at once — they run together.
idCapture.isEnabled = true
barcodeCapture.isEnabled = true
```

In `onBarcodeScanned(...)` read `session.newlyRecognizedBarcode`; in `onIdCaptured(...)` read the `CapturedId`. Use `isEnabled` (not mode removal) when you want to pause one of them. Co-existence with BarcodeCapture requires adding the `com.scandit.datacapture:barcode` dependency alongside `id` and `core`.

## Overlay customization

```kotlin
overlay.idLayoutStyle = IdLayoutStyle.SQUARE       // ROUNDED (default) or SQUARE
overlay.idLayoutLineStyle = IdLayoutLineStyle.BOLD // BOLD or LIGHT
overlay.showTextHints = true
overlay.setFrontSideTextHint("Place the front of your ID here")
overlay.setBackSideTextHint("Now flip to the back")
```

Brush colors for the captured / localized / rejected states are set via `overlay.capturedBrush`, `overlay.localizedBrush`, and `overlay.rejectedBrush` (each a `Brush`).

## Custom feedback

```kotlin
import com.scandit.datacapture.id.capture.IdCaptureFeedback

val feedback = IdCaptureFeedback()
// Configure the idCaptured / idRejected Feedback objects (sound / vibration) as needed.
idCapture.feedback = feedback
```

Use when you want your own UX cues (animations, toasts) instead of the SDK defaults. To restore defaults use `IdCaptureFeedback.defaultFeedback()`.

## Mobile documents (mDL / ISO 18013-5)

Reads **mobile driver's licenses** (mDL) — both the offline ISO 18013-5 mdoc exchange and the OCR of the on-screen rendering. The API surface lives entirely in the base `id` module (no add-on dependency).

Mobile documents are read by a `MobileDocumentScanner`, passed to `IdCaptureScanner` via the `mobileDocument` argument. The physical-document scanner is independent — supply only `mobileDocument` for mDL-only, or both to read physical and mobile documents in the same session:

```kotlin
// Mobile documents only:
settings.scanner = IdCaptureScanner(
    mobileDocument = MobileDocumentScanner(iso180135 = true, ocr = false))

// Physical + mobile documents in the same session:
settings.scanner = IdCaptureScanner(
    physicalDocument = FullDocumentScanner(),
    mobileDocument = MobileDocumentScanner(iso180135 = true, ocr = false))
```

`MobileDocumentScanner(iso180135 = true, ocr = false)` enables the ISO 18013-5 mdoc path and disables OCR; `MobileDocumentScanner(iso180135 = false, ocr = true)` reads only the OCR of the on-screen document. An optional `elementsToRetain: Set<MobileDocumentDataElement>` overload declares which fields the app intends to retain, setting the `IntentToRetain` flag in the ISO 18013-5 request.

**Read the result** — mobile-document data arrives on `CapturedId`:

```kotlin
override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
    mode.isEnabled = false
    id.mobileDocument?.let { mobile ->   // MobileDocumentResult? (ISO 18013-5 mdoc)
        Log.d("IdCapture", "${mobile.fullName} ${mobile.dateOfBirth}")
    }
    // The harmonized top-level fields (id.fullName, id.dateOfBirth, …)
    // are still populated for mobile documents — reach into mobileDocument only
    // when you need mobile-specific data.
}
```

> Document type is read via `capturedId.document?.documentType` — there is no `IdDocumentType` bitmask, and no `AamvaBarcodeVerifier` is involved here.

## NFC chip reading

Native Android supports NFC chip reading after an initial MRZ scan — refer to the [official Android ID Capture documentation](https://docs.scandit.com/sdks/android/id-capture/get-started/).
