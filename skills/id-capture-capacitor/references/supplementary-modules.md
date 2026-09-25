# ID Capture Add-On Capabilities (Capacitor)

Three ID Capture capabilities ship as **separate Capacitor packages** because they bundle additional native models. The pattern is the same for all three:

1. **Add the package** to `package.json` and run `npx cap sync` (this is what registers the native bridge — and on iOS, the corresponding pod).
2. **Set one flag** on `IdCaptureSettings` (the API lives in the base `scandit-capacitor-datacapture-id` package — these add-on packages expose **no JavaScript API of their own**, only a native plugin).
3. **Read the result** off the `CapturedId`, or handle the corresponding `RejectionReason`.

> There is **no standalone verifier or scanner class** for these on Capacitor (no `AamvaBarcodeVerifier`, no voided-detection object). Everything is driven by the settings flags below. Don't import classes from the add-on packages — they only register a native plugin.

You still initialize ID Capture exactly as in `references/integration.md`; these flags layer on top of an existing `IdCaptureSettings`. After adding any of these packages, run `npx cap sync` (and `pod install` from `ios/App/`).

---

## 1. Voided-ID detection

Rejects voided / cancelled documents (punched-hole or marked-void IDs). Primarily tuned for **US driver's licenses** — results may be less accurate on other document types.

**Package** (`package.json`):

```json
{
  "dependencies": {
    "scandit-capacitor-datacapture-id-voided-detection": "<sdk-version>"
  }
}
```

**Enable** (Capacitor `6.25+`):

```ts
settings.rejectVoidedIds = true;
```

**Handle the rejection** — voided documents arrive in `didRejectId` with `RejectionReason.DocumentVoided`:

```ts
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
    "scandit-capacitor-datacapture-id-europe-driving-license": "<sdk-version>"
  }
}
```

**Enable** (Capacitor `7.0+`) — also use a scanner that reads the back (`FullDocumentScanner`, or a `SingleSideScanner` with VIZ enabled):

```ts
settings.decodeBackOfEuropeanDrivingLicense = true;
settings.scanner = new IdCaptureScanner(new FullDocumentScanner());
```

**Read the result** — the decoded categories appear on the VIZ result as `DrivingLicenseDetails` (Capacitor `8.0+`):

```ts
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
    "scandit-capacitor-datacapture-id-aamva-barcode-verification": "<sdk-version>"
  }
}
```

**Enable** (Capacitor `7.3+`) — there is no separate verifier object on Capacitor any more; it's a settings flag:

```ts
settings.rejectForgedAamvaBarcodes = true;
```

**Two ways to consume the result:**

- **Rejection path** — when `rejectForgedAamvaBarcodes` is `true`, a forged barcode is rejected with `RejectionReason.ForgedAamvaBarcode`:

  ```ts
  if (reason === RejectionReason.ForgedAamvaBarcode) {
    // Document barcode failed verification.
  }
  ```

- **Inspect the verification result** on a captured document via `verificationResult.aamvaBarcodeVerification`:

  ```ts
  import { AamvaBarcodeVerificationStatus } from 'scandit-capacitor-datacapture-id';

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

## 4. Mobile documents (mDL / ISO 18013-5)

Reads **mobile driver's licenses** (mDL) — both the offline ISO 18013-5 mdoc exchange and the OCR of the on-screen rendering. This is GA, but thin in the guide docs. No add-on package is required — `MobileDocumentScanner` lives in the base `scandit-capacitor-datacapture-id` package.

Mobile documents are read by a `MobileDocumentScanner`, passed as the **second** positional argument to `IdCaptureScanner` (the first is the physical-document scanner; pass `undefined` for mDL-only):

```ts
import { IdCaptureScanner, MobileDocumentScanner } from 'scandit-capacitor-datacapture-id';

// Mobile documents only:
settings.scanner = new IdCaptureScanner(undefined, new MobileDocumentScanner(true, false));

// Physical + mobile documents in the same session:
settings.scanner = new IdCaptureScanner(new FullDocumentScanner(), new MobileDocumentScanner(true, false));
```

`MobileDocumentScanner(true, false)` enables the ISO 18013-5 mdoc path and disables OCR; `MobileDocumentScanner(false, true)` reads only the OCR of the on-screen document.

**Read the result** — mobile-document data arrives in source-specific getters on `CapturedId`:

```ts
const listener = {
  didCaptureId: (_: IdCapture, capturedId: CapturedId) => {
    const mobile = capturedId.mobileDocument;     // MobileDocumentResult | null (ISO 18013-5 mdoc)
    if (mobile) {
      console.log(mobile.fullName, mobile.dateOfBirth, mobile.documentNumber);
    }
    const ocr = capturedId.mobileDocumentOcr;      // MobileDocumentOCRResult | null (on-screen OCR)
    if (ocr) {
      console.log(ocr.fullName, ocr.documentNumber);
    }
  },
};
```

> The harmonized top-level fields (`capturedId.fullName`, `dateOfBirth`, …) are still populated for mobile documents; reach into `mobileDocument` / `mobileDocumentOcr` only for mobile-specific data. Document type is read via `capturedId.document?.documentType` — there is no `IdDocumentType` bitmask, and no `AamvaBarcodeVerifier` is involved.

---

## Related rejection / verification flags (no add-on package required)

These live in the base package and don't need a separate dependency, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `RejectionReason.DocumentExpired`
- `settings.rejectIdsExpiringIn = new Duration({ days: 30 })` → `RejectionReason.DocumentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `RejectionReason.HolderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `RejectionReason.NotRealIdCompliant`
- `settings.rejectInconsistentData = true` → `RejectionReason.InconsistentData`; the detail is on `capturedId.verificationResult.dataConsistency`

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/capacitor/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/id-capture/api.html)
