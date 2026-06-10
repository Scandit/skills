# ID Capture Capacitor Integration Guide

ID Capture reads identity documents — passports, driver's licenses, national ID cards, residence permits, ICAO visas — and returns structured data (name, date of birth, document number, expiry, etc.) from the document's barcode, Machine Readable Zone (MRZ), and/or Visual Inspection Zone (VIZ / printed text). It can also read mobile documents (mobile driver's licenses).

You declare **which documents to accept** and **which scanner to use**, attach a listener, and the SDK delivers a `CapturedId` per successful scan (or a `RejectionReason` when a document is seen but not accepted).

> **One mode at a time.** ID Capture cannot run simultaneously with another capture mode (e.g. Barcode Capture) on the same `DataCaptureContext`. Only one capture mode should be active at a time — remove or deactivate the other mode (`await context.removeMode(otherMode)`) before activating `IdCapture`.

## Prerequisites

- Scandit Capacitor packages in `package.json`:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-id`
  - (Add-on capabilities live in separate packages — see `references/supplementary-modules.md`.)
- A valid Scandit license key, **enabled for ID Capture**:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permissions configured by the app:
  - Install `@capacitor/camera` and run `npx cap sync`.
  - iOS: add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request it at runtime with the `@capacitor/camera` plugin's `requestPermissions()` before mounting the scan view.

## Step 1 — Initialize the Scandit plugins

Capacitor does **not** auto-initialize the Scandit plugins. At app startup (e.g. inside a `DOMContentLoaded` handler or your framework's bootstrap), call `await ScanditCaptureCorePlugin.initializePlugins()` first. This wires up the native bridge for the core plugin and every Scandit add-on plugin in the app.

```ts
import { ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';

async function bootstrap() {
  await ScanditCaptureCorePlugin.initializePlugins();
  // Now safe to use any other Scandit API.
}
document.addEventListener('DOMContentLoaded', bootstrap);
```

Skipping `initializePlugins()` results in opaque "plugin not implemented" errors from the Capacitor bridge.

## Step 2 — Create the DataCaptureContext with your license key

`DataCaptureContext.initialize(licenseKey)` returns the context — capture and keep a reference to it.

```ts
import { DataCaptureContext } from 'scandit-capacitor-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
const context = DataCaptureContext.initialize(licenseKey);
```

## Step 3 — Configure IdCaptureSettings

Two decisions: **which documents** to accept and **which scanner** to use.

```ts
import {
  IdCaptureSettings,
  IdCaptureScanner,
  FullDocumentScanner,
  IdCard,
  DriverLicense,
  Passport,
  IdCaptureRegion,
} from 'scandit-capacitor-datacapture-id';

const settings = new IdCaptureSettings();

// Which documents to accept. Narrow by region/country where you can — it's
// faster and more accurate than IdCaptureRegion.Any across all types.
settings.acceptedDocuments.push(
  new IdCard(IdCaptureRegion.Any),
  new DriverLicense(IdCaptureRegion.Any),
  new Passport(IdCaptureRegion.Any),
);

// Which scanner to use. FullDocumentScanner reads front + back automatically.
settings.scanner = new IdCaptureScanner(new FullDocumentScanner());
```

### Choosing documents

Accepted-document classes each take an `IdCaptureRegion`:

`new IdCard(region)`, `new DriverLicense(region)`, `new Passport(region)`, `new ResidencePermit(region)`, `new VisaIcao(region)`, `new HealthInsuranceCard(region)`, and `new RegionSpecific(subtype)` (which takes a `RegionSpecificSubtype` instead of a region).

> **Note:** There is no `VisaLetter` document class on Capacitor — only `VisaIcao` ships. If you need visa-letter scanning, that's not available on this platform.

`IdCaptureRegion` is a PascalCase TS enum with camelCase wire values — write `IdCaptureRegion.Any`, `IdCaptureRegion.EuAndSchengen`, `IdCaptureRegion.Us`, `IdCaptureRegion.Germany`, `IdCaptureRegion.France`. Use `rejectedDocuments` to carve out exceptions from a broad accept list:

```ts
settings.acceptedDocuments.push(new DriverLicense(IdCaptureRegion.Any));
settings.rejectedDocuments.push(new DriverLicense(IdCaptureRegion.Us)); // accept all DLs except US
```

### Choosing a scanner

Set `settings.scanner` to an `IdCaptureScanner`, which wraps a physical and/or a mobile scanner. The first positional argument is the physical scanner, the second is the mobile-document scanner:

| Goal | Scanner |
|---|---|
| Read whatever side(s) the SDK needs, automatically (front + back) | `new IdCaptureScanner(new FullDocumentScanner())` |
| Read a single side, only the zones you enable | `new IdCaptureScanner(new SingleSideScanner(barcode, machineReadableZone, visualInspectionZone))` |
| Read a mobile document (mDL) | `new IdCaptureScanner(undefined, new MobileDocumentScanner(true, false))` |

`SingleSideScanner` takes three positional booleans — `barcode`, `machineReadableZone` (MRZ), `visualInspectionZone` (VIZ / printed text).

### Extracting images (optional)

By default images are not returned. Opt in per image type:

```ts
import { IdImageType } from 'scandit-capacitor-datacapture-id';

settings.setShouldPassImageTypeToResult(IdImageType.Face, true);
settings.setShouldPassImageTypeToResult(IdImageType.CroppedDocument, true);
// IdImageType also has `Frame`.
```

### Anonymization (optional)

```ts
import { IdAnonymizationMode } from 'scandit-capacitor-datacapture-id';

settings.anonymizationMode = IdAnonymizationMode.FieldsAndImages;
// Values: None, FieldsOnly, ImagesOnly, FieldsAndImages.
```

For per-field anonymization, use `settings.addAnonymizedField(document, IdFieldType.<Field>)` for each field/document combination you want masked.

## Step 4 — Create IdCapture and attach a listener

`IdCapture` is constructed with `new IdCapture(settings)`. The listener is a plain object literal with optional `didCaptureId` / `didRejectId` methods, and `addListener` returns a Promise — `await` it:

```ts
import { IdCapture, CapturedId, RejectionReason } from 'scandit-capacitor-datacapture-id';

const idCapture = new IdCapture(settings);

const idCaptureListener = {
  didCaptureId: (_: IdCapture, capturedId: CapturedId) => {
    // Pause scanning while you present the result.
    idCapture.isEnabled = false;
    // ...show result; set idCapture.isEnabled = true when ready to resume.
  },
  didRejectId: (_: IdCapture, rejectedId: CapturedId | null, reason: RejectionReason) => {
    idCapture.isEnabled = false;
    // ...map `reason` to a user-facing message.
  },
};

await idCapture.addListener(idCaptureListener);
await context.setMode(idCapture);
```

A document is **rejected** when it's seen but not delivered. Map the reason to a user-facing message:

```ts
function messageFor(reason: RejectionReason): string {
  switch (reason) {
    case RejectionReason.NotAcceptedDocumentType:
      return 'Document not supported. Try another document.';
    case RejectionReason.Timeout:
      return 'Capture timed out. Ensure the document is well lit and free of glare.';
    default:
      return `Document capture was rejected. Reason: ${reason}.`;
  }
}
```

`RejectionReason` values (PascalCase names, camelCase wire values): `NotAcceptedDocumentType`, `InvalidFormat`, `DocumentVoided`, `Timeout`, `SingleImageNotRecognized`, `DocumentExpired`, `DocumentExpiresSoon`, `NotRealIdCompliant`, `HolderUnderage`, `ForgedAamvaBarcode`, `InconsistentData`, `BluetoothCommunicationError`, `BluetoothUnavailable`.

## Step 5 — Set up the camera

Use `Camera.withSettings(IdCapture.createRecommendedCameraSettings())` to construct a camera with the resolution / zoom tuned for document capture. Then set it as the frame source and switch it on.

```ts
import { Camera, FrameSourceState } from 'scandit-capacitor-datacapture-core';

// Camera.withSettings is typed `Camera | null` — guard it.
const camera = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
if (!camera) {
  throw new Error('No camera available on this device');
}
await context.setFrameSource(camera);
await camera.switchToDesiredState(FrameSourceState.On);
idCapture.isEnabled = true;
```

## Step 6 — Render the view and attach the overlay

The Capacitor `DataCaptureView` is an **imperative class** — not a custom element, not a React/Vue/Angular component. Create it, then attach it to a plain `<div>` in your DOM via `view.connectToElement(...)`.

```html
<!-- index.html -->
<div id="data-capture-view" style="width: 100vw; height: 100vh; z-index: -1"></div>
```

```ts
import { DataCaptureView } from 'scandit-capacitor-datacapture-core';
import { IdCaptureOverlay, IdLayoutStyle } from 'scandit-capacitor-datacapture-id';

const view = DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view')!);

const overlay = new IdCaptureOverlay(idCapture);
overlay.idLayoutStyle = IdLayoutStyle.Rounded;
view.addOverlay(overlay);
```

> **Use the plain constructors.** `new IdCapture(settings)` and `new IdCaptureOverlay(idCapture)` are the only forms on Capacitor. Do not write `IdCapture.forContext(...)`, `IdCaptureOverlay.withIdCapture(...)`, or any custom-element / React-style component for the view — those are other modes' or other platforms' APIs and do not exist here.

When navigating away from the scan view, call `view.detachFromElement()` so the native overlay is cleaned up.

## Step 7 — Camera permissions

The Scandit `Camera` class does not request permissions itself; use the official `@capacitor/camera` plugin:

```ts
import { Camera as CapacitorCamera } from '@capacitor/camera';

const status = await CapacitorCamera.checkPermissions();
if (status.camera !== 'granted') {
  const result = await CapacitorCamera.requestPermissions({ permissions: ['camera'] });
  if (result.camera !== 'granted') throw new Error('Camera permission denied');
}
```

Call this before mounting the scan screen (or before `camera.switchToDesiredState(FrameSourceState.On)`).

## Step 8 — Handle the app lifecycle

Use the Capacitor `App` plugin (`@capacitor/app`) to pause / resume the camera and the ID Capture mode when the app goes to background:

```ts
import { App } from '@capacitor/app';

const handle = await App.addListener('appStateChange', async ({ isActive }) => {
  if (!isActive) {
    idCapture.isEnabled = false;
    await camera.switchToDesiredState(FrameSourceState.Off);
  } else {
    await camera.switchToDesiredState(FrameSourceState.On);
    idCapture.isEnabled = true;
  }
});

// On teardown:
// handle.remove();
// view.detachFromElement();
// await context.removeMode(idCapture);
```

## Step 9 — Reading the CapturedId

`CapturedId` exposes harmonized fields regardless of which zone produced them. Note: on Capacitor the source-specific results are named `mrzResult` / `vizResult` (with `Result` suffix), not `mrz` / `viz`.

- Identity: `firstName`, `lastName`, `fullName`, `sex`, `dateOfBirth`, `nationality`, `nationalityISO`, `address`, `age`.
- Document: `documentNumber`, `documentAdditionalNumber`, `dateOfExpiry`, `dateOfIssue`, `isExpired`, `issuingCountry` / `issuingCountryIso`. The document **type** is on `capturedId.document` (an `IdCaptureDocument | null`): use `capturedId.document?.documentType` (an `IdCaptureDocumentType`) or the convenience methods `isIdCard()`, `isDriverLicense()`, `isPassport()`, `isResidencePermit()`, `isHealthInsuranceCard()`, `isVisaIcao()`, `isRegionSpecific(subtype)`. There is **no** `capturedId.documentType` getter, **no** `isVisa()`, **no** `isVisaLetter()`.
- Source-specific results (nullable): `mrzResult` (`MRZResult | null`), `vizResult` (`VIZResult | null`), `barcode` (`BarcodeResult | null`), `mobileDocument` (`MobileDocumentResult | null`), `mobileDocumentOcr` (`MobileDocumentOCRResult | null`).
- `images` (`IdImages`) — read images with `images.face`, `images.frame`, `images.getCroppedDocument(IdSide.Front)`, `images.getFrame(IdSide.Front)`. **Each returns a base64 `string | null`**, e.g. `<img src="data:image/png;base64,${face}">` or `imgEl.src = 'data:image/png;base64,' + face`. There is no `images.croppedDocument` getter — use `getCroppedDocument(IdSide.Front)` / `IdSide.Back`. Images are only populated for the `IdImageType`s you opted into via `setShouldPassImageTypeToResult(...)`.
- `verificationResult` (`VerificationResult`) — contains `dataConsistency` (`DataConsistencyResult | null`, populated when `settings.rejectInconsistentData = true`; read `dataConsistency.allChecksPassed`) and `aamvaBarcodeVerification` (see `references/supplementary-modules.md`).

Date fields are `DateResult | null` with `{ year, month, day }`. Format e.g. with `new Date(Date.UTC(d.year, d.month - 1, d.day)).toLocaleDateString('en-GB', { timeZone: 'UTC' })`. Branch on the source when you need zone-specific data:

```ts
if (capturedId.mrzResult) {
  // passport / MRZ specifics
} else if (capturedId.vizResult) {
  // printed-zone specifics (driving-license categories, etc.)
} else if (capturedId.barcode) {
  // barcode specifics (e.g. US DL PDF417)
}
```

## Common pitfalls

- **Skipping `await ScanditCaptureCorePlugin.initializePlugins()`** — the native bridge isn't wired; every subsequent Scandit call fails with "plugin not implemented".
- **Calling `DataCaptureContext.sharedInstance`** — that's the RN pattern. On Capacitor, capture the return value of `DataCaptureContext.initialize(licenseKey)`.
- **Using the removed `supportedDocuments` / `IdDocumentType` bitmask API.** v8 is list-based: `acceptedDocuments` + `scanner`. See `references/migration.md`.
- **Using `settings.scannerType = …`** — renamed to `settings.scanner` and reshaped into an `IdCaptureScanner` wrapper at v7 → v8.
- **Forgetting `await` on Promise APIs** (`addListener`, `removeListener`, `setMode`, `applySettings`, `setFrameSource`, `switchToDesiredState`) — causes startup races.
- **Using `Camera.default`** — that's RN/Flutter. On Capacitor: `Camera.withSettings(IdCapture.createRecommendedCameraSettings())`.
- **Reaching for `<data-capture-view>` or a `<DataCaptureView>` component** — neither exists on Capacitor. Use `DataCaptureView.forContext(context).connectToElement(divEl)`.
- **Using Flutter-style lowercase enum values** (`IdCaptureRegion.us`, `IdSide.front`). On Capacitor it's `IdCaptureRegion.Us`, `IdSide.Front`.
- **Reading `capturedId.mrz` or `capturedId.viz`** — Flutter names. On Capacitor it's `mrzResult` and `vizResult`.
- **Treating `images.face` like a URI or file** — it's a base64 string. Use the `data:` URI form when rendering.
- **Not detaching the view on teardown** → memory / overlay leak. Call `view.detachFromElement()` and `await context.removeMode(idCapture)` when navigating away.
- **Calling methods on `Camera.withSettings(...)` without a null guard** → TypeScript strict-null errors (`'camera' is possibly 'null'`). `Camera.withSettings(...)` is typed `Camera | null`; always check or throw before dereferencing.

## Reference links

- [Get Started](https://docs.scandit.com/sdks/capacitor/id-capture/get-started/)
- [Advanced Configurations](https://docs.scandit.com/sdks/capacitor/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
