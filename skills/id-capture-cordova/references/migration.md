# ID Capture Cordova Migration Guide

This guide covers upgrading an existing ID Capture integration across major SDK versions. The biggest breaking change for Cordova landed at **v7 → v8**: the standalone `AamvaBarcodeVerifier` was removed in favour of a settings flag, and several verification APIs were added. (The earlier `supportedDocuments` / `IdDocumentType` bitmask → `acceptedDocuments` change happened at v6 → v7 and is summarized at the end.)

Do not guess at the old or new signatures — follow the concrete before/after below, and verify anything else against the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/cordova/id-capture/api.html).

## Step 1 — Detect the installed version and current API

Check `config.xml` (or the installed plugin versions via `cordova plugin list`) for the `scandit-cordova-datacapture-*` versions, and look at the code:

- Uses `Scandit.AamvaBarcodeVerifier` → **pre-v8 (v7) code**; migrate per Step 2.
- Uses `settings.supportedDocuments` / `Scandit.IdDocumentType` → **pre-v7 (v6) code**; see Step 6 first, then continue.
- Already uses `settings.scanner = new Scandit.IdCaptureScanner(...)` and no `AamvaBarcodeVerifier` references → on v8; only Steps 3–5 (optional adoption) apply.

## Step 2 — Replace `AamvaBarcodeVerifier` with the settings flag

The standalone verifier was exported on Cordova at v7. It was removed at v8 — AAMVA verification is now a settings flag, and the result is delivered on the `CapturedId`.

```js
// BEFORE (v7) — standalone verifier
const verifier = await Scandit.AamvaBarcodeVerifier.create(context);
// ...later, inside didCaptureId:
const result = await verifier.verify(capturedId);
console.log(result.allChecksPassed, result.status);

// AFTER (v8) — settings flag + result on CapturedId
settings.rejectForgedAamvaBarcodes = true; // forged barcodes -> didRejectId(reason: ForgedAamvaBarcode)
// ...inside didCaptureId, inspect the verification result:
const aamva = capturedId.verificationResult.aamvaBarcodeVerification;
const status = aamva && aamva.status; // AamvaBarcodeVerificationStatus.Authentic / LikelyForged / Forged
```

Install the AAMVA add-on plugin (it ships the native models):

```sh
cordova plugin add scandit-cordova-datacapture-id-aamva-barcode-verification
cordova prepare
```

Remove any reference to `Scandit.AamvaBarcodeVerifier` — that symbol no longer exists. See `references/supplementary-modules.md` for the full result shape.

## Step 3 — Confirm the scanner property name

`Scandit.IdCaptureSettings` on Cordova uses the **v8 form** (`settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner())`) and has done so as far back as the public Cordova ID plugin shipped. If an integration was authored against another platform's pre-v8 API or against older internal Cordova builds and uses `settings.scannerType = …`, change it to `settings.scanner` and wrap the scanner in `IdCaptureScanner`:

```js
// If you have this anywhere (other-platform v7 form):
// settings.scannerType = new Scandit.FullDocumentScanner();

// Use this on Cordova v8:
settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner());
```

`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` keeps the same three positional booleans. For mobile documents pass a `MobileDocumentScanner` as the second positional argument: `new Scandit.IdCaptureScanner(undefined, new Scandit.MobileDocumentScanner(true, false))`.

> The default `new Scandit.IdCaptureSettings()` constructor on v8 produces a scanner that scans **nothing** and an empty `acceptedDocuments`. After upgrading, make sure you explicitly set both `scanner` and `acceptedDocuments` — relying on constructor defaults will silently capture nothing.

## Step 4 — Adopt the new rejection flags (optional)

v8 adds declarative rejection. Prefer these over manual post-capture checks; each surfaces a specific `RejectionReason` in `didRejectId`:

```js
settings.rejectExpiredIds = true;                                  // -> DocumentExpired
settings.rejectIdsExpiringIn = new Scandit.Duration({ days: 30 }); // -> DocumentExpiresSoon
settings.rejectHolderBelowAge = 18;                                // -> HolderUnderage
settings.rejectNotRealIdCompliant = true;                          // -> NotRealIdCompliant
settings.rejectInconsistentData = true;                            // -> InconsistentData
settings.rejectVoidedIds = true;                                   // -> DocumentVoided (needs voided-detection add-on)
```

## Step 5 — Adopt verification & richer results (optional)

- `capturedId.verificationResult` now carries `dataConsistency` (`DataConsistencyResult | null`, enable via `rejectInconsistentData`) and `aamvaBarcodeVerification`.
- `capturedId.vizResult?.drivingLicenseDetails` exposes `drivingLicenseCategories`, `restrictions`, `endorsements` when `decodeBackOfEuropeanDrivingLicense` is enabled (needs the europe-driving-license add-on). See `references/supplementary-modules.md`.
- Mobile documents: read `capturedId.mobileDocument` / `capturedId.mobileDocumentOcr` when using a `MobileDocumentScanner`.

## Step 6 — If you are coming from v6 (`supportedDocuments`)

In v6, documents were selected with a `supportedDocuments` bitmask of `IdDocumentType` and the scanner was implied by `supportedSides`. That API was removed at v7. Move to the list-based model:

```js
// v6 (removed): settings.supportedDocuments = Scandit.IdDocumentType.IdCardViz | Scandit.IdDocumentType.PassportMrz;
// v7+: declare documents and a scanner explicitly
settings.acceptedDocuments.push(
  new Scandit.IdCard(Scandit.IdCaptureRegion.Any),
  new Scandit.Passport(Scandit.IdCaptureRegion.Any),
);
settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner()); // v8 form
```

For the full v6 → v7 details, see the [6 → 7 migration guide](https://docs.scandit.com/sdks/cordova/migrate-6-to-7/) and the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/cordova/id-capture/api.html).

## Step 7 — Verify

- The project has no references to `Scandit.AamvaBarcodeVerifier`, `supportedDocuments`, `IdDocumentType`, or `settings.scannerType`.
- `acceptedDocuments` and `scanner` are both set explicitly.
- The bootstrap is still wrapped in `document.addEventListener('deviceready', …)`.
- A test scan delivers a `CapturedId` in `didCaptureId`, and an out-of-scope document triggers `didRejectId`.

## Reference links

- [7 → 8 migration guide](https://docs.scandit.com/sdks/cordova/migrate-7-to-8/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/cordova/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
