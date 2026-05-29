# ID Capture Add-On Capabilities (Cordova)

Three ID Capture capabilities ship as **separate Cordova plugins** because they bundle additional native models. The pattern is the same for all three:

1. **Install the plugin** with `cordova plugin add` (this is what registers the native bridge — and on iOS, the corresponding pod).
2. **Set one flag** on `Scandit.IdCaptureSettings` (the API lives in the base `scandit-cordova-datacapture-id` plugin — these add-on plugins expose **no JavaScript API of their own**, only a native bridge).
3. **Read the result** off the `CapturedId`, or handle the corresponding `RejectionReason`.

> There is **no standalone verifier or scanner class** for these on Cordova (no `Scandit.AamvaBarcodeVerifier`, no voided-detection object). Everything is driven by the settings flags below. The add-on plugins only register native code — there is no `Scandit.*` symbol added by them. After installing any of these plugins, run `cordova prepare` (and `pod install` on iOS if not run by the prepare).

You still initialize ID Capture exactly as in `references/integration.md`; these flags layer on top of an existing `Scandit.IdCaptureSettings`.

---

## 1. Voided-ID detection

Rejects voided / cancelled documents (punched-hole or marked-void IDs). Primarily tuned for **US driver's licenses** — results may be less accurate on other document types.

**Plugin:**

```sh
cordova plugin add scandit-cordova-datacapture-id-voided-detection
```

**Enable** (Cordova `6.25+`):

```js
settings.rejectVoidedIds = true;
```

**Handle the rejection** — voided documents arrive in `didRejectId` with `Scandit.RejectionReason.DocumentVoided`:

```js
const listener = {
  didRejectId: (_, rejectedId, reason) => {
    if (reason === Scandit.RejectionReason.DocumentVoided) {
      // Tell the user the document appears voided/cancelled.
    }
  },
};
```

---

## 2. European driving-license back decoding

Decodes the **back of European driving licenses** to extract vehicle-category data (categories, restrictions, endorsements, per-category issue/expiry dates).

**Plugin:**

```sh
cordova plugin add scandit-cordova-datacapture-id-europe-driving-license
```

**Enable** (Cordova `7.0+`) — also use a scanner that reads the back (`FullDocumentScanner`, or a `SingleSideScanner` with VIZ enabled):

```js
settings.decodeBackOfEuropeanDrivingLicense = true;
settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner());
```

**Read the result** — the decoded categories appear on the VIZ result as `DrivingLicenseDetails` (Cordova `8.0+`):

```js
const listener = {
  didCaptureId: (_, capturedId) => {
    const details = capturedId.vizResult && capturedId.vizResult.drivingLicenseDetails;
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

**Plugin:**

```sh
cordova plugin add scandit-cordova-datacapture-id-aamva-barcode-verification
```

**Enable** (Cordova `7.3+`) — there is no separate verifier object on Cordova any more; it's a settings flag:

```js
settings.rejectForgedAamvaBarcodes = true;
```

**Two ways to consume the result:**

- **Rejection path** — when `rejectForgedAamvaBarcodes` is `true`, a forged barcode is rejected with `Scandit.RejectionReason.ForgedAamvaBarcode`:

  ```js
  if (reason === Scandit.RejectionReason.ForgedAamvaBarcode) {
    // Document barcode failed verification.
  }
  ```

- **Inspect the verification result** on a captured document via `verificationResult.aamvaBarcodeVerification`:

  ```js
  const aamva = capturedId.verificationResult.aamvaBarcodeVerification;
  if (aamva) {
    const passed = aamva.allChecksPassed; // boolean
    switch (aamva.status) {
      case Scandit.AamvaBarcodeVerificationStatus.Authentic: break;
      case Scandit.AamvaBarcodeVerificationStatus.LikelyForged: break;
      case Scandit.AamvaBarcodeVerificationStatus.Forged: break;
    }
  }
  ```

---

## Related rejection / verification flags (no add-on plugin required)

These live in the base plugin and don't need a separate install, but they share the rejection model above:

- `settings.rejectExpiredIds = true` → `Scandit.RejectionReason.DocumentExpired`
- `settings.rejectIdsExpiringIn = new Scandit.Duration({ days: 30 })` → `Scandit.RejectionReason.DocumentExpiresSoon`
- `settings.rejectHolderBelowAge = 18` → `Scandit.RejectionReason.HolderUnderage`
- `settings.rejectNotRealIdCompliant = true` → `Scandit.RejectionReason.NotRealIdCompliant`
- `settings.rejectInconsistentData = true` → `Scandit.RejectionReason.InconsistentData`; the detail is on `capturedId.verificationResult.dataConsistency`

## Reference links

- [Advanced Configurations](https://docs.scandit.com/sdks/cordova/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/cordova/id-capture/api.html)
