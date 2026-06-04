# ID Capture iOS — Migration Guide

This guide covers the breaking changes in the Scandit iOS SDK across major versions. Read the section that matches your current version.

---

## Step 1 — Identify your current SDK version

Check the version pinned in your `Package.resolved` or SPM dependency graph for `datacapture-spm`. Then follow the matching section below:
- On **6.x** → follow [v6 → v7](#v6--v7-breaking-changes) then [v7 → v8](#v7--v8-breaking-changes)
- On **7.x** → follow [v7 → v8](#v7--v8-breaking-changes) only

---

## v6 → v7: Breaking Changes

This is a large, compile-breaking migration. The v6 API used a bitmask enum for document selection, a session/frame-data listener model, and per-zone callbacks. All of these changed in v7.

### Listener callbacks completely redesigned

The entire callback contract changed from frame-based to document-based.

**v6 — five session-based callbacks, fire per zone:**

```swift
// v6 — IdCaptureListener (OLD)
extension ViewController: IdCaptureListener {

    // REQUIRED — fires once per recognized zone; SDK gives you a partial CapturedId via the session
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

### Document selection model replaced

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

In v6, `supportedDocuments` controlled both which document types to scan AND which zones to read (the VIZ, MRZ, and barcode suffixes encoded the zone). In v7+, these are separated: document types go in `acceptedDocuments`, and zone selection goes in the `scanner`. You need to translate both.

**Step 1 — translate document types to `acceptedDocuments`:**

| v6 `supportedDocuments` value | v7+ `acceptedDocuments` entry |
|---|---|
| `.idCardVIZ`, `.idCardMRZ` | `IdCard(region: .any)` |
| `.dlVIZ`, `.dlMRZ`, `.dlBarcode` | `DriverLicense(region: .any)` |
| `.passportMRZ` | `Passport(region: .any)` |
| `.visaIcaoMRZ` | `VisaIcao(region: .any)` |
| `.residencePermitMRZ` | `ResidencePermit(region: .any)` |
| `.healthInsuranceCard` | `HealthInsuranceCard(region: .any)` |
| (US-specific barcode variants) | `DriverLicense(region: .us)` |

**Step 2 — translate zone suffixes to a `scanner`:**

The zone suffixes in the old enum (VIZ, MRZ, barcode) now map to `SingleSideScanner` flags, or `FullDocumentScanner` if you were scanning multiple zones across both sides:

| v6 zones in use | v7+ scanner |
|---|---|
| VIZ only | `SingleSideScanner(enablingBarcode: false, machineReadableZone: false, visualInspectionZone: true)` |
| MRZ only | `SingleSideScanner(enablingBarcode: false, machineReadableZone: true, visualInspectionZone: false)` |
| Barcode only | `SingleSideScanner(enablingBarcode: true, machineReadableZone: false, visualInspectionZone: false)` |
| Multiple zones / both sides | `FullDocumentScanner()` |

`FullDocumentScanner()` is also the direct equivalent of `supportedSides = .frontAndBack` — it reads all zones from both sides automatically.

### Scanner selection replaced

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

// v8+ also introduces MobileDocumentScanner via the same wrapper:
settings.scanner = IdCaptureScanner(
    physicalDocument: FullDocumentScanner(),
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false)
)
```

> If you're coming from v6, write the v8+ form directly (skip the v7 intermediate).

### Image types renamed

**v6:**
```swift
settings.resultShouldContainImage(true, forIdCaptureType: .idFront)
settings.resultShouldContainImage(true, forIdCaptureType: .idBack)
let frontImage = capturedId.imageForType(.idFront)
```

**v7:**
```swift
settings.resultShouldContainImage(true, forImageType: .croppedDocument)
settings.resultShouldContainImage(true, forImageType: .face)
settings.resultShouldContainImage(true, forImageType: .frame)
let croppedFront = capturedId.images.croppedDocumentForSide(.front)
let croppedBack  = capturedId.images.croppedDocumentForSide(.back)
let face         = capturedId.images.face
```

**v8+:**
```swift
settings.setIncludeImage(true, for: .croppedDocument)
settings.setIncludeImage(true, for: .face)
settings.setIncludeImage(true, for: .frame)
let croppedFront = capturedId.images.croppedDocument(side: .front)
let croppedBack  = capturedId.images.croppedDocument(side: .back)
let face         = capturedId.images.face
```

### Frame image retrieval changed

In v6, the raw camera frame was available via the `FrameData` parameter passed to the callback. In v7+, frame images are accessed via `capturedId.images.frame` after opting in via the settings:

```swift
// v7:
settings.resultShouldContainImage(true, forImageType: .frame)

// v8+:
settings.setIncludeImage(true, for: .frame)

// Accessing the frame image (same in v7 and v8+):
let frameImage: UIImage? = capturedId.images.frame
```

### Rejection model

In v6, rejection was detected by inspecting `session.newlyRejectedId` in the callback. In v7+, `didReject(_:capturedId:reason:)` delivers the reason directly. Replace session inspection with the `RejectionReason` switch pattern shown above.

Rejection flags (`rejectExpiredIds`, `rejectHolderBelowAge`, etc.) are new in v7.6 — they did not exist in v6. You can now set rules directly on settings instead of implementing the logic yourself.

### Verification verifiers consolidated

In v6, data consistency verification required two separate verifier objects:
- `AAMVAVizBarcodeComparisonVerifier` — compared AAMVA barcode data against the VIZ
- `VizMrzComparisonVerifier` — compared VIZ data against the MRZ

In v7, these were unified into a single `DataConsistencyVerifier`:

```swift
// v6 — two separate verifiers:
let vizBarcodeVerifier = AAMVAVizBarcodeComparisonVerifier(context: context)
let barcodeResult = vizBarcodeVerifier.verify(capturedId)

let vizMrzVerifier = VizMrzComparisonVerifier(context: context)
let mrzResult = vizMrzVerifier.verify(capturedId)

// v7 — unified:
let verifier = DataConsistencyVerifier(context: context)
let result = verifier.verify(capturedId)  // handles both VIZ/barcode and VIZ/MRZ comparisons
```

`AAMVABarcodeVerifier` (forged barcode detection) was present in both v6 and v7 and is not affected by this consolidation — it is replaced in v8 (see below).

### Result model flattened

In v6, `CapturedId` had a separate barcode result property for each supported document type — `aamvaBarcodeResult`, `colombiaDlBarcodeResult`, `southAfricaDLBarcodeResult`, `usUniformedServicesBarcodeResult`, and several China-specific MRZ result variants, among others. Similarly there were multiple specialised MRZ result types.

In v7 these were unified: all barcode results are accessed via the single `capturedId.barcode: BarcodeResult?` property, and all MRZ results via `capturedId.mrzResult: MrzResult?`. Delete any references to the old per-document result properties and replace with the unified accessors:

| v6 | v7+ |
|---|---|
| `capturedId.aamvaBarcodeResult` | `capturedId.barcode` |
| `capturedId.colombiaDlBarcodeResult` | `capturedId.barcode` |
| `capturedId.southAfricaDLBarcodeResult` | `capturedId.barcode` |
| `capturedId.chinaMainlandTravelPermitMrzResult` | `capturedId.mrzResult` |
| (other per-document barcode/MRZ properties) | `capturedId.barcode` or `capturedId.mrzResult` |
| `capturedId.issuingCountry` as `String` | `capturedId.issuingCountry` as `IdCaptureRegion` enum |

### After applying v6 → v7 changes

Run a build. Expect compile errors anywhere `IdCaptureSession`, `FrameData`, `supportedDocuments`, `supportedSides`, `IdDocumentType`, `didCaptureIn`, `didRejectIn`, `didLocalizeIn`, `didTimeoutIn`, `imageForType`, `AAMVAVizBarcodeComparisonVerifier`, or `VizMrzComparisonVerifier` appear. Fix each in turn using the patterns above.

---

## v7 → v8: Breaking Changes

This is a smaller migration but important to get right.

### Scanner property renamed and wrapped

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

### Image opt-in API changed

`resultShouldContainImage(_:forImageType:)` was deprecated in v7.6 and removed in v8.

**v7.6 deprecated / v8 removed (OLD):**
```swift
settings.resultShouldContainImage(true, forImageType: .face)
```

**v8+ (NEW):**
```swift
settings.setIncludeImage(true, for: .face)
```

### Verification verifiers removed

In v7, verification used two verifier objects: `DataConsistencyVerifier` (data consistency checks) and `AAMVABarcodeVerifier` (forged barcode detection). Both are removed in v8 and replaced by settings flags — `DataConsistencyVerifier` was already deprecated in v7.6.

```swift
// v7 — explicit verifier calls (OLD):
let consistencyVerifier = DataConsistencyVerifier(context: context)
let consistencyResult = consistencyVerifier.verify(capturedId)

let barcodeVerifier = AAMVABarcodeVerifier(context: context)
let barcodeResult = barcodeVerifier.verify(capturedId)

// v8+ — settings-driven (NEW):
settings.rejectInconsistentData = true
settings.rejectForgedAamvaBarcodes = true

// Results are delivered via the standard callbacks:
// In didCapture:
let frontReviewImage = capturedId.verificationResult.dataConsistency?.frontReviewImage

// In didReject (for .inconsistentData or .forgedAamvaBarcode):
let frontReviewImage = capturedId?.verificationResult.dataConsistency?.frontReviewImage
```

### After applying v7 → v8 changes

1. Search for `scannerType` — replace every occurrence with `scanner = IdCaptureScanner(physicalDocument: ...)`.
2. Search for `resultShouldContainImage` — replace with `setIncludeImage(_:for:)`.
3. Build and verify the camera preview appears and documents are recognized.
