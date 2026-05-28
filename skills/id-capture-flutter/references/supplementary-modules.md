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

## Related rejection / verification flags (no add-on package required)

These live in the base module and don't need a separate package, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `RejectionReason.documentExpired`
- `settings.rejectIdsExpiringIn = Duration(days: 30)` → `RejectionReason.documentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `RejectionReason.holderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `RejectionReason.notRealIdCompliant`
- `settings.rejectInconsistentData = true` → `RejectionReason.inconsistentData`; the detail is on `capturedId.verificationResult.dataConsistency`

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/flutter/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html)
