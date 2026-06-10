# ID Capture Add-On Capabilities (React Native)

Sections 1–3 below ship as **separate React Native packages** because they bundle additional native models. The pattern is the same for all three:

1. **Add the package** to `package.json` (this is what unlocks the native models — and on iOS, the corresponding pod).
2. **Set one flag** on `IdCaptureSettings` (the API lives in the base `scandit-react-native-datacapture-id` package — these add-on packages expose **no JavaScript API of their own**, only a native module bridge).
3. **Read the result** off the `CapturedId`, or handle the corresponding `RejectionReason`.

Sections 4–5 (data-consistency verification, mobile documents) need **no extra package** — they live entirely in the base `scandit-react-native-datacapture-id` package.

> The three add-on packages (sections 1–3) have **no standalone verifier or voided-detection class** on React Native (no `AamvaBarcodeVerifier`). Everything there is driven by the settings flags below — don't import classes from the add-on packages; they only register a `NativeModule`. (Mobile documents in section 5 are the one exception that uses a real class, `MobileDocumentScanner`, but that class ships in the **base** package, not an add-on.)

You still initialize ID Capture exactly as in `references/integration.md`; these flags layer on top of an existing `IdCaptureSettings`. After adding any of these packages on iOS, run `pod install` from `ios/`.

---

## 1. Voided-ID detection

Rejects voided / cancelled documents (punched-hole or marked-void IDs). Primarily tuned for **US driver's licenses** — results may be less accurate on other document types.

**Package** (`package.json`):

```json
{
  "dependencies": {
    "scandit-react-native-datacapture-id-voided-detection": "<sdk-version>"
  }
}
```

**Enable** (React Native `6.25+`):

```tsx
settings.rejectVoidedIds = true;
```

**Handle the rejection** — voided documents arrive in `didRejectId` with `RejectionReason.DocumentVoided`:

```tsx
const listener = {
  didRejectId: (_: IdCapture, rejectedId: CapturedId | null, reason: RejectionReason) => {
    if (reason === RejectionReason.DocumentVoided) {
      // Tell the user the document appears voided/cancelled.
    }
  },
};
```

---

## 2. European driving-license back decoding

Decodes the **back of European driving licenses** to extract vehicle-category data (categories, restrictions, endorsements, per-category issue/expiry dates).

**Package** (`package.json`):

```json
{
  "dependencies": {
    "scandit-react-native-datacapture-id-europe-driving-license": "<sdk-version>"
  }
}
```

**Enable** (React Native `7.0+`) — also use a scanner that reads the back (`FullDocumentScanner`, or a `SingleSideScanner` with VIZ enabled):

```tsx
settings.decodeBackOfEuropeanDrivingLicense = true;
settings.scanner = new IdCaptureScanner(new FullDocumentScanner());
```

**Read the result** — the decoded categories appear on the VIZ result as `DrivingLicenseDetails` (React Native `8.0+`):

```tsx
const listener = {
  didCaptureId: (_: IdCapture, capturedId: CapturedId) => {
    const details = capturedId.vizResult?.drivingLicenseDetails;
    if (details) {
      const categories = details.drivingLicenseCategories; // DrivingLicenseCategory[]
      const restrictions = details.restrictions;             // string | null
      const endorsements = details.endorsements;             // string | null
      for (const category of categories) {
        // DrivingLicenseCategory getters: code (string), dateOfIssue, dateOfExpiry (DateResult | null).
        // There is no `categoryCode` getter — use `code`.
        console.log(category.code, category.dateOfIssue, category.dateOfExpiry);
      }
    }
  },
};
```

---

## 3. AAMVA barcode verification

Verifies the PDF417 barcode on the back of **US / Canadian (AAMVA) driver's licenses** to detect forgeries.

**Package** (`package.json`):

```json
{
  "dependencies": {
    "scandit-react-native-datacapture-id-aamva-barcode-verification": "<sdk-version>"
  }
}
```

**Enable** (React Native `7.3+`) — there is no separate verifier object on RN any more; it's a settings flag:

```tsx
settings.rejectForgedAamvaBarcodes = true;
```

**Two ways to consume the result:**

- **Rejection path** — when `rejectForgedAamvaBarcodes` is `true`, a forged barcode is rejected with `RejectionReason.ForgedAamvaBarcode`:

  ```tsx
  if (reason === RejectionReason.ForgedAamvaBarcode) {
    // Document barcode failed verification.
  }
  ```

- **Inspect the verification result** on a captured document via `verificationResult.aamvaBarcodeVerification`:

  ```tsx
  import { AamvaBarcodeVerificationStatus } from 'scandit-react-native-datacapture-id';

  const aamva = capturedId.verificationResult.aamvaBarcodeVerification;
  if (aamva) {
    const passed: boolean = aamva.allChecksPassed;
    switch (aamva.status) {
      case AamvaBarcodeVerificationStatus.Authentic:
        break;
      case AamvaBarcodeVerificationStatus.LikelyForged:
        break;
      case AamvaBarcodeVerificationStatus.Forged:
        break;
    }
  }
  ```

---

## 4. Data-consistency verification

Cross-checks the human-readable data on a document against the data encoded in its barcode or MRZ (for a US driver's license — which has no MRZ — it compares the front VIZ against the back PDF417). A mismatch usually means a tampered or mis-read document. No add-on package is required — the flag and result live in the base `scandit-react-native-datacapture-id` package.

**Enable** — set the flag on `IdCaptureSettings`:

```tsx
settings.rejectInconsistentData = true;
```

**Two ways to consume the result:**

- **Rejection path** — when `rejectInconsistentData` is `true`, a document that fails the checks is rejected with `RejectionReason.InconsistentData`:

  ```tsx
  if (reason === RejectionReason.InconsistentData) {
    // Tell the user the data on the document is inconsistent.
  }
  ```

- **Inspect the consistency result** on the captured (or rejected) document via `verificationResult.dataConsistency`:

  ```tsx
  import { DataConsistencyCheck } from 'scandit-react-native-datacapture-id';

  const consistency = capturedId.verificationResult.dataConsistency;
  if (consistency) {
    const passed: boolean = consistency.allChecksPassed;
    const failed: DataConsistencyCheck[] = consistency.failedChecks;
    // failedChecks members, e.g. DataConsistencyCheck.FullNameComparison,
    // DataConsistencyCheck.DateOfBirthComparison, DataConsistencyCheck.DocumentNumberComparison.
    const reviewImage: string | null = consistency.frontReviewImage; // base64 string on RN, render via the data: URI form
  }
}
```

`DataConsistencyResult` getters on React Native: `allChecksPassed` (`boolean`), `failedChecks` / `passedChecks` / `skippedChecks` (`DataConsistencyCheck[]`), `frontReviewImage` (`string | null` — a base64 string, **not** a native image object; render it with `<Image source={{ uri: 'data:image/png;base64,' + reviewImage }} />`).

---

## 5. Mobile documents (mobile driver's licenses / ISO 18013-5 mDL)

Reads **mobile driver's licenses** (mDL) — both the offline ISO 18013-5 mdoc exchange and the OCR of the on-screen rendering. Mobile documents are read by a `MobileDocumentScanner`, passed as the **second** positional argument to `IdCaptureScanner` (the first is the physical-document scanner; pass `undefined` if you only want mobile documents). No add-on package is required — `MobileDocumentScanner` lives in the base `scandit-react-native-datacapture-id` package.

**Configure the scanner** — `MobileDocumentScanner(iso180135, ocr, elementsToRetain?)`:

```tsx
import { IdCaptureScanner, MobileDocumentScanner } from 'scandit-react-native-datacapture-id';

// Mobile documents only:
settings.scanner = new IdCaptureScanner(undefined, new MobileDocumentScanner(true, false));

// Physical + mobile documents in the same session:
settings.scanner = new IdCaptureScanner(new FullDocumentScanner(), new MobileDocumentScanner(true, false));
```

`MobileDocumentScanner(true, false)` enables the ISO 18013-5 mdoc path and disables OCR; `MobileDocumentScanner(false, true)` reads only the OCR of the on-screen document. The optional third argument is a `Set<MobileDocumentDataElement>` declaring which fields the app intends to retain — this sets the `IntentToRetain` flag in the ISO 18013-5 request (required for data-protection compliance); an empty/omitted set means no elements are retained.

```tsx
import { MobileDocumentDataElement } from 'scandit-react-native-datacapture-id';

const elementsToRetain = new Set([
  MobileDocumentDataElement.FamilyName,
  MobileDocumentDataElement.GivenName,
  MobileDocumentDataElement.BirthDate,
]);
settings.scanner = new IdCaptureScanner(undefined, new MobileDocumentScanner(true, false, elementsToRetain));
```

**Read the result** — mobile-document data arrives in two source-specific getters on `CapturedId`:

```tsx
const listener = {
  didCaptureId: (_: IdCapture, capturedId: CapturedId) => {
    const mobile = capturedId.mobileDocument;       // MobileDocumentResult | null (ISO 18013-5 mdoc)
    if (mobile) {
      console.log(mobile.fullName, mobile.dateOfBirth, mobile.documentNumber);
      // MobileDocumentResult also exposes portrait (base64 string | null), drivingLicenseCategories, issuingAuthority, etc.
    }
    const ocr = capturedId.mobileDocumentOcr;       // MobileDocumentOCRResult | null (on-screen OCR)
    if (ocr) {
      console.log(ocr.fullName, ocr.documentNumber, ocr.dateOfExpiry);
    }
  },
};
```

> The harmonized top-level fields (`capturedId.fullName`, `dateOfBirth`, `documentNumber`, …) are still populated for mobile documents, so existing field-reading code keeps working; reach into `mobileDocument` / `mobileDocumentOcr` only when you need mobile-specific data.

---

## Related rejection / verification flags (no add-on package required)

These live in the base package and don't need a separate dependency, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `RejectionReason.DocumentExpired`
- `settings.rejectIdsExpiringIn = new Duration({ days: 30 })` → `RejectionReason.DocumentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `RejectionReason.HolderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `RejectionReason.NotRealIdCompliant`
- `settings.rejectInconsistentData = true` → `RejectionReason.InconsistentData`; the detail is on `capturedId.verificationResult.dataConsistency` (see section 4)

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/react-native/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/react-native/id-capture/api.html)
