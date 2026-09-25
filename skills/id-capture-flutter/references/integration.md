# ID Capture Flutter Integration Guide

ID Capture reads identity documents — passports, driver's licenses, national ID cards, residence permits, visas — and returns structured data (name, date of birth, document number, expiry, etc.) from the document's barcode, Machine Readable Zone (MRZ), and/or Visual Inspection Zone (VIZ / printed text). It can also read mobile documents (mobile driver's licenses).

You declare **which documents to accept** and **which scanner to use**, attach a listener, and the SDK delivers a `CapturedId` per successful scan (or a `RejectionReason` when a document is seen but not accepted).

## Prerequisites

- Scandit Flutter packages in `pubspec.yaml`:
  - `scandit_flutter_datacapture_core`
  - `scandit_flutter_datacapture_id`
  - (Add-on capabilities live in separate packages — see `references/supplementary-modules.md`.)
- Flutter `>=3.22.0`, Dart `>=3.4.0`.
- A valid Scandit license key, **enabled for ID Capture**:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request it at runtime with `permission_handler` (or equivalent) before pushing the scan screen.

## Step 1 — Initialize the ID plugin

The ID plugin **must** be initialized before any Scandit API is touched. Initializing it also initializes the core plugin, so you do not call a separate core initializer.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_id/scandit_flutter_datacapture_id.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureId.initialize();
  runApp(const MyApp());
}
```

## Step 2 — Create the DataCaptureContext with your license key

```dart
const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

final DataCaptureContext context = DataCaptureContext.forLicenseKey(licenseKey);
```

> Use `DataCaptureContext.forLicenseKey(...)` — this is the constructor the official Flutter ID samples use.

## Step 3 — Configure IdCaptureSettings

Two decisions: **which documents** to accept and **which scanner** to use.

```dart
final settings = IdCaptureSettings();

// Which documents to accept. Narrow by region/country where you can — it's
// faster and more accurate than IdCaptureRegion.any across all types.
settings.acceptedDocuments.addAll([
  IdCard(IdCaptureRegion.any),
  DriverLicense(IdCaptureRegion.any),
  Passport(IdCaptureRegion.any),
]);

// Which scanner to use. FullDocumentScanner reads front + back automatically.
settings.scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());
```

### Choosing documents

Accepted-document classes each take an `IdCaptureRegion`:

`IdCard(region)`, `DriverLicense(region)`, `Passport(region)`, `ResidencePermit(region)`, `VisaIcao(region)`, `VisaLetter(region)`, `HealthInsuranceCard(region)`, and `RegionSpecific(subtype)` (which takes a `RegionSpecificSubtype` instead of a region).

`IdCaptureRegion` has `any`, broad regions (`euAndSchengen`), and per-country values (`us`, `germany`, `france`, …). Use `rejectedDocuments` to carve out exceptions from a broad accept list:

```dart
settings.acceptedDocuments.add(DriverLicense(IdCaptureRegion.any));
settings.rejectedDocuments.add(DriverLicense(IdCaptureRegion.us)); // accept all DLs except US
```

### Choosing a scanner

Set `settings.scanner` to an `IdCaptureScanner`, which wraps a physical and/or a mobile scanner:

| Goal | Scanner |
|---|---|
| Read whatever side(s) the SDK needs, automatically (front + back) | `IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner())` |
| Read a single side, only the zones you enable | `IdCaptureScanner(physicalDocumentScanner: SingleSideScanner(barcode, machineReadableZone, visualInspectionZone))` |
| Read a mobile document (mDL) | `IdCaptureScanner(mobileDocumentScanner: MobileDocumentScanner(iso180135: true, ocr: false))` |

`SingleSideScanner` takes three booleans in order — `barcode`, `machineReadableZone` (MRZ), `visualInspectionZone` (VIZ / printed text). Example: the PDF417 barcode on the back of a US driver's license → `SingleSideScanner(true, false, false)`; a passport MRZ → `SingleSideScanner(false, true, false)`; the printed front of a card → `SingleSideScanner(false, false, true)`.

### Extracting images (optional)

By default images are not returned. Opt in per image type:

```dart
settings.setShouldPassImageTypeToResult(IdImageType.face, true);
settings.setShouldPassImageTypeToResult(IdImageType.croppedDocument, true);
// IdImageType also has `frame`.
```

### Anonymization (optional)

Control what sensitive data is returned:

```dart
settings.anonymizationMode = IdAnonymizationMode.fieldsAndImages;
// Values: none, fieldsOnly, imagesOnly, fieldsAndImages.
```

## Step 4 — Create IdCapture, the view, and the overlay

```dart
// The mode.
final idCapture = IdCapture(settings)..addListener(this);

// The camera preview view, bound to the context.
final captureView = DataCaptureView.forContext(context);

// Optional but recommended: an overlay that draws the captured/located document.
final overlay = IdCaptureOverlay(idCapture)..idLayoutStyle = IdLayoutStyle.rounded;
captureView.addOverlay(overlay);

// Register the mode with the context.
context.setMode(idCapture);
```

> **Use the plain constructors.** `IdCapture(settings)` and `IdCaptureOverlay(idCapture)` are the only forms on Flutter. Do **not** write `IdCapture.forContext(context, settings)`, `IdCaptureOverlay.withIdCapture(...)`, or `IdCaptureOverlay.withIdCaptureForView(...)` — those are other modes' / other platforms' APIs and do not exist here. The mode is attached to the context via `context.setMode(idCapture)`, and the overlay to the view via `captureView.addOverlay(overlay)`.

## Step 5 — Set up and control the camera

```dart
Camera? camera = Camera.defaultCamera;
camera?.applySettings(IdCapture.createRecommendedCameraSettings());

context.setFrameSource(camera!);
camera.switchToDesiredState(FrameSourceState.on);
idCapture.isEnabled = true;
```

Always use `IdCapture.createRecommendedCameraSettings()` for the camera resolution/zoom tuned for document capture.

## Step 6 — Handle results with IdCaptureListener

Implement `IdCaptureListener`. The two callbacks are `didCaptureId` and `didRejectId`:

```dart
class _IdScanScreenState extends State<IdScanScreen>
    with WidgetsBindingObserver
    implements IdCaptureListener {

  @override
  Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
    // Pause scanning while you present the result.
    idCapture.isEnabled = false;

    final summary = '''
Full name: ${capturedId.fullName}
Date of birth: ${capturedId.dateOfBirth?.localDate}
Date of expiry: ${capturedId.dateOfExpiry?.localDate}
Document number: ${capturedId.documentNumber}
Nationality: ${capturedId.nationality}
''';
    // ...present `summary`, then re-enable when done:
    // idCapture.isEnabled = true;
  }

  @override
  Future<void> didRejectId(
      IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
    idCapture.isEnabled = false;
    // ...present a message based on `reason`, then re-enable.
  }
}
```

A document is **rejected** when it's seen but not delivered — e.g. it's a valid document type not in `acceptedDocuments`, the format is wrong, capture timed out, or (with add-on capabilities) it's voided / expired / a forged AAMVA barcode. Map the reason to a user-facing message:

```dart
String messageFor(RejectionReason reason) {
  switch (reason) {
    case RejectionReason.notAcceptedDocumentType:
      return 'Document not supported. Try another document.';
    case RejectionReason.timeout:
      return 'Capture timed out. Ensure the document is well lit and free of glare.';
    default:
      return 'Document capture was rejected. Reason: $reason.';
  }
}
```

`RejectionReason` values: `notAcceptedDocumentType`, `invalidFormat`, `documentVoided`, `timeout`, `singleImageNotRecognized`, `documentExpired`, `documentExpiresSoon`, `notRealIdCompliant`, `holderUnderage`, `forgedAamvaBarcode`, `inconsistentData`, `bluetoothCommunicationError`, `bluetoothUnavailable`.

## Step 7 — Reading the CapturedId

`CapturedId` exposes harmonized fields regardless of which zone produced them:

- Identity: `firstName`, `lastName`, `fullName`, `sex` / `sexType`, `dateOfBirth`, `nationality`, `address`, `age`
- Document: `documentNumber`, `documentAdditionalNumber`, `dateOfExpiry`, `dateOfIssue`, `isExpired`, `issuingCountry` / `issuingCountryIso`. The document **type** is on `capturedId.document` (an `IdCaptureDocument?`): use `capturedId.document?.documentType` (an `IdCaptureDocumentType` — `idCard`, `driverLicense`, `passport`, …) or the convenience methods: `isIdCard()`, `isDriverLicense()`, `isPassport()`, `isResidencePermit()`, `isHealthInsuranceCard()`, `isVisaIcao()`, `isVisaLetter()`, `isRegionSpecific(subtype)`. (There is no `isVisa()` — visas are `isVisaIcao()` / `isVisaLetter()`.) There is **no** `capturedId.documentType` getter, and `IdDocumentType` does not exist (removed) — do not use either.
- Source-specific results (nullable): `mrz` (`MrzResult`), `viz` (`VizResult`), `barcode` (`BarcodeResult`), `mobileDocument` (`MobileDocumentResult`)
- `images` (`IdImages`) — read images with `images.face`, `images.frame`, `images.getCroppedDocument(IdSide.front)`, `images.getFrame(IdSide.front)`. **Each returns a Flutter `Image` widget (`Image?` from `package:flutter/material.dart`), already decoded** — place it straight into the widget tree (e.g. `if (capturedId.images.face != null) capturedId.images.face!`). Do not call `.buffer`, `.bytes`, `Image.memory(...)`, or any byte/base64 accessor on it — it is a ready-to-render widget, not raw data. There is no `images.croppedDocument` getter — use `getCroppedDocument(IdSide.front)` / `IdSide.back`. Images are only populated for the `IdImageType`s you opted into via `setShouldPassImageTypeToResult(...)`.
- `verificationResult` (`VerificationResult`)

Date fields are `DateResult?` — use `.localDate` / `.utcDate`. Branch on the source when you need zone-specific data:

```dart
if (capturedId.mrz != null) {
  // passport / MRZ specifics
} else if (capturedId.viz != null) {
  // printed-zone specifics (driving-license categories, etc.)
} else if (capturedId.barcode != null) {
  // barcode specifics (e.g. US DL PDF417)
}
```

## Step 8 — Lifecycle and cleanup

Tie the camera to the widget lifecycle and disable the mode when leaving the screen.

```dart
@override
void didChangeAppLifecycleState(AppLifecycleState state) {
  if (state == AppLifecycleState.resumed) {
    _checkPermissionAndStart();
  } else {
    camera?.switchToDesiredState(FrameSourceState.off);
  }
}

void _cleanup() {
  WidgetsBinding.instance.removeObserver(this);
  idCapture.removeListener(this);
  idCapture.isEnabled = false;
  camera?.switchToDesiredState(FrameSourceState.off);
  context.removeAllModes();
}
```

## Co-existence with Barcode Capture

`IdCapture` and `BarcodeCapture` can run **together on one `DataCaptureContext`** — one context, one `DataCaptureView`, one camera. A common case is an airport screen that reads a boarding-pass PDF417 barcode **and** a passport/ID at the same time.

Attach **both** modes with `context.addMode(idCapture)` **and** `context.addMode(barcodeCapture)`. Do **not** use `context.setMode(...)` here — `setMode` **replaces** the context's current mode, so calling it twice would leave only the last mode. `setMode` is fine for a single-mode screen; for co-existence use `addMode` for each. Give each mode its own listener and toggle each independently with `mode.isEnabled` — both can be enabled at once and the native layer runs them together.

```dart
// BarcodeCapture/BarcodeCaptureSettings come from the scandit_flutter_datacapture_barcode
// package — add it to pubspec.yaml and import the barcode_capture entry point:
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_capture.dart';

// ID Capture mode (passport / ID)
final idSettings = IdCaptureSettings()
  ..acceptedDocuments = [Passport(IdCaptureRegion.any)]
  ..scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());
final idCapture = IdCapture(idSettings);
idCapture.addListener(this); // implements IdCaptureListener
context.addMode(idCapture);

// Barcode Capture mode (IATA boarding pass = PDF417), same context
final bcSettings = BarcodeCaptureSettings()
  ..enableSymbologies({Symbology.pdf417});
final barcodeCapture = BarcodeCapture(bcSettings);
barcodeCapture.addListener(this); // implements BarcodeCaptureListener
context.addMode(barcodeCapture);

// Both can be enabled at once — they run together.
idCapture.isEnabled = true;
barcodeCapture.isEnabled = true;
```

In `didScan` read `session.newlyRecognizedBarcode`; in `didCaptureId` read the `CapturedId`. When tearing down both modes, `context.removeAllModes()` removes them all at once.

## Common pitfalls

- **Forgetting `await ScanditFlutterDataCaptureId.initialize()`** in `main()` → opaque MethodChannel crashes. It must run before `runApp` and before any context/settings code.
- **Using the removed `supportedDocuments` / `IdDocumentType` bitmask API.** v8 is list-based: `acceptedDocuments` + `scanner`. See `references/migration.md`.
- **Not disabling the mode while a result dialog is shown** → the listener fires repeatedly. Set `idCapture.isEnabled = false` in the callback and re-enable after dismissal.
- **Expecting images without opting in** — call `setShouldPassImageTypeToResult(...)` for each `IdImageType` you need.
- **Reading a null `dateOfBirth`/`dateOfExpiry`** — these are nullable `DateResult`; guard with `?.`.
- **Reaching for a standalone verifier class.** AAMVA verification on Flutter is settings-driven (`rejectForgedAamvaBarcodes`) with the result on `CapturedId.verificationResult` — see `references/supplementary-modules.md`.

## Reference links

- [Get Started](https://docs.scandit.com/sdks/flutter/id-capture/get-started/)
- [Advanced Configurations](https://docs.scandit.com/sdks/flutter/id-capture/advanced/)
- [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/flutter/id-capture/api.html)
- Add-on capabilities: `references/supplementary-modules.md`
