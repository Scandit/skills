# ID Capture Add-On Capabilities (Flutter)

Three ID Capture capabilities ship as **separate Flutter packages** because they bundle additional native models. The pattern is the same for all three:

1. **Add the package** to `pubspec.yaml` (this is what unlocks the native models).
2. **Set one flag** on `IdCaptureSettings` (the API lives in the base `scandit_flutter_datacapture_id` module — these add-on packages expose no Dart API of their own).
3. **Read the result** off the `CapturedId`, or handle the corresponding `RejectionReason`.

> There is **no standalone verifier or scanner class** for these on Flutter (no `AamvaBarcodeVerifier`, no voided-detection object). Everything is driven by the settings flags below. Don't import classes from the add-on packages — they only declare a library.

You still initialize ID Capture exactly as in `references/integration.md`; these flags layer on top of an existing `IdCaptureSettings`.

---

## 1. Voided-ID detection

Rejects voided / cancelled documents (punched-hole or marked-void IDs). Primarily tuned for **US driver's licenses** — results may be less accurate on other document types.

**Package** (`pubspec.yaml`):

```yaml
dependencies:
  scandit_flutter_datacapture_id_voided_detection: <sdk-version>
```

**Enable** (Flutter `6.25+`):

```dart
settings.rejectVoidedIds = true;
```

**Handle the rejection** — voided documents arrive in `didRejectId` with `RejectionReason.documentVoided`:

```dart
@override
Future<void> didRejectId(
    IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
  if (reason == RejectionReason.documentVoided) {
    // Tell the user the document appears voided/cancelled.
  }
}
```

---

## 2. European driving-license back decoding

Decodes the **back of European driving licenses** to extract vehicle-category data (categories, restrictions, endorsements, per-category issue/expiry dates).

**Package** (`pubspec.yaml`):

```yaml
dependencies:
  scandit_flutter_datacapture_id_europe_driving_license: <sdk-version>
```

**Enable** (Flutter `7.0+`) — also use a scanner that reads the back (`FullDocumentScanner`, or a `SingleSideScanner` with VIZ enabled):

```dart
settings.decodeBackOfEuropeanDrivingLicense = true;
settings.scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());
```

**Read the result** — the decoded categories appear on the VIZ result as `DrivingLicenseDetails` (Flutter `8.0+`):

```dart
@override
Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
  final details = capturedId.viz?.drivingLicenseDetails;
  if (details != null) {
    final List<DrivingLicenseCategory> categories = details.drivingLicenseCategories;
    final String? restrictions = details.restrictions;
    final String? endorsements = details.endorsements;
    for (final category in categories) {
      // DrivingLicenseCategory getters: code (String), dateOfIssue, dateOfExpiry (DateResult?).
      // There is no `categoryCode` getter — use `code`.
      print('${category.code}: ${category.dateOfIssue?.localDate} – ${category.dateOfExpiry?.localDate}');
    }
  }
}
```

---

## 3. AAMVA barcode verification

Verifies the PDF417 barcode on the back of **US / Canadian (AAMVA) driver's licenses** to detect forgeries.

**Package** (`pubspec.yaml`):

```yaml
dependencies:
  scandit_flutter_datacapture_id_aamva_barcode_verification: <sdk-version>
```

**Enable** (Flutter `7.3+`) — there is no separate verifier object on Flutter; it's a settings flag:

```dart
settings.rejectForgedAamvaBarcodes = true;
```

**Two ways to consume the result:**

- **Rejection path** — when `rejectForgedAamvaBarcodes` is `true`, a forged barcode is rejected with `RejectionReason.forgedAamvaBarcode`:

  ```dart
  if (reason == RejectionReason.forgedAamvaBarcode) {
    // Document barcode failed verification.
  }
  ```

- **Inspect the verification result** on a captured document via `verificationResult.aamvaBarcodeVerification`:

  ```dart
  final aamva = capturedId.verificationResult.aamvaBarcodeVerification;
  if (aamva != null) {
    final bool passed = aamva.allChecksPassed;
    switch (aamva.status) {
      case AamvaBarcodeVerificationStatus.authentic:
        break;
      case AamvaBarcodeVerificationStatus.likelyForged:
        break;
      case AamvaBarcodeVerificationStatus.forged:
        break;
    }
  }
  ```

---

## 4. Data-consistency verification

Cross-checks the document's human-readable data (VIZ) against the data encoded in its MRZ or barcode, and rejects documents whose fields don't agree (a common forgery / tampering signal). **No add-on package** — this lives in the base `scandit_flutter_datacapture_id` module.

**Enable** — set the settings flag; inconsistent documents are rejected with `RejectionReason.inconsistentData`:

```dart
settings.rejectInconsistentData = true;
```

**Handle the rejection** in `didRejectId`:

```dart
@override
Future<void> didRejectId(
    IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
  if (reason == RejectionReason.inconsistentData) {
    // The document's printed data did not match its MRZ / barcode.
  }
}
```

**Inspect the detail** on a captured document via `capturedId.verificationResult.dataConsistency` (a `DataConsistencyResult?`):

```dart
final consistency = capturedId.verificationResult.dataConsistency;
if (consistency != null) {
  final bool passed = consistency.allChecksPassed;
  final Set<DataConsistencyCheck> failed = consistency.failedChecks;
  // Also: consistency.passedChecks, consistency.skippedChecks (Set<DataConsistencyCheck>),
  // and consistency.frontReviewImage (Image?) highlighting the mismatched fields.
}
```

`DataConsistencyCheck` values: `issuingCountryComparison`, `issuingJurisdictionComparison`, `fullNameComparison`, `documentNumberComparison`, `dateOfBirthComparison`, `dateOfExpiryComparison`, `dateOfIssueComparison`.

> `rejectInconsistentData = true` both rejects mismatched documents and populates `verificationResult.dataConsistency` on captured ones. With it `false`, `dataConsistency` is `null`.

---

## 5. Mobile documents (mDL / ISO 18013-5)

Reads **mobile driver's licenses** (mDL) — both the offline ISO 18013-5 mdoc exchange and the OCR of the on-screen rendering. This is GA, but thin in the guide docs. **No add-on package** — `MobileDocumentScanner` lives in the base `scandit_flutter_datacapture_id` module.

Mobile documents are read by a `MobileDocumentScanner`, supplied to `IdCaptureScanner` via the named `mobileDocumentScanner:` argument (the physical scanner is the separate `physicalDocumentScanner:` argument):

```dart
// Mobile documents only:
settings.scanner = IdCaptureScanner(
    mobileDocumentScanner: MobileDocumentScanner(iso180135: true, ocr: false));

// Physical + mobile documents in the same session:
settings.scanner = IdCaptureScanner(
    physicalDocumentScanner: FullDocumentScanner(),
    mobileDocumentScanner: MobileDocumentScanner(iso180135: true, ocr: false));
```

`MobileDocumentScanner(iso180135: true, ocr: false)` enables the ISO 18013-5 mdoc path and disables OCR; `MobileDocumentScanner(iso180135: false, ocr: true)` reads only the OCR of the on-screen document. An optional `elementsToRetain: {...}` set of `MobileDocumentDataElement` declares which fields the app intends to retain, setting the `IntentToRetain` flag in the ISO 18013-5 request.

**Read the result** — mobile-document data arrives in source-specific getters on `CapturedId`:

```dart
@override
Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
  final mobile = capturedId.mobileDocument;     // MobileDocumentResult? (ISO 18013-5 mdoc)
  if (mobile != null) {
    print('${mobile.fullName} ${mobile.dateOfBirth}');
  }
  final ocr = capturedId.mobileDocumentOcr;     // on-screen OCR result (nullable)
  // The harmonized top-level fields (capturedId.fullName, dateOfBirth, …) are still
  // populated for mobile documents — reach into mobileDocument / mobileDocumentOcr
  // only for mobile-specific data.
}
```

> Document type is read via `capturedId.document?.documentType` — there is no `IdDocumentType` bitmask, and no `AamvaBarcodeVerifier` is involved here.

---

## Related rejection flags (no add-on package required)

These live in the base module and don't need a separate package, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `RejectionReason.documentExpired`
- `settings.rejectIdsExpiringIn = Duration(days: 30)` → `RejectionReason.documentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `RejectionReason.holderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `RejectionReason.notRealIdCompliant`

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/flutter/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html)
