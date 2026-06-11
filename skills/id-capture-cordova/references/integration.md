# ID Capture Cordova Integration Guide

ID Capture reads identity documents — passports, driver's licenses, national ID cards, residence permits, ICAO visas — and returns structured data (name, date of birth, document number, expiry, etc.) from the document's barcode, Machine Readable Zone (MRZ), and/or Visual Inspection Zone (VIZ / printed text). It can also read mobile documents (mobile driver's licenses).

You declare **which documents to accept** and **which scanner to use**, attach a listener, and the SDK delivers a `CapturedId` per successful scan (or a `RejectionReason` when a document is seen but not accepted).

## Prerequisites

- Cordova `>=11` (or PhoneGap with an equivalent runtime).
- Scandit Cordova plugins added with `cordova plugin add`:
  ```sh
  cordova plugin add scandit-cordova-datacapture-core
  cordova plugin add scandit-cordova-datacapture-id
  # Add-on capability plugins live separately — see `references/supplementary-modules.md`.
  ```
- A valid Scandit license key, **enabled for ID Capture**:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permission configured by the app:
  - The native manifest permission is declared by the plugin.
  - iOS: `cordova plugin add scandit-cordova-datacapture-core` already wires `NSCameraUsageDescription`; if you want a custom prompt string, edit your `config.xml` (`<edit-config>` for `NSCameraUsageDescription`).
  - Android: the OS will prompt on first camera use. If you want to control the prompt timing, install `cordova-plugin-android-permissions` (or your project's existing permission plugin) and request `CAMERA` before showing the scan view.

## Step 1 — Wait for `deviceready`

The Cordova plugin loader populates `window.Scandit.*` and registers the native bridges on the `deviceready` event. Calling Scandit APIs before that yields `undefined`. Wrap every bootstrap in:

```js
document.addEventListener('deviceready', () => {
  // safe to use Scandit.* now
}, false);
```

There is **no manual `initializePlugins()` call** (that's the Capacitor pattern); Cordova fires the readiness automatically.

## Step 2 — Create the DataCaptureContext

`Scandit.DataCaptureContext.initialize(licenseKey)` returns the context. Hold a reference to it for the lifetime of the scan screen.

```js
const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
const context = Scandit.DataCaptureContext.initialize(licenseKey);
```

## Step 3 — Configure IdCaptureSettings

Two decisions: **which documents** to accept and **which scanner** to use.

```js
const settings = new Scandit.IdCaptureSettings();

// Which documents to accept. Narrow by region/country where you can — it's
// faster and more accurate than IdCaptureRegion.Any across all types.
settings.acceptedDocuments.push(
  new Scandit.IdCard(Scandit.IdCaptureRegion.Any),
  new Scandit.DriverLicense(Scandit.IdCaptureRegion.Any),
  new Scandit.Passport(Scandit.IdCaptureRegion.Any),
);

// Which scanner to use. FullDocumentScanner reads front + back automatically.
settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner());
```

### Choosing documents

Accepted-document classes each take an `IdCaptureRegion`:

`new Scandit.IdCard(region)`, `new Scandit.DriverLicense(region)`, `new Scandit.Passport(region)`, `new Scandit.ResidencePermit(region)`, `new Scandit.VisaIcao(region)`, `new Scandit.HealthInsuranceCard(region)`, and `new Scandit.RegionSpecific(subtype)` (which takes a `RegionSpecificSubtype` instead of a region).

> **Note:** There is no `VisaLetter` document class on Cordova — only `VisaIcao` ships.

`Scandit.IdCaptureRegion` is a PascalCase enum — write `Scandit.IdCaptureRegion.Any`, `Scandit.IdCaptureRegion.EuAndSchengen`, `Scandit.IdCaptureRegion.Us`, `Scandit.IdCaptureRegion.Germany`. Use `rejectedDocuments` to carve out exceptions from a broad accept list:

```js
settings.acceptedDocuments.push(new Scandit.DriverLicense(Scandit.IdCaptureRegion.Any));
settings.rejectedDocuments.push(new Scandit.DriverLicense(Scandit.IdCaptureRegion.Us)); // accept all DLs except US
```

### Choosing a scanner

Set `settings.scanner` to an `IdCaptureScanner`, which wraps a physical and/or a mobile scanner. The first positional argument is the physical scanner, the second the mobile-document scanner:

| Goal | Scanner |
|---|---|
| Read whatever side(s) the SDK needs, automatically (front + back) | `new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner())` |
| Read a single side, only the zones you enable | `new Scandit.IdCaptureScanner(new Scandit.SingleSideScanner(barcode, machineReadableZone, visualInspectionZone))` |
| Read a mobile document (mDL) | `new Scandit.IdCaptureScanner(undefined, new Scandit.MobileDocumentScanner(true, false))` |

`SingleSideScanner` takes three positional booleans — `barcode`, `machineReadableZone` (MRZ), `visualInspectionZone` (VIZ / printed text).

### Extracting images (optional)

By default images are not returned. Opt in per image type:

```js
settings.setShouldPassImageTypeToResult(Scandit.IdImageType.Face, true);
settings.setShouldPassImageTypeToResult(Scandit.IdImageType.CroppedDocument, true);
// IdImageType also has `Frame`.
```

### Anonymization (optional)

```js
settings.anonymizationMode = Scandit.IdAnonymizationMode.FieldsAndImages;
// Values: None, FieldsOnly, ImagesOnly, FieldsAndImages.
```

For per-field anonymization, use `settings.addAnonymizedField(document, Scandit.IdFieldType.<Field>)` for each field/document combination you want masked.

## Step 4 — Create IdCapture and attach a listener

`IdCapture` is constructed with `new Scandit.IdCapture(settings)`. The listener is a plain object literal with optional `didCaptureId` / `didRejectId` methods.

```js
const idCapture = new Scandit.IdCapture(settings);

const idCaptureListener = {
  didCaptureId: (_, capturedId) => {
    // Pause scanning while you present the result.
    idCapture.isEnabled = false;
    // ...show result; set idCapture.isEnabled = true when ready to resume.
  },
  didRejectId: (_, rejectedId, reason) => {
    idCapture.isEnabled = false;
    // ...map `reason` to a user-facing message.
  },
};

idCapture.addListener(idCaptureListener);
context.setMode(idCapture);
```

A document is **rejected** when it's seen but not delivered. Map the reason to a user-facing message:

```js
function messageFor(reason) {
  switch (reason) {
    case Scandit.RejectionReason.NotAcceptedDocumentType:
      return 'Document not supported. Try another document.';
    case Scandit.RejectionReason.Timeout:
      return 'Capture timed out. Ensure the document is well lit and free of glare.';
    default:
      return `Document capture was rejected. Reason: ${reason}.`;
  }
}
```

`Scandit.RejectionReason` values (PascalCase names, camelCase wire values): `NotAcceptedDocumentType`, `InvalidFormat`, `DocumentVoided`, `Timeout`, `SingleImageNotRecognized`, `DocumentExpired`, `DocumentExpiresSoon`, `NotRealIdCompliant`, `HolderUnderage`, `ForgedAamvaBarcode`, `InconsistentData`, `BluetoothCommunicationError`, `BluetoothUnavailable`.

## Step 5 — Set up the camera

`Scandit.Camera.withSettings(...)` returns `Camera | null` — guard the result before using it.

```js
const camera = Scandit.Camera.withSettings(Scandit.IdCapture.createRecommendedCameraSettings());
if (!camera) {
  throw new Error('No camera available on this device');
}
context.setFrameSource(camera);
camera.switchToDesiredState(Scandit.FrameSourceState.On);
idCapture.isEnabled = true;
```

## Step 6 — Render the view and attach the overlay

`Scandit.DataCaptureView` is an **imperative class** — not a custom element, not a component. Create it and attach it to a plain `<div>` in your DOM via `view.connectToElement(...)`.

```html
<!-- www/index.html -->
<div id="data-capture-view" style="width: 100vw; height: 100vh; z-index: -1"></div>
```

```js
const view = Scandit.DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));

const overlay = new Scandit.IdCaptureOverlay(idCapture);
overlay.idLayoutStyle = Scandit.IdLayoutStyle.Rounded;
view.addOverlay(overlay);
```

> **Use the plain constructors.** `new Scandit.IdCapture(settings)` and `new Scandit.IdCaptureOverlay(idCapture)` are the only forms on Cordova. Do not write `Scandit.IdCapture.forContext(...)`, `Scandit.IdCaptureOverlay.withIdCapture(...)`, or any custom-element / framework-component wrapper for the view — those are other modes' or other platforms' APIs and do not exist here.

When navigating away from the scan view, call `view.detachFromElement()` so the native overlay is cleaned up.

## Step 7 — Camera permission (optional explicit request)

The native plugin requests the camera permission lazily on first use. If you want to control the prompt timing, install `cordova-plugin-android-permissions` (Android-only) and request `CAMERA` before mounting the scan view:

```sh
cordova plugin add cordova-plugin-android-permissions
```

```js
const permissions = cordova.plugins.permissions;
permissions.checkPermission(permissions.CAMERA, (status) => {
  if (status.hasPermission) return;
  permissions.requestPermission(permissions.CAMERA, (s) => {
    if (!s.hasPermission) throw new Error('Camera permission denied');
  });
});
```

iOS handles the prompt automatically using the `NSCameraUsageDescription` configured by the core plugin.

## Step 8 — Handle the app lifecycle

Cordova fires document-level `pause` and `resume` events when the OS sends the app to background / foreground. Stop the camera and disable the mode on `pause`, reverse on `resume`:

```js
document.addEventListener('pause', () => {
  idCapture.isEnabled = false;
  camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', () => {
  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  idCapture.isEnabled = true;
}, false);
```

If you have a multi-page Cordova app and the scan view shares a process with other pages, also call `view.detachFromElement()` + `context.removeMode(idCapture)` when leaving the scan view's route (not when the OS pauses — the native context can survive a pause / resume cycle as-is).

## Step 9 — Reading the CapturedId

`CapturedId` exposes harmonized fields regardless of which zone produced them. Note: on Cordova the source-specific results are named `mrzResult` / `vizResult` (with `Result` suffix), not `mrz` / `viz`.

- Identity: `firstName`, `lastName`, `fullName`, `sex`, `dateOfBirth`, `nationality`, `nationalityISO`, `address`, `age`.
- Document: `documentNumber`, `documentAdditionalNumber`, `dateOfExpiry`, `dateOfIssue`, `isExpired`, `issuingCountry` / `issuingCountryIso`. The document **type** is on `capturedId.document` (an `IdCaptureDocument | null`): use `capturedId.document?.documentType` (an `IdCaptureDocumentType`) or the convenience methods `isIdCard()`, `isDriverLicense()`, `isPassport()`, `isResidencePermit()`, `isHealthInsuranceCard()`, `isVisaIcao()`, `isRegionSpecific(subtype)`. There is **no** `capturedId.documentType` getter, **no** `isVisa()`, **no** `isVisaLetter()`.
- Source-specific results (nullable): `mrzResult`, `vizResult`, `barcode`, `mobileDocument`, `mobileDocumentOcr`.
- `images` (`IdImages`) — read images with `images.face`, `images.frame`, `images.getCroppedDocument(Scandit.IdSide.Front)`, `images.getFrame(Scandit.IdSide.Front)`. **Each returns a base64 `string | null`**, e.g. `<img src="data:image/png;base64,${face}">` or `imgEl.src = 'data:image/png;base64,' + face`. There is no `images.croppedDocument` getter — use `getCroppedDocument(Scandit.IdSide.Front)` / `IdSide.Back`. Images are only populated for the `IdImageType`s you opted into via `setShouldPassImageTypeToResult(...)`.
- `verificationResult` (`VerificationResult`) — contains `dataConsistency` and `aamvaBarcodeVerification` (see `references/supplementary-modules.md`).

Date fields are `DateResult | null` with `{ year, month, day }`. Format e.g. with `new Date(Date.UTC(d.year, d.month - 1, d.day)).toLocaleDateString('en-GB', { timeZone: 'UTC' })`. Branch on the source when you need zone-specific data:

```js
if (capturedId.mrzResult) {
  // passport / MRZ specifics
} else if (capturedId.vizResult) {
  // printed-zone specifics (driving-license categories, etc.)
} else if (capturedId.barcode) {
  // barcode specifics (e.g. US DL PDF417)
}
```

## Co-existence with Barcode Capture

`IdCapture` and `BarcodeCapture` can run **together on one `DataCaptureContext`** — one context, one `DataCaptureView`, one camera. A common case is an airport screen that reads a boarding-pass PDF417 barcode **and** a passport/ID at the same time.

Attach **both** modes with `context.addMode(idCapture)` **and** `context.addMode(barcodeCapture)`. Do **not** use `context.setMode(...)` here — `setMode` **replaces** the context's current mode, so calling it twice would leave only the last mode. `setMode` is fine for a single-mode screen; for co-existence use `addMode` for each. Give each mode its own listener and toggle each independently with `mode.isEnabled` — both can be enabled at once and the native layer runs them together.

```js
// ID Capture mode (passport / ID)
const idSettings = new Scandit.IdCaptureSettings();
idSettings.acceptedDocuments.push(new Scandit.Passport(Scandit.IdCaptureRegion.Any));
idSettings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner());
const idCapture = new Scandit.IdCapture(idSettings);
idCapture.addListener({ didCaptureId: (_, capturedId) => { /* ... */ } });
context.addMode(idCapture);

// Barcode Capture mode (IATA boarding pass = PDF417), same context
const bcSettings = new Scandit.BarcodeCaptureSettings();
bcSettings.enableSymbologies([Scandit.Symbology.PDF417]);
const barcodeCapture = new Scandit.BarcodeCapture(bcSettings);
barcodeCapture.addListener({
  didScan: (_, session) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode) { /* ... */ }
  },
});
context.addMode(barcodeCapture);

// Both can be enabled at once — they run together.
idCapture.isEnabled = true;
barcodeCapture.isEnabled = true;
```

## Common pitfalls

- **Touching `Scandit.*` before `deviceready`** — the global is empty / partially populated. Always run bootstrap inside the `deviceready` handler.
- **Importing from `scandit-cordova-datacapture-id`** in your application code — the package only exposes its symbols via Cordova's plugin loader onto `window.Scandit`. Use `Scandit.IdCapture`, not `import { IdCapture } …`.
- **Calling `Scandit.DataCaptureContext.sharedInstance`** — that's the RN pattern. On Cordova, capture the return value of `Scandit.DataCaptureContext.initialize(licenseKey)`.
- **Using the removed `supportedDocuments` / `IdDocumentType` bitmask API** — see `references/migration.md`.
- **Using `Scandit.AamvaBarcodeVerifier`** — removed at v7 → v8. Use `settings.rejectForgedAamvaBarcodes` + `capturedId.verificationResult.aamvaBarcodeVerification`.
- **Calling methods on `Scandit.Camera.withSettings(...)` without a null guard** — it's typed `Camera | null`; always check.
- **Using `Scandit.Camera.default`** — that's RN / Flutter. On Cordova: `Scandit.Camera.withSettings(Scandit.IdCapture.createRecommendedCameraSettings())`.
- **Reaching for `<data-capture-view>`, a Scandit-supplied component, or a React-style wrapper** — neither exists on Cordova. Use `Scandit.DataCaptureView.forContext(context).connectToElement(divEl)`.
- **Using Flutter-style lowercase enum values** (`IdCaptureRegion.us`, `IdSide.front`). On Cordova it's `Scandit.IdCaptureRegion.Us`, `Scandit.IdSide.Front`.
- **Reading `capturedId.mrz` or `capturedId.viz`** — Flutter names. On Cordova it's `mrzResult` and `vizResult`.
- **Treating `images.face` like a URI or file** — it's a base64 string. Use the `data:` URI form when rendering.
- **Not detaching the view / removing the mode** when navigating away → memory / overlay leak. Call `view.detachFromElement()` and `context.removeMode(idCapture)` on route teardown.

## Reference links

- [Get Started](https://docs.scandit.com/sdks/cordova/id-capture/get-started/)
- [Advanced Configurations](https://docs.scandit.com/sdks/cordova/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/cordova/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
