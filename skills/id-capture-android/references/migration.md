# ID Capture Android — Migration Guide

This guide covers the breaking changes in the Scandit Android SDK across major versions. Read the section that matches your current version.

---

## Step 1 — Identify your current SDK version

Check the version pinned for `com.scandit.datacapture:id` / `:core` in `app/build.gradle` (or `build.gradle.kts`). Then follow the matching section below:
- On **6.x** → follow [v6 → v7](#v6--v7-breaking-changes) then [v7 → v8](#v7--v8-breaking-changes)
- On **7.x** → follow [v7 → v8](#v7--v8-breaking-changes) only

## Step 2 — Update the dependency version

Fetch the latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/id` and bump both dependencies:

```gradle
implementation "com.scandit.datacapture:id:<latest-version>"
implementation "com.scandit.datacapture:core:<latest-version>"
```

Keep `id` and `core` on the same version. Then apply the source changes below.

---

## v6 → v7: Breaking Changes

This is a large, compile-breaking migration. The v6 API used a bitmask enum for document selection, a session/frame-data listener model, and per-zone callbacks. All of these changed in v7.

### Listener callbacks completely redesigned

The entire callback contract changed from frame-based to document-based.

**v6 — session-based callbacks, fire per zone:**

```kotlin
// v6 — IdCaptureListener (OLD)
override fun onIdCaptured(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) {
    val capturedId = session.newlyCapturedId ?: return
    // capturedId here is a partial result — may not have both sides yet
    idCapture.isEnabled = false
    showResult(capturedId)
}

override fun onIdLocalized(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) { }
override fun onIdRejected(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) { }
override fun onErrorEncountered(idCapture: IdCapture, error: Throwable, session: IdCaptureSession, frameData: FrameData) { }
override fun onObservationStarted(idCapture: IdCapture) { }
override fun onObservationStopped(idCapture: IdCapture) { }
```

**v7+ — two direct-result callbacks, fire once per complete document:**

```kotlin
// v7+ — IdCaptureListener (NEW). The interface parameters are named mode / id / reason.
override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
    mode.isEnabled = false
    showResult(id)
}

override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
    mode.isEnabled = false
    showRejectionMessage(reason)
}
```

**What to change:**
- Change `onIdCaptured(idCapture, session, frameData)` → `onIdCaptured(mode, id)`. Read the `CapturedId` directly from the parameter, not from `session.newlyCapturedId`.
- Change `onIdRejected(idCapture, session, frameData)` → `onIdRejected(mode, id, reason)`. The `RejectionReason` is now passed directly.
- Delete `onIdLocalized`, `onErrorEncountered`, `onObservationStarted`/`onObservationStopped` overrides — these are no longer part of the result contract. Handle `RejectionReason.TIMEOUT` inside `onIdRejected`.
- Delete all `IdCaptureSession` references — the class was removed.
- Delete all `FrameData` references in ID-capture callbacks — frame data is no longer passed.

> **Gotcha:** In v6, `onIdCaptured` fired once per recognized scan zone (MRZ, VIZ, barcode) — potentially multiple times for a two-sided document. In v7+, it fires exactly once per complete document. Apps that relied on partial per-zone results must be rewritten to handle a single complete `CapturedId`.

### Document selection model replaced

The v6 bitmask was replaced by a list of document objects with explicit regions.

**v6 — bitmask (OLD):**

```kotlin
// v6
settings.supportedDocuments = EnumSet.of(IdDocumentType.ID_CARD_VIZ, IdDocumentType.DL_VIZ, IdDocumentType.PASSPORT_MRZ)
settings.supportedSides = SupportedSides.FRONT_AND_BACK
```

**v7+ — object list (NEW):**

```kotlin
// v7+
settings.acceptedDocuments = listOf(
    IdCard(IdCaptureRegion.ANY),
    DriverLicense(IdCaptureRegion.ANY),
    Passport(IdCaptureRegion.ANY),
)
settings.scanner = IdCaptureScanner(FullDocumentScanner())
```

In v6, `supportedDocuments` controlled both which document types to scan AND which zones to read (the VIZ, MRZ, and barcode suffixes encoded the zone). In v7+, these are separated: document types go in `acceptedDocuments`, and zone selection goes in the `scanner`.

**Step 1 — translate document types to `acceptedDocuments`:**

| v6 `IdDocumentType` value | v7+ `acceptedDocuments` entry |
|---|---|
| `ID_CARD_VIZ`, `ID_CARD_MRZ` | `IdCard(IdCaptureRegion.ANY)` |
| `DL_VIZ`, `DL_MRZ`, `DL_BARCODE` | `DriverLicense(IdCaptureRegion.ANY)` |
| `PASSPORT_MRZ` | `Passport(IdCaptureRegion.ANY)` |
| `VISA_ICAO_MRZ` | `VisaIcao(IdCaptureRegion.ANY)` |
| `RESIDENCE_PERMIT_MRZ` | `ResidencePermit(IdCaptureRegion.ANY)` |
| `HEALTH_INSURANCE_CARD` | `HealthInsuranceCard(IdCaptureRegion.ANY)` |
| (US-specific barcode variants) | `DriverLicense(IdCaptureRegion.US)` |

**Step 2 — translate zone suffixes to a `scanner`:**

| v6 zones in use | v7+ scanner |
|---|---|
| VIZ only | `SingleSideScanner(barcode = false, machineReadableZone = false, visualInspectionZone = true)` |
| MRZ only | `SingleSideScanner(barcode = false, machineReadableZone = true, visualInspectionZone = false)` |
| Barcode only | `SingleSideScanner(barcode = true, machineReadableZone = false, visualInspectionZone = false)` |
| Multiple zones / both sides | `FullDocumentScanner()` |

`FullDocumentScanner()` is also the direct equivalent of `supportedSides = FRONT_AND_BACK` — it reads all zones from both sides automatically.

### Image opt-in renamed

```kotlin
// v6/v7 (OLD):
settings.setShouldPassImageTypeToResult(IdImageType.ID_FRONT, true)   // v6 image types
// v8+ (NEW):
settings.setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true)
settings.setShouldPassImageTypeToResult(IdImageType.FACE, true)
settings.setShouldPassImageTypeToResult(IdImageType.FRAME, true)
val croppedFront = capturedId.images.getCroppedDocument(IdSide.FRONT)
val face = capturedId.images.face
```

### Result model flattened

In v6, `CapturedId` had a separate barcode/MRZ result property per document type. In v7+ these were unified: all barcode results via `capturedId.barcode`, all MRZ results via `capturedId.mrz`, all VIZ via `capturedId.viz`. Delete references to the old per-document result properties and use the unified accessors. `capturedId.issuingCountry` is now an `IdCaptureRegion` enum, not a `String`.

### After applying v6 → v7 changes

Run a build. Expect compile errors anywhere `IdCaptureSession`, `FrameData` (in ID callbacks), `supportedDocuments`, `supportedSides`, `IdDocumentType`, the old per-zone callbacks, or the old per-document result properties appear. Fix each in turn using the patterns above.

---

## v7 → v8: Breaking Changes

This is a smaller migration but important to get right.

### Scanner property renamed and wrapped

**v7 — `scannerType` direct assignment (OLD):**

```kotlin
// v7
settings.scannerType = FullDocumentScanner()
settings.scannerType = SingleSideScanner(barcode = true, machineReadableZone = true, visualInspectionZone = true)
```

**v8+ — `scanner` with `IdCaptureScanner` wrapper (NEW):**

```kotlin
// v8+
settings.scanner = IdCaptureScanner(FullDocumentScanner())
settings.scanner = IdCaptureScanner(
    SingleSideScanner(barcode = true, machineReadableZone = true, visualInspectionZone = true)
)
```

Wrap every scanner subclass in `IdCaptureScanner(...)`. To combine a physical and mobile scanner:

```kotlin
settings.scanner = IdCaptureScanner(
    physicalDocument = FullDocumentScanner(),
    mobileDocument = MobileDocumentScanner(iso180135 = true, ocr = false)
)
```

### Verification verifiers removed

In v7, verification used verifier objects (`DataConsistencyVerifier`, `AamvaBarcodeVerifier`). Both are removed in v8 and replaced by settings flags:

```kotlin
// v7 — explicit verifier calls (OLD):
val consistencyResult = DataConsistencyVerifier.create(context).verify(capturedId)
val barcodeResult = AamvaBarcodeVerifier.create(context).verify(capturedId)

// v8+ — settings-driven (NEW):
settings.rejectInconsistentData = true
settings.rejectForgedAamvaBarcodes = true

// Results are delivered via the standard callbacks:
val frontReviewImage = capturedId.verificationResult?.dataConsistency?.frontReviewImage
```

### After applying v7 → v8 changes

1. Search for `scannerType` — replace every occurrence with `scanner = IdCaptureScanner(...)`.
2. Search for `DataConsistencyVerifier` / `AamvaBarcodeVerifier` — replace with `rejectInconsistentData` / `rejectForgedAamvaBarcodes` flags + read `capturedId.verificationResult`.
3. Build and verify the camera preview appears and documents are recognized.

## After migrating

- Build and type-check the project.
- See the official guides: [Migrate 6→7](https://docs.scandit.com/sdks/android/migrate-6-to-7/) · [Migrate 7→8](https://docs.scandit.com/sdks/android/migrate-7-to-8/).
