# ID Capture React Native Integration Guide

ID Capture reads identity documents — passports, driver's licenses, national ID cards, residence permits, ICAO visas — and returns structured data (name, date of birth, document number, expiry, etc.) from the document's barcode, Machine Readable Zone (MRZ), and/or Visual Inspection Zone (VIZ / printed text). It can also read mobile documents (mobile driver's licenses).

You declare **which documents to accept** and **which scanner to use**, attach a listener, and the SDK delivers a `CapturedId` per successful scan (or a `RejectionReason` when a document is seen but not accepted).

## Prerequisites

- Scandit React Native packages in `package.json`:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-id`
  - (Add-on capabilities live in separate packages — see `references/supplementary-modules.md`.)
- React Native `>=0.74` is recommended.
- A valid Scandit license key, **enabled for ID Capture**:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request it at runtime with `PermissionsAndroid` (the built-in React Native API) before pushing the scan screen.

## Step 1 — Initialize the DataCaptureContext

There is **no separate plugin-init call** on React Native — importing the core module sets the runtime up. You only need to initialize the data capture context with your license key, once, at module load:

```tsx
// CaptureContext.ts
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

From here on, the rest of the app imports `DataCaptureContext.sharedInstance`. This is the convention the official `IdCaptureSimpleSample` follows.

## Step 2 — Configure IdCaptureSettings

Two decisions: **which documents** to accept and **which scanner** to use.

```tsx
import {
  IdCaptureSettings,
  IdCaptureScanner,
  FullDocumentScanner,
  IdCard,
  DriverLicense,
  Passport,
  IdCaptureRegion,
} from 'scandit-react-native-datacapture-id';

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

> **Note:** There is no `VisaLetter` document class on React Native — only `VisaIcao` ships. If you need visa-letter scanning, that's not available on this platform; choose another scanner-zone strategy or contact Scandit.

`IdCaptureRegion` is a PascalCase TS enum with camelCase wire values — write `IdCaptureRegion.Any`, `IdCaptureRegion.EuAndSchengen`, `IdCaptureRegion.Us`, `IdCaptureRegion.Germany`, `IdCaptureRegion.France`. Use `rejectedDocuments` to carve out exceptions from a broad accept list:

```tsx
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

`SingleSideScanner` takes three positional booleans — `barcode`, `machineReadableZone` (MRZ), `visualInspectionZone` (VIZ / printed text). Example: the PDF417 barcode on the back of a US driver's license → `new SingleSideScanner(true, false, false)`; a passport MRZ → `new SingleSideScanner(false, true, false)`; the printed front of a card → `new SingleSideScanner(false, false, true)`.

### Extracting images (optional)

By default images are not returned. Opt in per image type:

```tsx
import { IdImageType } from 'scandit-react-native-datacapture-id';

settings.setShouldPassImageTypeToResult(IdImageType.Face, true);
settings.setShouldPassImageTypeToResult(IdImageType.CroppedDocument, true);
// IdImageType also has `Frame`.
```

### Anonymization (optional)

Control what sensitive data is returned:

```tsx
import { IdAnonymizationMode } from 'scandit-react-native-datacapture-id';

settings.anonymizationMode = IdAnonymizationMode.FieldsAndImages;
// Values: None, FieldsOnly, ImagesOnly, FieldsAndImages.
```

For per-field anonymization, use `settings.addAnonymizedField(document, IdFieldType.<Field>)` for each field/document combination you want masked.

## Step 3 — Create IdCapture and attach a listener

`IdCapture` is constructed with `new IdCapture(settings)` — there is **no** `IdCapture.forContext(...)` factory on RN. The listener is a plain object literal with optional `didCaptureId` / `didRejectId` methods, and `addListener` returns a Promise — `await` it:

```tsx
import { IdCapture, CapturedId, RejectionReason } from 'scandit-react-native-datacapture-id';

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
await dataCaptureContext.setMode(idCapture);
```

> **One mode at a time.** `IdCapture` cannot run simultaneously with another capture mode (e.g. `BarcodeCapture`, `SparkScan`, `BarcodeTracking`) on the same `DataCaptureContext`. Use `await context.setMode(idCapture)` — it replaces any currently-active mode (internally it removes all modes, then adds this one). Do **not** `await context.addMode(idCapture)` alongside another mode expecting both to run; only one mode is active at a time. To switch between products, call `setMode` with the other mode (or `removeMode(idCapture)` first), and re-enable as needed.

A document is **rejected** when it's seen but not delivered — e.g. it's a valid document type not in `acceptedDocuments`, the format is wrong, capture timed out, or (with add-on capabilities) it's voided / expired / a forged AAMVA barcode. Map the reason to a user-facing message:

```tsx
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

## Step 4 — Pattern A: `<DataCaptureView>` + manual overlay (recommended; matches the official sample)

```tsx
import { DataCaptureView, Camera, FrameSourceState } from 'scandit-react-native-datacapture-core';
import { IdCaptureOverlay, IdLayoutStyle } from 'scandit-react-native-datacapture-id';

const overlay = new IdCaptureOverlay(idCapture);
overlay.idLayoutStyle = IdLayoutStyle.Rounded;

// Camera setup. Camera.default is typed `Camera | null` — guard it.
const camera = Camera.default;
if (!camera) {
  throw new Error('No camera available on this device');
}
await camera.applySettings(IdCapture.createRecommendedCameraSettings());
await dataCaptureContext.setFrameSource(camera);
await camera.switchToDesiredState(FrameSourceState.On);
idCapture.isEnabled = true;

// Render the view; attach the overlay through its ref.
const viewRef = useRef<DataCaptureView | null>(null);

return (
  <DataCaptureView
    style={{ flex: 1 }}
    context={dataCaptureContext}
    ref={view => {
      if (view && !viewRef.current) {
        view.addOverlay(overlay);
        viewRef.current = view;
      }
    }}
  />
);
```

> **Use the plain constructors.** `new IdCapture(settings)` and `new IdCaptureOverlay(idCapture)` are the only forms on RN. Do not write `IdCapture.forContext(...)`, `IdCaptureOverlay.withIdCapture(...)`, or `IdCaptureOverlay.withIdCaptureForView(...)` — those are other modes' or other platforms' APIs and do not exist here. The mode is attached to the context via `await context.setMode(idCapture)`, and the overlay to the view via `view.addOverlay(overlay)`.

## Step 4 (alternative) — Pattern B: `<IdCaptureView>` shorthand

The id package also ships a higher-level React component, `IdCaptureView`, that wraps the mode + camera + overlay + listener wiring behind props. It's terser but less flexible than Pattern A; the official public sample uses Pattern A. Use this only when the project really wants the shorthand and doesn't need to compose other overlays on the same view.

```tsx
import { IdCaptureView } from 'scandit-react-native-datacapture-id';
import { FrameSourceState } from 'scandit-react-native-datacapture-core';

return (
  <IdCaptureView
    context={dataCaptureContext}
    isEnabled={isEnabled}
    idCaptureSettings={settings}
    desiredCameraState={FrameSourceState.On}
    didCaptureId={(_, capturedId) => { /* … */ }}
    didRejectId={(_, rejectedId, reason) => { /* … */ }}
    navigation={navigation}
  />
);
```

`<IdCaptureView>` exposes an imperative `reset()` handle via `forwardRef`. Anything you'd configure on the overlay (brushes, layout style) is passed as a prop (`capturedBrush`, `localizedBrush`, `rejectedBrush`).

## Step 5 — Camera permissions

Use React Native's built-in `PermissionsAndroid` for Android; iOS is gated by the `NSCameraUsageDescription` in `Info.plist`.

```tsx
import { PermissionsAndroid, Platform } from 'react-native';

export async function requestCameraPermissionsIfNeeded(): Promise<void> {
  if (Platform.OS !== 'android' || Platform.Version < 23) return;
  const ok = await PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.CAMERA);
  if (ok) return;
  const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA);
  if (granted !== PermissionsAndroid.RESULTS.GRANTED) throw new Error('Camera permission denied');
}
```

Call `await requestCameraPermissionsIfNeeded()` before mounting the scan screen.

## Step 6 — Handle the camera lifecycle with `AppState`

```tsx
import { AppState, AppStateStatus } from 'react-native';

useEffect(() => {
  const sub = AppState.addEventListener('change', (next: AppStateStatus) => {
    if (next.match(/inactive|background/)) {
      idCapture.isEnabled = false;
      camera?.switchToDesiredState(FrameSourceState.Off);
    } else if (next === 'active' && navigation.isFocused()) {
      camera?.switchToDesiredState(FrameSourceState.On);
      idCapture.isEnabled = true;
    }
  });
  return () => {
    sub.remove();
    dataCaptureContext.removeMode(idCapture);
  };
}, []);
```

The `navigation.isFocused()` guard prevents the camera from restarting on `AppState 'active'` when the scan screen is no longer the current route.

## Step 7 — Reading the CapturedId

`CapturedId` exposes harmonized fields regardless of which zone produced them. Note: on React Native the source-specific results are named `mrzResult` / `vizResult` (with `Result` suffix), not `mrz` / `viz`.

- Identity: `firstName`, `lastName`, `fullName`, `sex`, `dateOfBirth`, `nationality`, `nationalityISO`, `address`, `age`.
- Document: `documentNumber`, `documentAdditionalNumber`, `dateOfExpiry`, `dateOfIssue`, `isExpired`, `issuingCountry` / `issuingCountryIso`. The document **type** is on `capturedId.document` (an `IdCaptureDocument | null`): use `capturedId.document?.documentType` (an `IdCaptureDocumentType`) or the convenience methods `isIdCard()`, `isDriverLicense()`, `isPassport()`, `isResidencePermit()`, `isHealthInsuranceCard()`, `isVisaIcao()`, `isRegionSpecific(subtype)`. There is **no** `capturedId.documentType` getter, **no** `isVisa()`, **no** `isVisaLetter()` — and the removed `IdDocumentType` enum does not exist; do not use any of those.
- Source-specific results (nullable): `mrzResult` (`MRZResult | null`), `vizResult` (`VIZResult | null`), `barcode` (`BarcodeResult | null`), `mobileDocument` (`MobileDocumentResult | null`), `mobileDocumentOcr` (`MobileDocumentOCRResult | null`).
- `images` (`IdImages`) — read images with `images.face`, `images.frame`, `images.getCroppedDocument(IdSide.Front)`, `images.getFrame(IdSide.Front)`. **Each returns a base64 `string | null`**, e.g. `<Image source={{ uri: 'data:image/png;base64,' + face }} />`. There is **no** `images.croppedDocument` getter — use `getCroppedDocument(IdSide.Front)` / `IdSide.Back`. Images are only populated for the `IdImageType`s you opted into via `setShouldPassImageTypeToResult(...)`.
- `verificationResult` (`VerificationResult`) — contains `dataConsistency` and `aamvaBarcodeVerification` (see `references/supplementary-modules.md`).

Date fields are `DateResult | null` with `{ year, month, day }`. Format e.g. with `new Date(Date.UTC(d.year, d.month - 1, d.day)).toLocaleDateString('en-GB', { timeZone: 'UTC' })`. Branch on the source when you need zone-specific data:

```tsx
if (capturedId.mrzResult) {
  // passport / MRZ specifics
} else if (capturedId.vizResult) {
  // printed-zone specifics (driving-license categories, etc.)
} else if (capturedId.barcode) {
  // barcode specifics (e.g. US DL PDF417)
}
```

## Common pitfalls

- **Calling `ScanditDataCaptureId.initialize()`** — that's the Flutter API. On RN you only call `DataCaptureContext.initialize(licenseKey)` once.
- **Using the removed `supportedDocuments` / `IdDocumentType` bitmask API.** v8 is list-based: `acceptedDocuments` + `scanner`. See `references/migration.md`.
- **Using `settings.scannerType = …`** — renamed to `settings.scanner` and reshaped into an `IdCaptureScanner` wrapper at v7 → v8.
- **Forgetting `await` on Promise APIs** (`addListener`, `removeListener`, `setMode`, `applySettings`, `setFrameSource`, `switchToDesiredState`) — causes startup races and "listener not registered" symptoms.
- **Using Flutter-style lowercase enum values** (`IdCaptureRegion.us`, `IdSide.front`). On RN it's `IdCaptureRegion.Us`, `IdSide.Front`.
- **Reading `capturedId.mrz` or `capturedId.viz`** — those are Flutter names. On RN it's `mrzResult` and `vizResult`.
- **Treating `images.face` like a URI or file** — it's a base64 string. Use the `data:` URI form when rendering.
- **Not disabling the mode while a result modal is shown** → the listener fires repeatedly. Set `idCapture.isEnabled = false` in the callback and re-enable after dismissal.
- **Calling methods on `Camera.default` without a null guard** → TypeScript strict-null errors (`'camera' is possibly 'null'`). `Camera.default` is typed `Camera | null`; always check or throw before dereferencing.
- **Forgetting to `removeMode` on unmount** — leaks the mode on the context across navigation. Use the `useEffect` cleanup as in Step 6.

## Reference links

- [Get Started](https://docs.scandit.com/sdks/react-native/id-capture/get-started/)
- [Advanced Configurations](https://docs.scandit.com/sdks/react-native/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/react-native/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
