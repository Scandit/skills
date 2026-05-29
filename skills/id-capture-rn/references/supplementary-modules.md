# ID Capture Add-On Capabilities (React Native)

Three ID Capture capabilities ship as **separate React Native packages** because they bundle additional native models. The pattern is the same for all three:

1. **Add the package** to `package.json` (this is what unlocks the native models — and on iOS, the corresponding pod).
2. **Set one flag** on `IdCaptureSettings` (the API lives in the base `scandit-react-native-datacapture-id` package — these add-on packages expose **no JavaScript API of their own**, only a native module bridge).
3. **Read the result** off the `CapturedId`, or handle the corresponding `RejectionReason`.

> There is **no standalone verifier or scanner class** for these on React Native (no `AamvaBarcodeVerifier`, no voided-detection object). Everything is driven by the settings flags below. Don't import classes from the add-on packages — they only register a `NativeModule`.

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

## Related rejection / verification flags (no add-on package required)

These live in the base package and don't need a separate dependency, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `RejectionReason.DocumentExpired`
- `settings.rejectIdsExpiringIn = new Duration({ days: 30 })` → `RejectionReason.DocumentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `RejectionReason.HolderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `RejectionReason.NotRealIdCompliant`
- `settings.rejectInconsistentData = true` → `RejectionReason.InconsistentData`; the detail is on `capturedId.verificationResult.dataConsistency`

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/react-native/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/react-native/id-capture/api.html)
