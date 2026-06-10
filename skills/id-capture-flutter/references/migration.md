# ID Capture Flutter Migration Guide

This guide covers upgrading an existing ID Capture integration across major SDK versions. The biggest breaking changes for Flutter landed at **v7 → v8**: the scanner property was renamed and reshaped, and the standalone `AamvaBarcodeVerifier` was removed. (The earlier `supportedDocuments` bitmask → `acceptedDocuments` change happened at v6 → v7 and is summarized at the end.)

Do not guess at the old or new signatures — follow the concrete before/after below, and verify anything else against the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html).

## Step 1 — Detect the installed version and current API

Check `pubspec.yaml` for the `scandit_flutter_datacapture_*` versions, and look at the code:

- Uses `settings.scannerType = ...` and/or `AamvaBarcodeVerifier` → **pre-v8 (v7) code**; migrate per Steps 2–3.
- Uses `settings.supportedDocuments` / `IdDocumentType` → **pre-v7 (v6) code**; see Step 7 first, then continue.
- Already uses `settings.scanner = IdCaptureScanner(physicalDocumentScanner: ...)` → on v8; only Steps 4–6 (optional adoption) apply.

## Step 2 — Migrate the scanner property (`scannerType` → `scanner`)

In v7, `SingleSideScanner` / `FullDocumentScanner` were assigned directly to `scannerType`. In v8 they are `PhysicalDocumentScanner`s wrapped in an `IdCaptureScanner`, assigned to `scanner`.

```dart
// BEFORE (v7)
final settings = IdCaptureSettings();
settings.scannerType = FullDocumentScanner();
// or: settings.scannerType = SingleSideScanner(true, false, false);

// AFTER (v8)
final settings = IdCaptureSettings();
settings.scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());
// or: settings.scanner = IdCaptureScanner(
//       physicalDocumentScanner: SingleSideScanner(true, false, false));
```

`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` keeps the same three positional booleans — only the wrapping and the property name changed. To scan mobile documents, pass `mobileDocumentScanner:` instead of (or in addition to) `physicalDocumentScanner:`.

> The default `IdCaptureSettings()` constructor in v8 produces a scanner that scans **nothing** and an empty `acceptedDocuments`. After upgrading, make sure you explicitly set both `scanner` and `acceptedDocuments` — relying on constructor defaults will silently capture nothing.

## Step 3 — Replace `AamvaBarcodeVerifier` with the settings flag

The standalone verifier class was removed on Flutter. AAMVA verification is now a settings flag, and the result is delivered on the `CapturedId`.

```dart
// BEFORE (v7) — standalone verifier
final verifier = await AamvaBarcodeVerifier.create(context);
// ...later, inside didCaptureId:
final AamvaBarcodeVerificationResult result = await verifier.verify(capturedId);

// AFTER (v8) — settings flag + result on CapturedId
settings.rejectForgedAamvaBarcodes = true; // forged barcodes -> didRejectId(reason: forgedAamvaBarcode)
// ...inside didCaptureId, inspect the verification result:
final aamva = capturedId.verificationResult.aamvaBarcodeVerification;
final status = aamva?.status; // authentic / likelyForged / forged
```

Add the AAMVA add-on package to `pubspec.yaml` (it ships the native models):

```yaml
dependencies:
  scandit_flutter_datacapture_id_aamva_barcode_verification: <sdk-version>
```

Remove any `import` of `AamvaBarcodeVerifier` — it no longer exists. See `references/supplementary-modules.md` for the full result shape.

## Step 4 — Adopt the new rejection flags (optional)

v8 adds declarative rejection. Prefer these over manual post-capture checks; each surfaces a specific `RejectionReason` in `didRejectId`:

```dart
settings.rejectExpiredIds = true;                 // -> documentExpired
settings.rejectIdsExpiringIn = Duration(days: 30);// -> documentExpiresSoon
settings.rejectHolderBelowAge = 18;               // -> holderUnderage
settings.rejectNotRealIdCompliant = true;         // -> notRealIdCompliant
settings.rejectInconsistentData = true;           // -> inconsistentData
settings.rejectVoidedIds = true;                  // -> documentVoided (needs voided-detection add-on)
```

## Step 5 — Adopt verification & richer results (optional)

- `capturedId.verificationResult` now carries `dataConsistency` (`DataConsistencyResult?`, enable via `rejectInconsistentData`) and `aamvaBarcodeVerification`.
- `capturedId.viz?.drivingLicenseDetails` exposes `drivingLicenseCategories`, `restrictions`, `endorsements` when `decodeBackOfEuropeanDrivingLicense` is enabled (needs the europe-driving-license add-on). See `references/supplementary-modules.md`.
- Mobile documents: read `capturedId.mobileDocument` / `capturedId.mobileDocumentOcr` when using a `MobileDocumentScanner`.
- v8.5 additions: `SingleSideScanner.withFreeFormText(barcode, machineReadableZone, visualInspectionZone, freeFormText)` and `MobileDocumentScanner(..., elementsToRetain: {...})`.

## Step 6 — Verify the listener and lifecycle still match

The listener contract is unchanged across v7 → v8: implement `IdCaptureListener` with `didCaptureId(IdCapture, CapturedId)` and `didRejectId(IdCapture, CapturedId?, RejectionReason)`. Camera setup (`IdCapture.createRecommendedCameraSettings()`), the `DataCaptureView` + `IdCaptureOverlay`, and `context.setMode(idCapture)` are also unchanged. No migration needed there.

## Step 7 — If you are coming from v6 (`supportedDocuments`)

In v6, documents were selected with a `supportedDocuments` bitmask of `IdDocumentType`, the sides were chosen with `supportedSides`, and the document type was read from `capturedId.documentType`. All three were removed at v7. Move to the list-based model:

```dart
// BEFORE (v6, removed):
// settings.supportedDocuments = IdDocumentType.idCardViz | IdDocumentType.passportMrz;
// settings.supportedSides = SupportedSides.frontAndBack;

// AFTER (v7+): declare documents and a scanner explicitly
settings.acceptedDocuments.addAll([
  IdCard(IdCaptureRegion.any),
  Passport(IdCaptureRegion.any),
]);
settings.scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner()); // v8 form
```

The document **type** also moved off `CapturedId`. Replace `capturedId.documentType` (removed, along with the `IdDocumentType` enum) with `capturedId.document?.documentType` (an `IdCaptureDocumentType`) or the convenience methods `isPassport()` / `isDriverLicense()` / `isIdCard()` / …:

```dart
// BEFORE (v6, removed): final type = capturedId.documentType;
// AFTER (v7+):
final IdCaptureDocumentType? type = capturedId.document?.documentType;
// or: if (capturedId.isPassport()) { ... }
```

For the full v6 → v7 details, see the [6 → 7 migration guide](https://docs.scandit.com/sdks/flutter/migrate-6-to-7/) and the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html).

## Step 8 — Verify

- The project compiles with no references to `scannerType`, `AamvaBarcodeVerifier`, `supportedDocuments`, or `IdDocumentType`.
- `acceptedDocuments` and `scanner` are both set explicitly.
- A test scan delivers a `CapturedId` in `didCaptureId`, and an out-of-scope document triggers `didRejectId`.

## Reference links

- [7 → 8 migration guide](https://docs.scandit.com/sdks/flutter/migrate-7-to-8/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
