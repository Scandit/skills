# ID Capture — Kotlin Multiplatform (KMP) Integration Guide

ID Capture reads identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas, mobile documents — via MRZ, VIZ, PDF417 barcode, or ISO 18013-5 mdoc exchange. On the Scandit KMP SDK, the setup logic (`DataCaptureContext`, `IdCaptureSettings`, `IdCapture`, `IdCaptureListener`, `DataCaptureView`/`IdCaptureOverlay`) lives in `commonMain`; only the thin native hosting code differs between `androidApp` and `iosApp`.

Examples below follow the shape of Scandit's official `IdCaptureSimpleSample` and `USDLVerificationSample` — a shared `ScreenModel` class plus a Compose `AndroidView`/SwiftUI `UIViewRepresentable` host. Adapt ownership to your app's architecture (ViewModel, Presenter, etc.) as needed.

## Prerequisites

- Scandit KMP SDK — add via Gradle in `shared/build.gradle.kts` (`commonMain.dependencies`), group `com.scandit.datacapture.kmp`:
  ```kotlin
  commonMain.dependencies {
      implementation("com.scandit.datacapture.kmp:core:<version>")
      implementation("com.scandit.datacapture.kmp:id:<version>")
  }
  ```
  Before writing the dependency, confirm the latest published `<version>` (8.6.0 at the time of writing) rather than guessing.
- iOS distribution is a single umbrella SPM package, `Scandit/datacapture-kmp-spm` — pick **one** variant that bundles the `id` module (and any add-ons you need). An app can only link one Scandit KMP Kotlin framework — do not add a second variant alongside it.
- A valid Scandit license key — sign in at https://ssl.scandit.com to generate one, or sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission — `android.permission.CAMERA` in the Android manifest (requested at runtime before scanning starts) and `NSCameraUsageDescription` in `Info.plist` on iOS.

## Before writing code — ask the user

1. **Which documents?** `Passport`, `DriverLicense`, `IdCard`, `ResidencePermit`, `HealthInsuranceCard`, `VisaIcao`, `VisaLetter`, `RegionSpecific`. Each takes an `IdCaptureRegion` (`ANY`, `US`, `EU_AND_SCHENGEN`, …). Use the narrowest region that fits.
2. **Which scanner?** — full document, one side/zone only, or mobile document (mDL). KMP does not support combining physical and mobile scanning in one settings object — see Step 2.
3. **Any documents to explicitly exclude?** — `rejectedDocuments`.
4. **Which fields to read?** Top-level (`fullName`, `dateOfBirth`, `documentNumber`, …) or zone-specific (`mrz`, `viz`, `barcode`, `mobileDocument`)?
5. **Verification needed?** AAMVA forgery / data-consistency checks require the `id-aamva-barcode-verification` add-on dependency in addition to the settings flags.
6. **Compose Multiplatform UI, or a custom-hosted `DataCaptureView`?** The samples use the latter (imperative `DataCaptureView` embedded via platform interop); the `id-compose` module offers a declarative `IdCaptureView` composable as an alternative — see the Compose section below.

## Step 1 — Shared `DataCaptureContext`

```kotlin
import com.kmp.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext: DataCaptureContext by lazy {
    DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
}
```

Construct it once, in shared code, and reuse the same reference for the lifetime of the scanning surface.

## Step 2 — Configure `IdCaptureSettings`

```kotlin
import com.kmp.datacapture.id.capture.IdCaptureSettings.Companion.idCaptureSettings
import com.kmp.datacapture.id.data.*
import com.kmp.datacapture.id.scanner.FullDocumentScanner

val settings = IdCaptureSettings.idCaptureSettings().apply {
    acceptedDocuments = listOf(
        Passport(IdCaptureRegion.ANY),
        DriverLicense(IdCaptureRegion.ANY),
        IdCard(IdCaptureRegion.ANY),
    )

    // Optional: explicitly reject a subset of accepted documents.
    // "Rejected always wins" — a match in rejectedDocuments overrides acceptedDocuments.
    rejectedDocuments = listOf(IdCard(IdCaptureRegion.FRANCE))

    scannerType = FullDocumentScanner()
}
```

`IdCaptureSettings` has **no public constructor** — it is created via the `idCaptureSettings()` companion factory, then configured with `.apply { }`.

Document constructors — each takes a single `region: IdCaptureRegion` argument (except `RegionSpecific`, which takes a `subtype`): `IdCard(region)`, `DriverLicense(region)`, `Passport(region)`, `VisaIcao(region)`, `VisaLetter(region)`, `ResidencePermit(region)`, `HealthInsuranceCard(region)`, `RegionSpecific(subtype: RegionSpecificSubtype)`.

### Scanner

`settings.scannerType` takes the scanner value **directly** — there is no wrapper constructor like native Android's `IdCaptureScanner(FullDocumentScanner())`. `FullDocumentScanner`, `SingleSideScanner`, and `MobileDocumentScanner` each directly extend `IdCaptureScanner`.

**`FullDocumentScanner()`** — reads both sides, all zones. No parameters.

```kotlin
settings.scannerType = FullDocumentScanner()
```

**`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone, freeFormText)`** — one side, only the zones you enable. All four parameters are `Boolean`; `barcode`/`machineReadableZone`/`visualInspectionZone` default to `true`, `freeFormText` (KMP-specific) defaults to `false`.

```kotlin
import com.kmp.datacapture.id.scanner.SingleSideScanner

// Back barcode only (US DL):
settings.scannerType = SingleSideScanner(
    barcode = true, machineReadableZone = false, visualInspectionZone = false)

// MRZ only (passport):
settings.scannerType = SingleSideScanner(
    barcode = false, machineReadableZone = true, visualInspectionZone = false)
```

**`MobileDocumentScanner(iso180135, ocr, elementsToRetain)`** — for IDs presented on another device's screen (mDL). Both `Boolean` parameters default to `false`; `elementsToRetain: Set<MobileDocumentDataElement>` defaults to empty. `MobileDocumentScanner.mobileDocumentScanner()` is an equivalent zero-arg factory.

```kotlin
import com.kmp.datacapture.id.scanner.MobileDocumentScanner

settings.scannerType = MobileDocumentScanner(iso180135 = true, ocr = false)
```

**Platform limitation:** unlike native Android, KMP's `scannerType` holds exactly one scanner value — there is no documented way to scan physical and mobile documents from the same `IdCaptureSettings`. If a user needs both, they need two separate settings/mode configurations (or should be told this isn't currently supported on KMP), not a combined constructor.

### Rejection rules

Set flags before creating `IdCapture`. The SDK calls `onIdRejected` with the matching `RejectionReason` when a rule trips.

| Setting | Rejection reason |
|---|---|
| `rejectExpiredIds = true` | `DOCUMENT_EXPIRED` |
| `rejectIdsExpiringIn = Duration(days = 0, months = 6, years = 0)` | `DOCUMENT_EXPIRES_SOON` |
| `rejectVoidedIds = true` | `DOCUMENT_VOIDED` |
| `rejectHolderBelowAge = 21` | `HOLDER_UNDERAGE` |
| `rejectNotRealIdCompliant = true` | `NOT_REAL_ID_COMPLIANT` |
| `rejectForgedAamvaBarcodes = true` | `FORGED_AAMVA_BARCODE` |
| `rejectInconsistentData = true` | `INCONSISTENT_DATA` |

Verification is settings-driven — there is no verifier class. `rejectHolderBelowAge` is an `Int?` — assign the integer `21`, not a string.

### Image capture

Opt in before creating `IdCapture`. Images increase processing time — only request what you need.

```kotlin
import com.kmp.datacapture.id.data.IdImageType

settings.setShouldPassImageTypeToResult(IdImageType.FACE, true)             // holder portrait
settings.setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true) // cropped document (required for frontReviewImage)
settings.setShouldPassImageTypeToResult(IdImageType.FRAME, true)            // full camera frame
```

## Step 3 — Camera setup

`Camera.getDefaultCamera(...)` returns the back camera pre-configured with the recommended settings — it is **nullable** (no camera on some devices). Attach it to the context via `setFrameSource`.

```kotlin
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.id.capture.IdCapture

private val camera: Camera? =
    Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())?.also {
        dataCaptureContext.setFrameSource(it)
    }
```

## Step 4 — Create the `IdCapture` mode

```kotlin
private val idCapture: IdCapture =
    IdCapture.forContext(dataCaptureContext, settings).also {
        it.addListener(this)
        it.feedback = IdCaptureFeedback.defaultFeedback()
    }
```

`IdCapture.forContext(dataCaptureContext, settings)` — not native Android's `forDataCaptureContext`, not iOS's `IdCapture(context:settings:)`. Register the listener once at setup — not repeatedly on every lifecycle resume. Re-apply settings at runtime with `idCapture.applySettings(newSettings)`.

## Step 5 — Shared `DataCaptureView` setup

Build the `DataCaptureView` and attach the overlay in shared code, so both platforms get identical UI configuration:

```kotlin
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import com.kmp.datacapture.id.capture.IdCaptureOverlay

fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
    view.logoStyle = LogoStyle.MINIMAL
    view.addOverlay(IdCaptureOverlay.withIdCaptureForView(idCapture, view))
    return view
}
```

`IdCaptureOverlay.withIdCaptureForView(idCapture, view)` attaches the overlay to a specific view; `IdCaptureOverlay.withIdCapture(idCapture)` creates one without a view reference for later attachment. Neither is a constructor.

### Android hosting

```kotlin
val dataCaptureView = remember {
    screenModel.setupDataCaptureView(DataCaptureView(context, screenModel.dataCaptureContext))
}

AndroidView(
    modifier = Modifier.fillMaxSize(),
    factory = {
        val nativeView: View = dataCaptureView.toAndroidView()
        (nativeView.parent as? ViewGroup)?.removeView(nativeView)
        nativeView
    },
)
```

### iOS hosting

```swift
DataCaptureViewRepresentable {
    let dcView = host.screenModel.setupDataCaptureView(
        view: DataCaptureView(dataCaptureContext: host.screenModel.dataCaptureContext)
    )
    return dcView.toUIView()
}
.edgesIgnoringSafeArea(.all)
```

`DataCaptureView` has no cross-platform constructor exposed in shared code — the Android form takes a platform `Context` (`DataCaptureView(context, dataCaptureContext)`), the iOS form does not (`DataCaptureView(dataCaptureContext: dataCaptureContext)`). The shared `setupDataCaptureView(view)` function still configures both identically once each platform constructs its own instance. `toAndroidView()` / `toUIView()` are the extension functions that expose the shared view as a native `View`/`UIView`.

## Step 6 — Implement `IdCaptureListener`

```kotlin
import com.kmp.datacapture.id.capture.IdCapture
import com.kmp.datacapture.id.capture.IdCaptureListener
import com.kmp.datacapture.id.data.CapturedId
import com.kmp.datacapture.id.scanner.RejectionReason

class IdScannerScreenModel : IdCaptureListener {

    override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
        mode.isEnabled = false
        val message = listOfNotNull(id.fullName, id.documentNumber).joinToString("\n")
        // publish `message` to the shared UI state (e.g. a StateFlow) for both platforms to observe
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        val message = when (reason) {
            RejectionReason.DOCUMENT_EXPIRED -> "This ID has expired."
            RejectionReason.HOLDER_UNDERAGE  -> "Age requirement not met."
            RejectionReason.TIMEOUT          -> "Capture timed out. Try again."
            else                             -> "Document not supported."
        }
        // publish `message` to the shared UI state
    }
}
```

The listener parameters are `mode: IdCapture` and `id: CapturedId` / `id: CapturedId?` — matching the SDK's `IdCaptureListener` interface and the official samples. Always handle every `RejectionReason` you enable with a distinct message.

### Reading results

**Top-level fields** (aggregated from all zones):

```kotlin
capturedId.fullName          // String?
capturedId.dateOfBirth       // DateResult? (.day, .month, .year)
capturedId.dateOfExpiry      // DateResult?
capturedId.documentNumber    // String?
capturedId.nationality       // String?
capturedId.sexType           // Sex (FEMALE / MALE / UNSPECIFIED) — NOT capturedId.sex
capturedId.document?.documentType  // IdCaptureDocumentType
```

**Zone-specific results** (available when that zone was scanned) — property names are `mrz` / `viz` / `barcode` / `mobileDocument` / `mobileDocumentOcr`, **not** `mrzResult` / `vizResult` / `barcodeResult`:

```kotlin
capturedId.mrz             // MrzResult?
capturedId.viz             // VizResult?
capturedId.barcode         // BarcodeResult? — AAMVA data for US/Canadian DLs
capturedId.mobileDocument  // MobileDocumentResult? — ISO 18013-5 mdoc data
```

**Images** (populated only if opted in via `setShouldPassImageTypeToResult`), of type `CapturedImage?`:

```kotlin
capturedId.images.face                            // CapturedImage? (property)
capturedId.images.croppedDocument(IdSide.FRONT)    // CapturedImage? (function)
capturedId.images.frame                           // CapturedImage? (property, side-agnostic)
capturedId.images.frame(IdSide.FRONT)              // CapturedImage? (function, per-side overload)
```

## Feedback & overlay customization

```kotlin
import com.kmp.datacapture.id.capture.IdCaptureFeedback

val feedback = IdCaptureFeedback()
// Configure feedback.idCaptured / feedback.idRejected (each a core Feedback) as needed.
idCapture.feedback = feedback
// Restore defaults with IdCaptureFeedback.defaultFeedback().
```

```kotlin
import com.kmp.datacapture.id.capture.IdLayoutStyle
import com.kmp.datacapture.id.capture.IdLayoutLineStyle
import com.kmp.datacapture.id.ui.TextHintPosition

overlay.idLayoutStyle = IdLayoutStyle.SQUARE           // ROUNDED (default) or SQUARE
overlay.idLayoutLineStyle = IdLayoutLineStyle.BOLD     // LIGHT (default) or BOLD
overlay.textHintPosition = TextHintPosition.BELOW_VIEWFINDER
overlay.showTextHints = true
overlay.setFrontSideTextHint("Place the front of your ID here")
overlay.setBackSideTextHint("Now flip to the back")
```

Brush colors for the captured / localized / rejected states are set via `overlay.capturedBrush`, `overlay.localizedBrush`, `overlay.rejectedBrush` (each a `Brush`); restore defaults with the static `IdCaptureOverlay.defaultCapturedBrush()` / `defaultLocalizedBrush()` / `defaultRejectedBrush()`.

## AAMVA/USDL verification (add-on module)

Requires the `id-aamva-barcode-verification` add-on dependency **in addition to** `id` — the add-on contributes no Kotlin API of its own, it only links the native verification library. Enable it entirely through `IdCaptureSettings`:

```kotlin
// shared/build.gradle.kts
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:id-aamva-barcode-verification:<version>")
}
```

```kotlin
val settings = IdCaptureSettings.idCaptureSettings().apply {
    acceptedDocuments = listOf(DriverLicense(IdCaptureRegion.US))
    scannerType = FullDocumentScanner()
    setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true) // required for frontReviewImage
    rejectForgedAamvaBarcodes = true
    rejectInconsistentData = true
    rejectExpiredIds = true
}
```

Read the review image on a data-consistency rejection, exactly as the `USDLVerificationSample` does:

```kotlin
override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
    mode.isEnabled = false
    when (reason) {
        RejectionReason.INCONSISTENT_DATA -> {
            val reviewImage = id?.verificationResult?.dataConsistency?.frontReviewImage
            presentResult(reason, reviewImage)
        }
        RejectionReason.FORGED_AAMVA_BARCODE -> presentResult(reason, null)
        RejectionReason.DOCUMENT_EXPIRED     -> presentResult(reason, null)
        RejectionReason.TIMEOUT              -> showAlert("Capture timed out. Please try again.")
        else                                 -> showAlert("Document not supported.")
    }
}
```

**`VerificationResult` members** (`capturedId.verificationResult`, non-null once the checks ran):
- `.dataConsistency` — `DataConsistencyResult?` — `.allChecksPassed: Boolean`, `.passedChecks` / `.skippedChecks` / `.failedChecks: Set<DataConsistencyCheck>`, `.frontReviewImage: CapturedImage?` (null unless `CROPPED_DOCUMENT` image capture was opted in).
- `.aamvaBarcodeVerification` — `AamvaBarcodeVerificationResult?` — `.allChecksPassed: Boolean`, `.status: AamvaBarcodeVerificationStatus` (`AUTHENTIC` / `LIKELY_FORGED` / `FORGED`).

Verification is settings-driven — do **not** use a standalone `AamvaBarcodeVerifier` or `DataConsistencyVerifier` class; neither exists on KMP.

## Voided document detection (add-on module)

Requires the `id-voided-detection` add-on dependency, plus `rejectVoidedIds = true`:

```kotlin
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:id-voided-detection:<version>")
}
```

```kotlin
settings.rejectVoidedIds = true
```

```kotlin
override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
    mode.isEnabled = false
    when (reason) {
        RejectionReason.DOCUMENT_VOIDED ->
            showAlert("This document is voided. Please scan a valid document.")
        else -> showAlert("Document not supported.")
    }
}
```

There is no standalone voided-detection result type — the only signal is `RejectionReason.DOCUMENT_VOIDED`. Primarily tuned for US Driver's Licenses.

## Decode the back of European Driving Licenses (add-on module)

Requires the `id-europe-driving-license` add-on dependency, plus `decodeBackOfEuropeanDrivingLicense = true`:

```kotlin
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:id-europe-driving-license:<version>")
}
```

```kotlin
settings.decodeBackOfEuropeanDrivingLicense = true
```

The categories then appear on the VIZ result:

```kotlin
override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
    mode.isEnabled = false
    id.viz?.drivingLicenseDetails?.drivingLicenseCategories?.forEach { category ->
        println("Category: ${category.code}")     // NOT categoryCode
        println("Issued: ${category.dateOfIssue}")
        println("Expires: ${category.dateOfExpiry}")
    }
}
```

Read from `capturedId.viz` — not `capturedId.vizResult`. The category code is `category.code`, not `.categoryCode`.

## Compose Multiplatform

The `id-compose` module (built on `core-compose`) exposes ID Capture as a single declarative composable — an alternative to the imperative `DataCaptureView`/`IdCaptureOverlay` setup above, not a required addition to it.

```kotlin
// shared/build.gradle.kts
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:core-compose:<version>")
    implementation("com.scandit.datacapture.kmp:id-compose:<version>")
}
```

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.kmp.datacapture.id.compose.IdCaptureView
import com.kmp.datacapture.id.capture.IdCaptureSettings.Companion.idCaptureSettings
import com.kmp.datacapture.id.capture.IdLayoutStyle

@Composable
fun IdScreen() {
    IdCaptureView(
        settings = IdCaptureSettings.idCaptureSettings(),
        modifier = Modifier.fillMaxSize(),
        overlayStyle = IdLayoutStyle.ROUNDED,
        onCapture = { capturedId -> /* handle the captured document */ },
        onReject = { capturedId, reason -> /* handle rejection */ },
    )
}
```

`onReject`'s `capturedId` parameter is nullable (e.g. `null` on a timeout where nothing was recognized). `IdCaptureView` builds and owns its own `IdCapture` mode from `settings` by default — pass an existing `idCapture` instance instead if you need to control it from outside the composable (e.g. to toggle `isEnabled`, register additional listeners, or call `reset()`); when you do, the `settings` parameter is ignored. `IdCaptureView` renders through the core-compose `DataCaptureView` internally — it does not require you to build a `DataCaptureView` yourself.

## Lifecycle & Teardown

Drive the camera and mode from your platform's lifecycle events (Android `Activity`/`Fragment` lifecycle, iOS `onAppear`/`onDisappear`), by calling into the shared `ScreenModel`:

```kotlin
fun onStarted() {
    camera?.switchToDesiredState(FrameSourceState.ON)
    idCapture.isEnabled = true
}

fun onStopped() {
    idCapture.isEnabled = false
    camera?.switchToDesiredState(FrameSourceState.OFF)
}

fun dispose() {
    idCapture.isEnabled = false
    idCapture.removeListener(this)
    dataCaptureContext.removeMode(idCapture)
    camera?.switchToDesiredState(FrameSourceState.OFF)
}
```

On Android, drive `onStarted()`/`onStopped()` from `ON_RESUME`/`ON_PAUSE` and call `dispose()` from the composable's `DisposableEffect.onDispose`. On iOS, call `onStarted()`/`onStopped()` from `.onAppear`/`.onDisappear` and `dispose()` from `deinit`.

## Pitfalls

1. `IdCaptureSettings.idCaptureSettings()` — not a bare constructor.
2. `settings.scannerType` takes the scanner value directly — no `IdCaptureScanner(...)` wrapper, and no combined physical+mobile scanner.
3. `IdCapture.forContext(context, settings)` — not `forDataCaptureContext` (native Android), not an iOS-style initializer.
4. `IdCaptureOverlay.withIdCapture(...)` / `.withIdCaptureForView(...)` — not `.newInstance(...)`.
5. `capturedId.sexType`, not `capturedId.sex`.
6. `Camera.getDefaultCamera(...)` returns `Camera?` — always null-check before using it.
7. AAMVA verification / voided detection / EU driving-license decoding each need an extra Gradle/SPM add-on dependency on top of the settings flag — the flag alone has no effect without the corresponding native library linked.
8. Package imports are `com.kmp.datacapture.*`; Gradle/SPM coordinates are `com.scandit.datacapture.kmp:*` — different namespaces, don't conflate them.
9. Enum values are `UPPER_SNAKE_CASE` (`IdCaptureRegion.ANY`, `RejectionReason.DOCUMENT_EXPIRED`).
10. `DataCaptureView` has no shared constructor — build it per-platform (`DataCaptureView(context, dataCaptureContext)` on Android, `DataCaptureView(dataCaptureContext: dataCaptureContext)` on iOS), then run identical shared setup code on it.

## Where to go next

- [ID Capture Intro (KMP)](https://docs.scandit.com/sdks/kmp/id-capture/intro/)
- [Get Started (KMP)](https://docs.scandit.com/sdks/kmp/id-capture/get-started/)
- [Advanced Configurations (KMP)](https://docs.scandit.com/sdks/kmp/id-capture/advanced/)
- [Core Concepts (context, camera, views, Compose)](https://docs.scandit.com/sdks/kmp/core-concepts/)
