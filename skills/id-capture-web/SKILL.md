---
name: id-capture-web
description: Use when ID Capture (Scandit identity-document scanning — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas, region-specific subtypes, reading MRZ / VIZ / PDF417 barcode on identity documents / mobile-document data) is involved in a web project (browser, TypeScript/JavaScript, using `@scandit/web-datacapture-id`) — whether the user mentions ID Capture directly, says "scan a passport / driver's license / ID card / identity document in the browser / in JS / in TypeScript / on the web", or the codebase already imports from `@scandit/web-datacapture-id` and something needs to be added, changed, fixed, or customized. This includes integrating ID Capture into a web app, registering `idCaptureLoader({ enableVIZDocuments: true })` on the `DataCaptureContext`, configuring `IdCaptureSettings` with `acceptedDocuments` (`new IdCard(Region.Any)`, `new DriverLicense(Region.Us)`, `new Passport(Region.Any)`, …) and a `scanner` (`new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() | new SingleSideScanner(...) , mobileDocument: new MobileDocumentScanner() })`), creating the mode with `await IdCapture.forContext(context, settings)`, handling results through `addListener({ didCaptureId, didRejectId })`, reading `CapturedId` (`fullName`, `dateOfBirth`, `dateOfExpiry`, `documentNumber`, `mrzResult`, `vizResult`, `barcode`, `images`, `verificationResult`, `usRealIdStatus`), hosting the preview with `DataCaptureView` + `IdCaptureOverlay.withIdCaptureForView(...)`, managing the camera/frame-source lifecycle (`Camera.pickBestGuess()`, `SingleImageUploader`), rejection rules (expired / voided / underage / inconsistent-data / not-accepted / timeout), AAMVA USDL verification via the standalone `AamvaBarcodeVerifier`, data-consistency verification, anonymization, localized overlay hints, button-tap (shutter) capture, or upgrading/migrating the Scandit Web SDK version (v6→v7, v7→v8, or any version bump). If the project runs in a browser and uses `@scandit/web-datacapture-id`, use this skill. Note: the Web SDK is async-first (everything returns Promises) and its API differs substantially from the native iOS/Android/.NET/Flutter/React Native SDKs.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# ID Capture Web (TypeScript/JavaScript) Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit ID Capture APIs. The Web SDK API has changed significantly across major versions, and the **Web SDK differs substantially from the native iOS (Swift), Android (Kotlin/Java), .NET, Flutter, and React Native SDKs**. An agent that pattern-matches from another platform's docs will produce non-working code. Two Web-specific facts dominate:

1. **The Web SDK is async-first.** Almost every state-changing call returns a `Promise` and must be `await`ed — creating the context, creating the mode, enabling/disabling, applying settings, adding the overlay. There are no synchronous constructors for the mode or overlay.
2. **You must register the ID module loader.** `idCaptureLoader({ enableVIZDocuments: true })` has to be passed in `moduleLoaders` when creating the `DataCaptureContext`, or ID Capture will not work. `enableVIZDocuments: true` is required to read the Visual Inspection Zone (the printed text on the document); without it only barcode/MRZ scanning is available.

**Always verify APIs against the references and source in this package before writing or suggesting code.** The most common sources of wrong code:

- **The v6 API** — `supportedDocuments` (a bitmask), `supportedSides`, and session-based callbacks were replaced. Do not emit any of these.
- **The v7.0-era API** — `settings.scannerType = new FullDocumentScanner()` was replaced; the current property is `scanner` and it takes an `IdCaptureScanner` wrapper constructed with an **options object**: `settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() })`.
- **Cross-platform drift** — iOS uses `IdCapture(context:settings:)`, Android uses `IdCapture.forDataCaptureContext(...)`, .NET uses `IdCapture.Create(...)`. The Web API is **`await IdCapture.forContext(context, settings)`**.
- **`isEnabled`** — on Web this is the method `idCapture.isEnabled()` to read and **`await idCapture.setEnabled(true)`** to set. It is NOT an assignable property.
- **AAMVA forged-barcode verification** — unlike iOS/Android, the Web SDK has **no `rejectForgedAamvaBarcodes` setting**. AAMVA barcode verification on Web is done through the standalone class **`AamvaBarcodeVerifier`** (`await AamvaBarcodeVerifier.create(context)`, then `await verifier.verify(capturedId)`). Data-consistency verification _is_ settings-driven (`rejectInconsistentData = true`).
- **Images are base64 data-URL strings, not native bitmaps.** `capturedId.images.face` / `.getFrame(IdSide.Front)` / `.getCroppedDocument(IdSide.Back)` return `string | null` (a `data:image/...` URL), suitable for an `<img>` `src`. They are only populated when enabled via `settings.setShouldPassImageTypeToResult(IdImageType.Face, true)`.

### Forbidden APIs (commonly hallucinated — do NOT emit these)

| Do NOT write                                                                       | Use instead                                                                                |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `new IdCapture(context, settings)`                                                 | `await IdCapture.forContext(context, settings)`                                            |
| `IdCapture.forDataCaptureContext(...)` / `IdCapture.Create(...)`                   | `await IdCapture.forContext(context, settings)`                                            |
| `idCapture.isEnabled = true` / `idCapture.enabled = true`                          | `await idCapture.setEnabled(true)` (read with `idCapture.isEnabled()`)                     |
| `settings.supportedDocuments = [...]` / `settings.supportedSides = ...` (v6)       | `settings.acceptedDocuments = [...]` + `settings.scanner = new IdCaptureScanner({...})`    |
| `settings.scannerType = new FullDocumentScanner()` (v7)                            | `settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() })` |
| `new IdCaptureScanner(new FullDocumentScanner())` (positional)                     | `new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() })` (options object)   |
| `new IdCaptureOverlay(idCapture, view)`                                            | `await IdCaptureOverlay.withIdCaptureForView(idCapture, view)`                             |
| `settings.rejectForgedAamvaBarcodes = true`                                        | `const v = await AamvaBarcodeVerifier.create(context); await v.verify(capturedId)`         |
| `capturedId.barcodeResult`                                                         | `capturedId.barcode`                                                                       |
| `capturedId.images.croppedDocument(side)` / `capturedId.images.face()` as a method | `capturedId.images.getCroppedDocument(IdSide.Front)` / `capturedId.images.face` (a getter) |
| `DataCaptureContext.initialize(licenseKey)` (iOS) / `forLicenseKey(...)` sync      | `await DataCaptureContext.forLicenseKey(key, { moduleLoaders: [idCaptureLoader({...})] })` |
| Creating the context without `idCaptureLoader(...)` in `moduleLoaders`             | always include `idCaptureLoader({ enableVIZDocuments: true })`                             |
| `SDCIdCapture` / `SDCCapturedId` / any `SDC`-prefixed type                         | `IdCapture` / `CapturedId` (no prefix; import from `@scandit/web-datacapture-id`)          |
| `Camera.default` / `camera.switch(toDesiredState:)`                                | `Camera.pickBestGuess()` / `await camera.switchToDesiredState(FrameSourceState.On)`        |

## Intent Routing

Based on the user's request, pick the right path before responding:

- **Questions about other Scandit products or scanning modes** (e.g. Barcode Capture, SparkScan, MatrixScan, Label Capture, or product selection) → hand off to the `data-capture-sdk` skill. Do not attempt to answer questions about other capture modes from memory.
- **Integrating ID Capture from scratch, configuring documents/scanner/rejection rules, reading results, customizing the overlay, or verification** (e.g. "scan a passport in the browser", "reject expired IDs", "show the face image") → use the Product Guidance and Minimal integration shape below, verifying every API against the References.
- **Migrating or upgrading an existing ID Capture integration** (e.g. "upgrade from v6 to v7", "migrate my ID Capture to v8", "bump the Scandit Web SDK", "what changed between SDK versions") → read `references/migration.md` and follow the instructions there.

## Product Guidance

- **Accept only the documents you actually need.** Ask the user which document types and regions they expect. Documents not in `acceptedDocuments` are rejected with `RejectionReason.NotAcceptedDocumentType`.
- **Pick the scanner that matches the data you need.** Ask whether they need both sides and all zones, a single zone only (barcode / MRZ / VIZ), or a mobile-presented ID — then choose `FullDocumentScanner`, `SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)`, or `MobileDocumentScanner`. `SingleSideScanner` takes positional booleans selecting which zone to read.
- **`enableVIZDocuments`.** Reading the printed VIZ (and most full-document scanning) requires `idCaptureLoader({ enableVIZDocuments: true })` and a license entitled for VIZ. If the license lacks VIZ entitlement, loading throws `IdCaptureErrorCode.InvalidLicenseKeyForVIZProcessing`. Barcode-only / MRZ-only flows can run without it.
- **Handle `didRejectId`, not just `didCaptureId`.** Rejections (`Timeout`, `NotAcceptedDocumentType`, `DocumentExpired`, `DocumentVoided`, `HolderUnderage`, `InconsistentData`, `SingleImageNotRecognized`, …) are how the user learns why a scan didn't succeed. `SingleImageNotRecognized` is Web-specific (single-image-upload flows) and usually warrants an `idCapture.reset()`.
- **Disable the mode while handling a result.** The samples consistently `await idCapture.setEnabled(false)` at the top of `didCaptureId`/`didRejectId`, then re-enable when the user dismisses the result. Do the same.
- **Handle `didFailWithError` for recoverable failures.** On `IdCaptureErrorCode.RecoveredAfterFailure`, inform the user and call `idCapture.reset()` so they start over from the front side.
- **Use the Localization API for overlay text.** `IdCaptureOverlay.setFrontSideTextHint(...)` and friends are deprecated. Customize hints via `Localization.getInstance().update({ "id.idCaptureOverlay.scanFrontSideHint": "..." })`.
- **Defer non-ID-Capture questions.** For Barcode Capture, SparkScan, MatrixScan, Label Capture, or product selection, hand off to the `data-capture-sdk` skill — this skill covers ID Capture only.

## Minimal integration shape

Prerequisites: install `@scandit/web-datacapture-core` and `@scandit/web-datacapture-id` (same version) with the project's package manager, and serve the SDK engine files so `libraryLocation` resolves them (the samples copy them to `library/engine/`; self-hosted projects typically use `sdc-lib`). License keys come from <https://ssl.scandit.com> (sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>).

This is the canonical structure shared by every sample under `web/samples/02_ID_Scanning_Samples/`. Use it as the skeleton; adjust documents/scanner/listeners to the task.

```ts
import {
  Camera,
  CameraSwitchControl,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  IdCapture,
  IdCaptureSettings,
  IdCaptureScanner,
  IdCaptureOverlay,
  FullDocumentScanner,
  IdCard,
  Passport,
  DriverLicense,
  Region,
  IdImageType,
  RejectionReason,
  idCaptureLoader,
  type CapturedId,
} from "@scandit/web-datacapture-id";

const view = new DataCaptureView();
view.connectToElement(document.getElementById("data-capture-view")!);
view.showProgressBar();

const context = await DataCaptureContext.forLicenseKey(LICENSE_KEY, {
  libraryLocation: new URL("library/engine/", document.baseURI).toString(),
  moduleLoaders: [idCaptureLoader({ enableVIZDocuments: true })],
});
view.hideProgressBar();

const camera = Camera.pickBestGuess();
await camera.applySettings(IdCapture.recommendedCameraSettings);
await context.setFrameSource(camera);
await view.setContext(context);
view.addControl(new CameraSwitchControl());

const settings = new IdCaptureSettings();
settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() });
settings.acceptedDocuments = [new IdCard(Region.Any), new Passport(Region.Any), new DriverLicense(Region.Any)];
settings.setShouldPassImageTypeToResult(IdImageType.Face, true);

const idCapture = await IdCapture.forContext(context, settings);
idCapture.addListener({
  didCaptureId: async (capturedId: CapturedId) => {
    await idCapture.setEnabled(false);
    // read capturedId.fullName, capturedId.dateOfBirth, capturedId.images.face, ...
  },
  didRejectId: async (_capturedId: CapturedId, reason: RejectionReason) => {
    await idCapture.setEnabled(false);
    // surface a message based on `reason`
  },
});
await IdCaptureOverlay.withIdCaptureForView(idCapture, view);

await idCapture.setEnabled(false); // keep disabled until the camera is on
await camera.switchToDesiredState(FrameSourceState.On);
await idCapture.setEnabled(true);
```

## API Usage Policy

Only use APIs that exist in this package (`@scandit/web-datacapture-id`) and the referenced documentation. Do not invent or guess method signatures, parameters, or property names. When unsure whether an API exists or how to call it, fetch the documentation before responding. Do not tell the user to check the docs themselves. After answering, include the relevant link so they can explore further. **Never construct or guess documentation URLs** — fetch the index page and follow links from there.

## References

| Topic                  | Resource                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Get Started (Web)      | [Get Started (Web)](https://docs.scandit.com/sdks/web/id-capture/get-started/)            |
| Advanced configuration | [Advanced (Web)](https://docs.scandit.com/sdks/web/id-capture/advanced/)                  |
| Migration between major SDK versions | [6 → 7](https://docs.scandit.com/sdks/web/migrate-6-to-7/) · [7 → 8](https://docs.scandit.com/sdks/web/migrate-7-to-8/) |
| Full API reference     | [ID Capture API (Web)](https://docs.scandit.com/data-capture-sdk/web/id-capture/api.html) |
| Source of truth        | `@scandit/web-datacapture-id` package                                                     |
| Samples                | To be found on [github](https://github.com/Scandit/datacapture-web-samples)               |

### Sample → use-case map

- **IdCaptureSimpleSample** — minimal full-document scan, accept IdCard/Passport/DriverLicense, show face image.
- **IdCaptureExtendedSample** — switch between barcode / MRZ / VIZ via `SingleSideScanner(barcode, mrz, viz)`; `applySettings` to change mode at runtime; localized loading text.
- **IdCaptureSettingsSample** — exhaustive settings playground; the QA reference for every setting.
- **IdCaptureUSDLVerificationSample** — `rejectExpiredIds` + `rejectInconsistentData`, plus standalone `AamvaBarcodeVerifier.create(context)` / `verify(capturedId)`; `DataConsistencyResult.frontReviewImage()`.
- **IdCaptureDriverOnboardingSample** — two-sided flow with `notifyOnSideCapture = true`, `capturedId.isCapturingComplete`, `SingleImageUploader` fallback, `IdSide` image access.
- **IdCaptureShutterModeSample** — `IdCaptureTrigger.ButtonTap` (tap-to-scan shutter), single-image upload, image review.

### Available in this package but NOT covered by this skill

- **Cloud / free-form-text scanning** (`VisaLetter`, `SingleSideScanner` `freeFormText`, `allowCloudScanning`) — partly internal; verify against source and docs before using. Currently not used except by some customers doing a pilot project.
- **Internal frame-signal callbacks** on `Listener` (`didEncounterCaptureIssue`, `didChangeViewfinderHint`, `didUpdateIdOutline`) — marked `@internal`; do not use in customer code.
