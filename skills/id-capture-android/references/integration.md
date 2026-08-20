# ID Capture — Android (Kotlin/Java) Integration Guide

ID Capture reads identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — via MRZ, VIZ, and/or PDF417 barcode. You declare which documents to accept and which scanner to use; the SDK returns a `CapturedId`.

Examples below use Kotlin and an Activity. The same APIs work identically with Java and in Fragments — adapt ownership of `DataCaptureContext`, `IdCapture`, and the `Camera` to the project's existing structure.

## Prerequisites

- Scandit Data Capture SDK for Android — add via Gradle. Before writing the dependency, fetch the latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/id` and extract the latest version number from the page. Then add both dependencies to `app/build.gradle`:
  ```gradle
  dependencies {
      implementation "com.scandit.datacapture:id:<latest-version>"
      implementation "com.scandit.datacapture:core:<latest-version>"
  }
  ```
  Or in `app/build.gradle.kts`:
  ```kotlin
  dependencies {
      implementation("com.scandit.datacapture:id:<latest-version>")
      implementation("com.scandit.datacapture:core:<latest-version>")
  }
  ```
  The SDK is distributed via Maven Central. The PDF417/AAMVA barcode reader and MRZ/VIZ engines are bundled in the `id` module — there is no separate barcode package to add for ID Capture.
- `minSdk` 24 or higher.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission in `AndroidManifest.xml`:
  ```xml
  <uses-feature
      android:name="android.hardware.camera"
      android:required="true" />
  <uses-permission android:name="android.permission.CAMERA" />
  ```
  Request the `CAMERA` permission at runtime using the standard Android permission API before scanning starts — the manifest declaration alone is not sufficient.

## Before writing code — ask the user

1. **Which documents?** `Passport`, `DriverLicense`, `IdCard`, `ResidencePermit`, `HealthInsuranceCard`, `VisaIcao`, `RegionSpecific`. Each takes an `IdCaptureRegion` (`ANY`, `US`, `EU_AND_SCHENGEN`, …). Use the narrowest region that fits.
2. **Which scanner?** — see Step 2 below.
3. **Any documents to explicitly exclude?** — use `rejectedDocuments`.
4. **Which fields to read?** Top-level (`fullName`, `dateOfBirth`, `documentNumber`, …) or zone-specific (`mrz`, `viz`, `barcode`)?
5. **Document images needed?** Face photo, cropped document, or raw frame?
6. **Which Activity or Fragment to integrate into?** Write code directly into that file — don't just show it in chat.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```kotlin
import com.scandit.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

## Step 2 — Configure IdCaptureSettings

```kotlin
import com.scandit.datacapture.id.capture.*
import com.scandit.datacapture.id.data.*

val settings = IdCaptureSettings().apply {
    acceptedDocuments = listOf(
        Passport(IdCaptureRegion.ANY),
        DriverLicense(IdCaptureRegion.ANY),
        IdCard(IdCaptureRegion.ANY),
    )

    // Optional: explicitly reject a subset of accepted documents.
    // "Rejected always wins" — a match in rejectedDocuments overrides acceptedDocuments.
    rejectedDocuments = listOf(IdCard(IdCaptureRegion.FRANCE))

    scanner = IdCaptureScanner(FullDocumentScanner())
}
```

Document constructors: `IdCard(IdCaptureRegion)`, `DriverLicense(IdCaptureRegion)`, `Passport(IdCaptureRegion)`, `VisaIcao(IdCaptureRegion)`, `ResidencePermit(IdCaptureRegion)`, `HealthInsuranceCard(IdCaptureRegion)`, `RegionSpecific(RegionSpecificSubtype)`.

### Scanner

Choose based on what data you need:

**`FullDocumentScanner`** — reads both sides, all zones. Use when you need complete data from front and back.

```kotlin
scanner = IdCaptureScanner(FullDocumentScanner())
```

**`SingleSideScanner`** — one side, only the zones you enable. Use when you need a specific zone only.

```kotlin
// Back barcode only (US DL):
scanner = IdCaptureScanner(SingleSideScanner(
    barcode = true, machineReadableZone = false, visualInspectionZone = false))

// MRZ only (passport):
scanner = IdCaptureScanner(SingleSideScanner(
    barcode = false, machineReadableZone = true, visualInspectionZone = false))
```

**`MobileDocumentScanner`** — for IDs presented on another device's screen (mDL). Not for physical documents. See `references/advanced.md`.

### Rejection rules

Set flags before creating `IdCapture`. The SDK calls `onIdRejected` with the matching `RejectionReason` when a rule trips.

| Setting | Rejection reason |
|---|---|
| `rejectExpiredIds = true` | `DOCUMENT_EXPIRED` |
| `rejectIdsExpiringIn = Duration(months = 6)` | `DOCUMENT_EXPIRES_SOON` |
| `rejectVoidedIds = true` | `DOCUMENT_VOIDED` |
| `rejectHolderBelowAge = 21` | `HOLDER_UNDERAGE` |
| `rejectNotRealIdCompliant = true` | `NOT_REAL_ID_COMPLIANT` |
| `rejectForgedAamvaBarcodes = true` | `FORGED_AAMVA_BARCODE` |
| `rejectInconsistentData = true` | `INCONSISTENT_DATA` |

Verification is settings-driven — there is no verifier class. `rejectHolderBelowAge` is an `Int?` — assign the integer `21`, not a string.

### Image capture

Opt in before creating `IdCapture`. Images increase processing time — only request what you need.

```kotlin
settings.setShouldPassImageTypeToResult(IdImageType.FACE, true)             // holder portrait
settings.setShouldPassImageTypeToResult(IdImageType.CROPPED_DOCUMENT, true) // cropped document (required for frontReviewImage)
settings.setShouldPassImageTypeToResult(IdImageType.FRAME, true)            // full camera frame
```

## Step 3 — Camera setup

`Camera.getDefaultCamera(...)` returns the back camera pre-configured with the recommended settings. Attach it to the context via `setFrameSource`.

```kotlin
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.id.capture.IdCapture

private val camera = Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())

init {
    dataCaptureContext.setFrameSource(camera)
}
```

## Step 4 — Create the IdCapture mode

```kotlin
private val idCapture = IdCapture.forDataCaptureContext(dataCaptureContext, settings)

// Register once at setup — not in onResume.
idCapture.addListener(this)
```

Re-applying settings at runtime is done via `idCapture.applySettings(newSettings)`.

## Step 5 — DataCaptureView and IdCaptureOverlay

`DataCaptureView.newInstance(context, dataCaptureContext)` creates the camera preview. In an Activity, pass it to `setContentView`. `IdCaptureOverlay.newInstance(idCapture, dataCaptureView)` adds the document overlay.

```kotlin
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.id.ui.overlay.IdCaptureOverlay

// In onCreate():
val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
IdCaptureOverlay.newInstance(idCapture, dataCaptureView)
setContentView(dataCaptureView)
```

In a Fragment, add the view to a container in your layout instead:
```kotlin
val dataCaptureView = DataCaptureView.newInstance(requireContext(), dataCaptureContext)
IdCaptureOverlay.newInstance(idCapture, dataCaptureView)
binding.scannerContainer.addView(dataCaptureView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
```

## Step 6 — Implement IdCaptureListener

Both callbacks run on a **background thread** — dispatch UI work with `runOnUiThread {}`. Disable the mode before showing results to prevent re-capture.

```kotlin
import com.scandit.datacapture.id.capture.IdCapture
import com.scandit.datacapture.id.capture.IdCaptureListener
import com.scandit.datacapture.id.data.CapturedId
import com.scandit.datacapture.id.data.RejectionReason

class IdScanActivity : AppCompatActivity(), IdCaptureListener {

    override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
        mode.isEnabled = false
        val message = listOfNotNull(id.fullName, id.documentNumber)
            .joinToString("\n")
        // onIdCaptured runs on a background thread — dispatch UI work.
        runOnUiThread {
            showResultDialog("Recognized", message) { mode.isEnabled = true }
        }
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        val message = when (reason) {
            RejectionReason.DOCUMENT_EXPIRED -> "This ID has expired."
            RejectionReason.HOLDER_UNDERAGE  -> "Age requirement not met."
            RejectionReason.TIMEOUT          -> "Capture timed out. Try again."
            else                             -> "Document not supported."
        }
        runOnUiThread {
            showResultDialog("Rejected", message) { mode.isEnabled = true }
        }
    }
}
```

The listener parameters are named `mode`, `id`, and `reason` — this matches the SDK's `IdCaptureListener` interface and the official samples. (Kotlin lets you rename override parameters, but following the SDK convention keeps code consistent.) Always handle every `RejectionReason` you enable with a distinct user-facing message.

### Reading results

**Top-level fields** (aggregated from all zones):

```kotlin
capturedId.fullName          // String?
capturedId.dateOfBirth       // DateResult? (.day, .month, .year)
capturedId.dateOfExpiry      // DateResult?
capturedId.documentNumber    // String?
capturedId.nationality       // String?
capturedId.issuingCountry    // IdCaptureRegion
capturedId.document?.documentType  // IdCaptureDocumentType
```

**Zone-specific results** (available when that zone was scanned) — note the property names are `mrz` / `viz` / `barcode`, **not** `mrzResult` / `vizResult` / `barcodeResult`:

```kotlin
capturedId.mrz             // MrzResult? — MRZ string, check digits
capturedId.viz             // VizResult? — VIZ data, capturedSides
capturedId.barcode         // BarcodeResult? — AAMVA data for US/Canadian DLs
capturedId.mobileDocument  // MobileDocumentResult? — ISO 18013-5 mDL data
```

**Images** (only populated if opted in via `setShouldPassImageTypeToResult`) — returned as `android.graphics.Bitmap?`:

```kotlin
capturedId.images.face                          // Bitmap?
capturedId.images.getCroppedDocument(IdSide.FRONT) // Bitmap?
capturedId.images.frame                         // Bitmap?
```

## Step 7 — Lifecycle management

Drive the camera from `onResume` and `onPause`. The camera must not be active while the app is in the background.

```kotlin
override fun onResume() {
    super.onResume()
    idCapture.isEnabled = true
    camera?.switchToDesiredState(FrameSourceState.ON)
}

override fun onPause() {
    idCapture.isEnabled = false
    camera?.switchToDesiredState(FrameSourceState.OFF)
    super.onPause()
}

override fun onDestroy() {
    idCapture.removeListener(this)
    dataCaptureContext.removeCurrentMode()
    super.onDestroy()
}
```

## Complete example

```kotlin
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.id.capture.*
import com.scandit.datacapture.id.data.*
import com.scandit.datacapture.id.ui.overlay.IdCaptureOverlay

class IdScanActivity : AppCompatActivity(), IdCaptureListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())

    private val idCapture: IdCapture

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = IdCaptureSettings().apply {
            acceptedDocuments = listOf(
                Passport(IdCaptureRegion.ANY),
                DriverLicense(IdCaptureRegion.ANY),
                IdCard(IdCaptureRegion.ANY),
            )
            scanner = IdCaptureScanner(FullDocumentScanner())
        }

        idCapture = IdCapture.forDataCaptureContext(dataCaptureContext, settings)
        idCapture.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        IdCaptureOverlay.newInstance(idCapture, dataCaptureView)
        setContentView(dataCaptureView)
        // Request CAMERA permission here before scanning starts.
    }

    override fun onResume() {
        super.onResume()
        idCapture.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        idCapture.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        idCapture.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
        mode.isEnabled = false
        val message = listOfNotNull(id.fullName, id.documentNumber)
            .joinToString("\n")
        runOnUiThread {
            // show `message`, then mode.isEnabled = true when dismissed
        }
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        val message = if (reason == RejectionReason.TIMEOUT)
            "Capture timed out." else "Document not supported."
        runOnUiThread {
            // show `message`, then mode.isEnabled = true when dismissed
        }
    }
}
```

## Key rules

1. `DataCaptureContext.forLicenseKey(key)` once — reuse the same reference for the scanning surface.
2. `settings.scanner` always takes an `IdCaptureScanner` wrapper — not `scannerType` (v7) or `supportedDocuments` (v6).
3. `IdCapture.forDataCaptureContext(context, settings)` — not a constructor, not iOS `IdCapture(context:settings:)`, not `.NET IdCapture.Create`.
4. `addListener` once after creating the mode, not in `onResume`.
5. Both callbacks run on a background thread — always `runOnUiThread {}` for UI.
6. `isEnabled = false` before showing results; `true` when dismissed.
7. Camera off in `onPause`, on in `onResume`; `removeCurrentMode()` in `onDestroy`.
8. Runtime `CAMERA` permission required before the first scan — manifest alone is not enough.
9. Enum values are `UPPER_SNAKE_CASE` (`IdCaptureRegion.ANY`, `RejectionReason.DOCUMENT_EXPIRED`).

## Where to go next

- `references/advanced.md` — USDL verification, anonymization, voided detection, EU driving-license back decoding, mobile documents (mDL), BarcodeCapture co-existence, overlay/feedback customization.
- [Get Started (Android)](https://docs.scandit.com/sdks/android/id-capture/get-started/)
