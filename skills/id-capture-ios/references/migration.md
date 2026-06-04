# ID Capture iOS — Migration Guide

This guide covers the breaking changes in the Scandit iOS SDK across major versions. Read the section that matches your current version.

---

## Step 1 — Identify your current SDK version

Check the version pinned in your `Package.resolved` or SPM dependency graph for `datacapture-spm`. Then follow the matching section below:
- On **6.x** → follow [v6 → v7](#v6--v7-breaking-changes) then [v7 → v8](#v7--v8-breaking-changes)
- On **7.x** → follow [v7 → v8](#v7--v8-breaking-changes) only

---

## v6 → v7: Breaking Changes

This is a large, compile-breaking migration. The v6 API used a bitmask enum for document selection, a session/frame-data listener model, and per-frame/zone callbacks. All of these changed in v7.

### 1. Listener callbacks completely redesigned

The entire callback contract changed from frame-based to document-based.

**v6 — five session-based callbacks, fire per frame/zone:**

```swift
// v6 — IdCaptureListener (OLD)
extension ViewController: IdCaptureListener {

    // REQUIRED — fires once per recognized zone/frame; SDK gives you a partial CapturedId via the session
    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }
        // capturedId here is a partial result — may not have both sides yet
        idCapture.isEnabled = false
        showResult(capturedId)
    }

    // OPTIONAL — fires when a document zone is seen but not yet fully captured
    func idCapture(_ idCapture: IdCapture, didLocalizeIn session: IdCaptureSession, frameData: FrameData) { }

    // OPTIONAL — fires when a recognized zone is rejected
    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) { }

    // OPTIONAL — fires on timeout
    func idCapture(_ idCapture: IdCapture, didTimeoutIn session: IdCaptureSession, frameData: FrameData) { }
}
```

**v7+ — two direct-result callbacks, fire once per complete document:**

```swift
// v7+ — IdCaptureListener (NEW)
extension ViewController: IdCaptureListener {

    // REQUIRED — fires exactly once when the full document is recognised
    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        showResult(capturedId)
    }

    // REQUIRED — fires when a document is seen but rejected (wrong type, expired, etc.)
    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        showRejectionMessage(reason)
    }
}
```

**What to change:**
- Rename `didCaptureIn session:frameData:` → `didCapture(_:capturedId:)`. Read the `CapturedId` directly from the parameter, not from `session.newlyCapturedId`.
- Rename `didRejectIn session:frameData:` → `didReject(_:capturedId:reason:)`. The `RejectionReason` is now explicit.
- Delete `didLocalizeIn`, `didTimeoutIn`, `didFailWithError` — these methods no longer exist. Handle `.timeout` inside `didReject`.
- Delete all `IdCaptureSession` references — the class was removed entirely.
- Delete all `FrameData` references in ID capture callbacks — frame data is no longer passed.

> **Gotcha:** In v6, `didCapture` fired once per recognized scan zone (MRZ, VIZ, barcode) — potentially multiple times for a two-sided document. In v7+, it fires exactly once per complete document. Apps that relied on partial per-zone results must be rewritten to handle a single complete `CapturedId`.

### 2. Document selection model replaced

The v6 bitmask was replaced by an array of document objects with explicit regions.

**v6 — bitmask enum (OLD):**

```swift
// v6
settings.supportedDocuments = [.idCardVIZ, .dlVIZ, .passportMRZ]
settings.supportedSides = .frontAndBack
```

**v7+ — object array (NEW):**

```swift
// v7+
settings.acceptedDocuments = [
    IdCard(region: .any),
    DriverLicense(region: .any),
    Passport(region: .any),
]
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
```

**What to change:**
- Replace `supportedDocuments` with `acceptedDocuments`, converting old `IdDocumentType` enum values to the corresponding `IdCaptureDocument` type + region pair:

| v6 `supportedDocuments` value | v7+ `acceptedDocuments` entry |
|---|---|
| `.idCardVIZ`, `.idCardMRZ` | `IdCard(region: .any)` |
| `.dlVIZ`, `.dlMRZ`, `.dlBarcode` | `DriverLicense(region: .any)` |
| `.passportMRZ` | `Passport(region: .any)` |
| `.visaIcaoMRZ` | `VisaIcao(region: .any)` |
| `.residencePermitMRZ` | `ResidencePermit(region: .any)` |
| `.healthInsuranceCard` | `HealthInsuranceCard(region: .any)` |
| (US-specific barcode variants) | `DriverLicense(region: .us)` |

- Replace `supportedSides` with a `scanner` (see next section).

### 3. Scanner selection replaced

**v6 — `supportedSides` enum (OLD):**

```swift
// v6
settings.supportedSides = .frontOnly    // single-side
settings.supportedSides = .frontAndBack // both sides
```

**v7 — `scannerType` direct assignment (intermediate, v7.x only):**

```swift
// v7.x only — scannerType property, direct scanner subclass assignment
settings.scannerType = FullDocumentScanner()
settings.scannerType = SingleSideScanner(enablingBarcode: true, machineReadableZone: false, visualInspectionZone: false)
```

**v8+ — `scanner` with wrapper (current):**

```swift
// v8+ (current)
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(enablingBarcode: true, machineReadableZone: false, visualInspectionZone: false)
)
```

> If you're coming from v6, write the v8+ form directly (skip the v7 intermediate).

### 4. Image types renamed

**v6:**
```swift
settings.resultShouldContainImage(true, forIdCaptureType: .idFront)
settings.resultShouldContainImage(true, forIdCaptureType: .idBack)
let frontImage = capturedId.imageForType(.idFront)
```

**v7+:**
```swift
settings.setIncludeImage(true, for: .croppedDocument)  // replaces idFront/idBack
settings.setIncludeImage(true, for: .face)
settings.setIncludeImage(true, for: .frame)
let croppedFront = capturedId.images.croppedDocument(side: .front)
let croppedBack  = capturedId.images.croppedDocument(side: .back)
let face         = capturedId.images.face
```

### 5. Frame image retrieval changed

In v6, the raw camera frame was available via the `FrameData` parameter passed to the callback. In v7+, frame images are accessed via `capturedId.images.frame` after opting in:

```swift
// v7+
settings.setIncludeImage(true, for: .frame)
// ...then in the callback:
let frameImage: UIImage? = capturedId.images.frame
```

### 6. Rejection model

In v6, rejection was detected by inspecting `session.newlyRejectedId` in the callback. In v7+, `didReject(_:capturedId:reason:)` delivers the reason directly. Replace session inspection with the `RejectionReason` switch pattern shown above.

Rejection flags (`rejectExpiredIds`, `rejectHolderBelowAge`, etc.) are new in v7.6 — they did not exist in v6. You can now set rules directly on settings instead of implementing the logic yourself.

### 7. Result model restructured

Several sub-results moved to top-level `CapturedId` properties in v7:

| v6 access pattern | v7+ access pattern |
|---|---|
| `capturedId.aamvaBarcodeResult` | `capturedId.barcode` |
| Nested document-type result structures | `capturedId.mrzResult`, `capturedId.vizResult`, `capturedId.barcode` as top-level optionals |
| `capturedId.issuingCountry` as `String` | `capturedId.issuingCountry` as `IdCaptureRegion` enum |

### After applying v6 → v7 changes

Run a build. Expect compile errors anywhere `IdCaptureSession`, `FrameData`, `supportedDocuments`, `supportedSides`, `IdDocumentType`, `didCaptureIn`, `didRejectIn`, `didLocalizeIn`, `didTimeoutIn`, or `imageForType` appear. Fix each in turn using the patterns above.

---

## v7 → v8: Breaking Changes

This is a smaller migration but important to get right.

### 1. SDK initialization now explicit (required)

In v8, you must explicitly initialize the SDK before accessing `DataCaptureContext.shared`. This was optional (automatic) in v7.

**v7 — implicit (OLD):**
```swift
// v7: DataCaptureContext could be accessed via DataCaptureContext.licensed or DataCaptureContext.shared
// without explicit initialization
context = DataCaptureContext.licensed
```

**v8+ — explicit initialization required (NEW):**
```swift
// v8+: must call initialize(licenseKey:) before accessing DataCaptureContext.shared
DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
let context = DataCaptureContext.shared
```

If you skip initialization, accessing `DataCaptureContext.shared` will crash or return an invalid context.

### 2. Scanner property renamed and wrapped

**v7 — `scannerType` direct assignment (OLD):**

```swift
// v7
settings.scannerType = FullDocumentScanner()
settings.scannerType = SingleSideScanner(enablingBarcode: true, machineReadableZone: true, visualInspectionZone: true)
```

**v8+ — `scanner` with `IdCaptureScanner` wrapper (NEW):**

```swift
// v8+
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
settings.scanner = IdCaptureScanner(
    physicalDocument: SingleSideScanner(enablingBarcode: true, machineReadableZone: true, visualInspectionZone: true)
)
```

Wrap every scanner subclass in `IdCaptureScanner(physicalDocument:)`. To combine a physical and mobile scanner:

```swift
settings.scanner = IdCaptureScanner(
    physicalDocument: FullDocumentScanner(),
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false)
)
```

### 3. Image opt-in API changed

`resultShouldContainImage(_:forImageType:)` was deprecated in v7.6 and removed in v8.

**v7.6 deprecated / v8 removed (OLD):**
```swift
settings.resultShouldContainImage(true, forImageType: .face)
```

**v8+ (NEW):**
```swift
settings.setIncludeImage(true, for: .face)
```

### 4. Verification result model

In v7, verification required calling a separate `AamvaBarcodeVerifier` object (available on some platforms). In v8, **verification is entirely settings-driven** — there is no verifier class on native iOS.

```swift
// v8+ settings-driven verification:
settings.rejectForgedAamvaBarcodes = true
settings.rejectInconsistentData = true

// Read the outcome in the callbacks:
// In didCapture:
let verificationResult = capturedId.verificationResult
let frontReviewImage = verificationResult.dataConsistency?.frontReviewImage

// In didReject (for .forgedAamvaBarcode or .inconsistentData):
let frontReviewImage = capturedId?.verificationResult.dataConsistency?.frontReviewImage
```

### After applying v7 → v8 changes

1. Search for `scannerType` — replace every occurrence with `scanner = IdCaptureScanner(physicalDocument: ...)`.
2. Search for `DataCaptureContext.licensed` — replace with `DataCaptureContext.initialize(licenseKey:)` + `DataCaptureContext.shared`.
3. Search for `resultShouldContainImage` — replace with `setIncludeImage(_:for:)`.
4. Build and verify the camera preview appears and documents are recognized.
