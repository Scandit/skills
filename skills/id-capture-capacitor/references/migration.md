# ID Capture Capacitor Migration Guide

This guide covers upgrading an existing ID Capture integration across major SDK versions. The biggest breaking changes for Capacitor landed at **v7 → v8**: the scanner property was renamed and reshaped, and the standalone `AamvaBarcodeVerifier` was removed. (The earlier `supportedDocuments` / `IdDocumentType` bitmask → `acceptedDocuments` change happened at v6 → v7 and is summarized at the end.)

Do not guess at the old or new signatures — follow the concrete before/after below, and verify anything else against the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/id-capture/api.html).

## Step 1 — Detect the installed version and current API

Check `package.json` for the `scandit-capacitor-datacapture-*` versions, and look at the code:

- Uses `settings.scannerType = ...` and/or `AamvaBarcodeVerifier` → **pre-v8 (v7) code**; migrate per Steps 2–3.
- Uses `settings.supportedDocuments` / `IdDocumentType` → **pre-v7 (v6) code**; see Step 7 first, then continue.
- Already uses `settings.scanner = new IdCaptureScanner(new FullDocumentScanner())` → on v8; only Steps 4–6 (optional adoption) apply.

## Step 2 — Migrate the scanner property (`scannerType` → `scanner`)

In v7, `SingleSideScanner` / `FullDocumentScanner` were assigned directly to `scannerType`. In v8 they are physical scanners wrapped in an `IdCaptureScanner`, assigned to `scanner`.

```ts
// BEFORE (v7)
const settings = new IdCaptureSettings();
settings.scannerType = new FullDocumentScanner();
// or: settings.scannerType = new SingleSideScanner(true, false, false);

// AFTER (v8)
const settings = new IdCaptureSettings();
settings.scanner = new IdCaptureScanner(new FullDocumentScanner());
// or: settings.scanner = new IdCaptureScanner(new SingleSideScanner(true, false, false));
```

`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` keeps the same three positional booleans — only the wrapping and the property name changed. To scan mobile documents, pass a `MobileDocumentScanner` as the second positional argument: `new IdCaptureScanner(undefined, new MobileDocumentScanner(true, false))`.

> The default `new IdCaptureSettings()` constructor in v8 produces a scanner that scans **nothing** and an empty `acceptedDocuments`. After upgrading, make sure you explicitly set both `scanner` and `acceptedDocuments` — relying on constructor defaults will silently capture nothing.

## Step 3 — Replace `AamvaBarcodeVerifier` with the settings flag

The standalone verifier class was removed on Capacitor at v8. AAMVA verification is now a settings flag, and the result is delivered on the `CapturedId`.

```ts
// BEFORE (v7) — standalone verifier
const verifier = await AamvaBarcodeVerifier.create(context);
// ...later, inside didCaptureId:
const result: AamvaBarcodeVerificationResult = await verifier.verify(capturedId);

// AFTER (v8) — settings flag + result on CapturedId
settings.rejectForgedAamvaBarcodes = true; // forged barcodes -> didRejectId(reason: ForgedAamvaBarcode)
// ...inside didCaptureId, inspect the verification result:
const aamva = capturedId.verificationResult.aamvaBarcodeVerification;
const status = aamva?.status; // AamvaBarcodeVerificationStatus.Authentic / LikelyForged / Forged
```

Add the AAMVA add-on package to `package.json` (it ships the native models):

```json
{
  "dependencies": {
    "scandit-capacitor-datacapture-id-aamva-barcode-verification": "<sdk-version>"
  }
}
```

Then `npm install`, `npx cap sync`, and `pod install` from `ios/App/`. Remove any `import { AamvaBarcodeVerifier } from 'scandit-capacitor-datacapture-id'` — that symbol no longer exists. See `references/supplementary-modules.md` for the full result shape.

## Step 4 — Adopt the new rejection flags (optional)

v8 adds declarative rejection. Prefer these over manual post-capture checks; each surfaces a specific `RejectionReason` in `didRejectId`:

```ts
settings.rejectExpiredIds = true;                          // -> DocumentExpired
settings.rejectIdsExpiringIn = new Duration({ days: 30 }); // -> DocumentExpiresSoon
settings.rejectHolderBelowAge = 18;                        // -> HolderUnderage
settings.rejectNotRealIdCompliant = true;                  // -> NotRealIdCompliant
settings.rejectInconsistentData = true;                    // -> InconsistentData
settings.rejectVoidedIds = true;                           // -> DocumentVoided (needs voided-detection add-on)
```

## Step 5 — Adopt verification & richer results (optional)

- `capturedId.verificationResult` now carries `dataConsistency` (`DataConsistencyResult | null`, enable via `rejectInconsistentData`) and `aamvaBarcodeVerification`.
- `capturedId.vizResult?.drivingLicenseDetails` exposes `drivingLicenseCategories`, `restrictions`, `endorsements` when `decodeBackOfEuropeanDrivingLicense` is enabled (needs the europe-driving-license add-on). See `references/supplementary-modules.md`.
- Mobile documents: read `capturedId.mobileDocument` / `capturedId.mobileDocumentOcr` when using a `MobileDocumentScanner`.

## Step 6 — Verify the listener and lifecycle still match

The listener contract is unchanged across v7 → v8: a plain object literal with optional `didCaptureId(idCapture, capturedId)` and `didRejectId(idCapture, rejectedId, reason)` methods. The `DataCaptureView.forContext(context)` + `view.connectToElement(div)` pattern, `await context.setMode(idCapture)`, and `ScanditCaptureCorePlugin.initializePlugins()` at startup are also unchanged. No migration needed there.

If your existing code didn't `await` the Promise-returning APIs (`addListener`, `setMode`, `applySettings`, `setFrameSource`, `switchToDesiredState`), this is a good moment to add `await` — they have always returned Promises, but the v8 runtime is stricter about ordering.

## Step 7 — If you are coming from v6 (`supportedDocuments`)

In v6, documents were selected with a `supportedDocuments` bitmask of `IdDocumentType` and the scanner was implied by `supportedSides`. That API was removed at v7. Move to the list-based model:

```ts
// v6 (removed): settings.supportedDocuments = IdDocumentType.IdCardViz | IdDocumentType.PassportMrz;
// v7+: declare documents and a scanner explicitly
settings.acceptedDocuments.push(
  new IdCard(IdCaptureRegion.Any),
  new Passport(IdCaptureRegion.Any),
);
settings.scanner = new IdCaptureScanner(new FullDocumentScanner()); // v8 form
```

v6 also used different listener and result APIs that were reshaped on the way to v8:

- **Listener callbacks renamed.** v6's `onIdCaptured(idCapture, capturedId)` and the dedicated `onIdCapturedTimedOut(idCapture, capturedId)` became `didCaptureId(idCapture, capturedId)` and `didRejectId(idCapture, rejectedId, reason)`. There is no separate timeout callback any more — a timeout now arrives in `didRejectId` with `RejectionReason.Timeout`.

  ```ts
  // BEFORE (v6)
  idCapture.addListener({
    onIdCaptured: (_, capturedId) => { /* ... */ },
    onIdCapturedTimedOut: (_, capturedId) => { /* timed out */ },
  });

  // AFTER (v8)
  idCapture.addListener({
    didCaptureId: (_, capturedId) => { /* ... */ },
    didRejectId: (_, rejectedId, reason) => {
      if (reason === RejectionReason.Timeout) { /* timed out */ }
    },
  });
  ```

- **Document type moved off `CapturedId`.** v6's `capturedId.documentType` was removed. Read the type via `capturedId.document?.documentType` (an `IdCaptureDocumentType`) or the `capturedId.isPassport()` / `isDriverLicense()` / `isIdCard()` convenience methods.

  ```ts
  // BEFORE (v6): const type = capturedId.documentType;
  // AFTER (v8):
  const type = capturedId.document?.documentType;
  ```

For the full v6 → v7 details, see the [6 → 7 migration guide](https://docs.scandit.com/sdks/capacitor/migrate-6-to-7/) and the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/id-capture/api.html).

## Step 8 — Verify

- The project compiles with no references to `scannerType`, `AamvaBarcodeVerifier`, `supportedDocuments`, or `IdDocumentType`.
- `acceptedDocuments` and `scanner` are both set explicitly.
- A test scan delivers a `CapturedId` in `didCaptureId`, and an out-of-scope document triggers `didRejectId`.
- Run `tsc --noEmit` against the project to surface any other v7 API names you might have missed.

## Reference links

- [7 → 8 migration guide](https://docs.scandit.com/sdks/capacitor/migrate-7-to-8/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
